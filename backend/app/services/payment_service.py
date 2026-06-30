from app.config.db import get_connection
from app.utils.sp_executor import execute_stored_procedure
from app.utils.Razorpayclient import razorpay_client
from app.utils.Signature import verify_payment_signature
from app.utils.logger import log_info, log_exception


# -------------------------------------------------
# Helper -- har jagah connection open/close/execute karna padta tha,
# isko ek hi jagah le aaye taaki repeat na ho.
# -------------------------------------------------
def run_sp(procedure_name: str, params: tuple = (), fetch: bool = False):
    conn = get_connection()
    try:
        return execute_stored_procedure(conn, procedure_name, params, fetch=fetch)
    finally:
        conn.close()


# =========================================================
# STEP 1: INVOICE GENERATE (pehle yeh hota hai)
# =========================================================
def create_invoice(name: str, email: str, address: str, amount: float):
    """
    Razorpay ki Invoice API use karke pehle invoice banate hain.
    Invoice ke andar Razorpay khud ek order_id bhi create kar deta hai --
    wahi order_id hum apne DB mein bhi save karte hain.
    """
    amount_in_paise = int(round(amount * 100))

    try:
        invoice = razorpay_client.invoice.create({
            "type": "invoice",
            "description": "Payment for order",
            "customer": {
                "name": name,
                "email": email,
            },
            "line_items": [
                {
                    "name": "Order Payment",
                    "amount": amount_in_paise,
                    "currency": "INR",
                    "quantity": 1,
                }
            ],
            "currency": "INR",
        })
    except Exception as e:
        log_exception(f"Razorpay invoice creation failed: {str(e)}")
        return {"success": False, "message": "Failed to create Razorpay invoice", "error": str(e)}

    invoice_id = invoice["id"]
    razorpay_order_id = invoice["order_id"]
    short_url = invoice["short_url"]
    status = invoice["status"]

    db_result = run_sp(
        "sp_CreateTransactionOrder",
        (name, email, address, amount, razorpay_order_id)
    )

    if not db_result["success"]:
        return {"success": False, "message": "Invoice created on Razorpay but failed to save in DB", "error": db_result["error"]}

    # Invoice URL turant save kar dete hain, payment hone se pehle hi
    run_sp("sp_UpdateTransactionInvoice", (razorpay_order_id, short_url, None))

    log_info(f"Invoice created: {invoice_id} for order {razorpay_order_id}")

    return {
        "success": True,
        "message": "Invoice created successfully",
        "data": {
            "invoiceId": invoice_id,
            "razorpayOrderId": razorpay_order_id,
            "shortUrl": short_url,
            "amount": amount_in_paise,
            "currency": "INR",
            "status": status,
            "keyId": razorpay_client.auth[0],
        }
    }


# =========================================================
# STEP 2: PAYMENT VERIFY (invoice ban chuka, ab payment confirm karte hain)
# =========================================================
def verify_and_complete_payment(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str):
    is_valid = verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature)

    if not is_valid:
        return {"success": False, "message": "Signature verification failed. Payment rejected."}

    try:
        payment = razorpay_client.payment.fetch(razorpay_payment_id)
    except Exception as e:
        log_exception(f"Failed to fetch payment from Razorpay: {str(e)}")
        return {"success": False, "message": "Could not verify payment with Razorpay", "error": str(e)}

    if payment.get("status") not in ("captured", "authorized"):
        return {"success": False, "message": f"Payment not completed. Razorpay status: {payment.get('status')}"}

    payment_method = payment.get("method")

    db_result = run_sp(
        "sp_UpdateTransactionSuccess",
        (razorpay_order_id, razorpay_payment_id, razorpay_signature, None, payment_method)
    )

    if not db_result["success"]:
        return {"success": False, "message": "Payment verified but DB update failed", "error": db_result["error"]}

    log_info(f"Payment verified and updated: {razorpay_order_id}")
    return {"success": True, "message": "Payment verified and recorded", "data": {"paymentMethod": payment_method}}


# =========================================================
# STEP 3: PAYMENT FAILED
# =========================================================
def mark_payment_failed(razorpay_order_id: str, reason: str = None):
    return run_sp("sp_UpdateTransactionFailed", (razorpay_order_id, reason))


# =========================================================
# WEBHOOK -- server-to-server update (signature route level pe verify ho chuki hoti hai)
# =========================================================
def update_transaction_from_webhook(razorpay_order_id: str, razorpay_payment_id: str, payment_method: str = None):
    db_result = run_sp(
        "sp_UpdateTransactionSuccess",
        (razorpay_order_id, razorpay_payment_id, "webhook-verified", None, payment_method)
    )

    if not db_result["success"]:
        log_exception(f"Webhook DB update failed for {razorpay_order_id}: {db_result.get('error')}")

    return db_result


# =========================================================
# READ
# =========================================================
def get_transaction(order_id: str):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vw_ActiveTransactions WHERE OrderId = ?", order_id)
        row = cursor.fetchone()
        if not row:
            return None
        columns = [c[0] for c in cursor.description]
        return dict(zip(columns, row))
    finally:
        conn.close()
        
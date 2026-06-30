from fastapi import APIRouter, Request, HTTPException

from app.schemas.payment import (
    CreateInvoiceRequest,
    CreateInvoiceResponse,
    VerifyPaymentRequest,
    PaymentFailedRequest,
    TransactionResponse,
)
from app.services.payment_service import (
    create_invoice,
    verify_and_complete_payment,
    mark_payment_failed,
    update_transaction_from_webhook,
    get_transaction,
)
from app.utils.Signature import verify_webhook_signature
from app.utils.logger import log_info, log_exception

router = APIRouter()


def success(data=None, message="Success"):
    return {"success": True, "message": message, "data": data}


@router.post("/create-invoice", response_model=None)
def create_invoice_api(data: CreateInvoiceRequest):
    result = create_invoice(data.name, data.email, data.address, data.amount)

    if not result["success"]:
        raise HTTPException(status_code=502, detail=result["message"])

    return success(result["data"], result["message"])


@router.post("/verify-payment")
def verify_payment_api(data: VerifyPaymentRequest):
    result = verify_and_complete_payment(
        data.razorpay_order_id,
        data.razorpay_payment_id,
        data.razorpay_signature,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return success(result["data"], "Payment verified and recorded")


@router.post("/payment-failed")
def payment_failed_api(data: PaymentFailedRequest):
    result = mark_payment_failed(data.razorpay_order_id, data.reason)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error") or "Failed to update transaction")

    return success(message="Payment marked as failed")


@router.post("/webhook")
async def razorpay_webhook(request: Request):
    raw_body = await request.body()
    received_signature = request.headers.get("X-Razorpay-Signature", "")

    if not verify_webhook_signature(raw_body, received_signature):
        log_exception("Webhook signature mismatch — possible spoofed request")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event", "")
    log_info(f"Webhook event received: {event}")

    if event == "payment.captured":
        entity = payload["payload"]["payment"]["entity"]
        update_transaction_from_webhook(
            entity["order_id"],
            entity["id"],
            entity.get("method")
        )

    elif event == "payment.failed":
        entity = payload["payload"]["payment"]["entity"]
        reason = entity.get("error_description") or entity.get("error_code") or "Payment failed"
        mark_payment_failed(entity["order_id"], reason)

    elif event == "invoice.paid":
        entity = payload["payload"]["invoice"]["entity"]
        order_id = entity.get("order_id")
        payment_id = entity.get("payment_id")
        if order_id and payment_id:
            update_transaction_from_webhook(order_id, payment_id, None)
        log_info(f"Invoice paid webhook: invoice_id={entity.get('id')} order_id={order_id}")

    elif event == "order.paid":
        entity = payload["payload"]["order"]["entity"]
        order_id = entity.get("id")
        payment = payload["payload"].get("payment", {}).get("entity", {})
        payment_id = payment.get("id")
        method = payment.get("method")
        if order_id and payment_id:
            update_transaction_from_webhook(order_id, payment_id, method)
        log_info(f"Order paid webhook: order_id={order_id}")

    elif event == "refund.created":
        entity = payload["payload"]["refund"]["entity"]
        log_info(f"Refund created: refund_id={entity.get('id')} order_id={entity.get('notes', {}).get('order_id', 'N/A')}")

    else:
        log_info(f"Unhandled webhook event: {event}")

    return {"status": "ok"}


@router.get("/transaction/{order_id}", response_model=TransactionResponse)
def get_transaction_api(order_id: str):
    txn = get_transaction(order_id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"No active transaction found for OrderId '{order_id}'")
    return txn
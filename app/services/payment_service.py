"""
Payment service — business logic layer.
All DB calls go through run_sp(); all Razorpay calls use razorpay_client.
"""

import json
import re

from app.config.db import get_connection
from app.utils.sp_executor import execute_stored_procedure
from app.utils.Razorpayclient import razorpay_client
from app.utils.Signature import verify_payment_signature
from app.utils.logger import log_info, log_exception


# --------------------------------------------------------------------------- #
# Internal helpers                                                             #
# --------------------------------------------------------------------------- #

def _sanitize_name(name: str) -> str | None:
    """Strip unsafe characters from customer name before sending to Razorpay."""
    if not isinstance(name, str):
        return None
    clean = re.sub(r"[^A-Za-z0-9\s\.\-,'&()]+", "", name.strip())
    return clean.strip() or None


def run_sp(procedure_name: str, params: tuple = (), fetch: bool = False) -> dict:
    """Open a connection, run one stored procedure, close connection."""
    try:
        conn = get_connection()
    except Exception as exc:
        log_exception(f"DB connection failed [{procedure_name}]: {exc}")
        return {
            "success": False,
            "message": "Database connection failed",
            "data": None,
            "error": str(exc),
        }

    try:
        return execute_stored_procedure(conn, procedure_name, params, fetch=fetch)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# Public service functions                                                     #
# --------------------------------------------------------------------------- #

def create_invoice(name: str, email: str, address: str, amount: float) -> dict:
    """
    1. Validate inputs
    2. Create Razorpay invoice
    3. Save to DB via sp_create_transaction_order
    4. Update short_url/invoice_id via sp_update_transaction_invoice
    """
    # ── Guard: Razorpay client ──────────────────────────────────────────────
    if not razorpay_client:
        return {
            "success": False,
            "message": "Razorpay is not configured",
            "error": "RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET missing",
        }

    # ── Guard: name sanitization ────────────────────────────────────────────
    sanitized_name = _sanitize_name(name)
    if not sanitized_name:
        return {
            "success": False,
            "message": "Invalid customer name",
            "error": "Name must contain valid characters and cannot be empty",
        }
    if sanitized_name != name:
        log_info(f"Name sanitized: {name!r} → {sanitized_name!r}")

    amount_paise = int(round(amount * 100))

    # ── Create Razorpay invoice ─────────────────────────────────────────────
    try:
        invoice = razorpay_client.invoice.create({
            "type": "invoice",
            "description": "Payment for order",
            "customer": {"name": sanitized_name, "email": email},
            "line_items": [{
                "name": "Order Payment",
                "amount": amount_paise,
                "currency": "INR",
                "quantity": 1,
            }],
            "currency": "INR",
        })
    except Exception as exc:
        log_exception(f"Razorpay invoice creation failed: {exc}")
        return {
            "success": False,
            "message": "Failed to create Razorpay invoice",
            "error": str(exc),
        }

    invoice_id = invoice["id"]
    order_id   = invoice["order_id"]
    short_url  = invoice["short_url"]
    status     = invoice["status"]

    # ── Save to DB ──────────────────────────────────────────────────────────
    # sp_create_transaction_order(
    #   name, email, address, amount, gross_amount,
    #   order_id, invoice_id, short_url,
    #   payment_request_data, payment_response_data,
    #   application_name, coupon_code
    # )
    db = run_sp(
        "sp_create_transaction_order",
        (
            name, email, address,
            amount, amount,          # amount + gross_amount (same at creation)
            order_id, invoice_id, short_url,
            None, None,              # payment_request_data, payment_response_data
            None, None,              # application_name, coupon_code
        ),
    )

    if not db["success"]:
        log_exception(f"Invoice on Razorpay but DB save failed [{order_id}]: {db.get('error')}")
        # Still return invoice data so user can pay — DB can be retried
        return {
            "success": True,
            "message": "Invoice created; DB save failed. Try again later.",
            "data": _invoice_payload(invoice_id, order_id, short_url, amount_paise, status),
            "error": db.get("error"),
        }

    # ── Update invoice meta (best-effort, not critical) ─────────────────────
    # sp_update_transaction_invoice(order_id, short_url, invoice_id)
    run_sp("sp_update_transaction_invoice", (order_id, short_url, invoice_id))

    log_info(f"Invoice created: invoice_id={invoice_id} order_id={order_id}")
    return {
        "success": True,
        "message": "Invoice created successfully",
        "data": _invoice_payload(invoice_id, order_id, short_url, amount_paise, status),
    }


def verify_and_complete_payment(
    order_id: str,
    payment_id: str,
    signature: str,
) -> dict:
    """
    1. Verify HMAC signature
    2. Fetch payment from Razorpay (confirm captured/authorized)
    3. Update DB via sp_update_transaction_success
    """
    if not verify_payment_signature(order_id, payment_id, signature):
        return {"success": False, "message": "Signature verification failed. Payment rejected."}

    try:
        payment = razorpay_client.payment.fetch(payment_id)
    except Exception as exc:
        log_exception(f"Could not fetch payment [{payment_id}]: {exc}")
        return {"success": False, "message": "Could not verify payment with Razorpay", "error": str(exc)}

    if payment.get("status") not in ("captured", "authorized"):
        return {
            "success": False,
            "message": f"Payment not completed. Razorpay status: {payment.get('status')}",
        }

    method = payment.get("method")

    # sp_update_transaction_success(
    #   order_id, gateway_payment_id, gateway_signature,
    #   invoice_path, after_payment_response_data
    # )
    db = run_sp(
        "sp_update_transaction_success",
        (
            order_id, payment_id, signature,
            None,                                    # invoice_path
            {"payment_method": method} if method else None,
        ),
    )

    if not db["success"]:
        return {"success": False, "message": "Payment verified but DB update failed", "error": db["error"]}

    log_info(f"Payment verified: order_id={order_id} payment_id={payment_id} method={method}")
    return {"success": True, "message": "Payment verified and recorded", "data": {"paymentMethod": method}}


def mark_payment_failed(order_id: str, reason: str = None) -> dict:
    """
    Mark transaction as Failed in DB via sp_update_transaction_failed.
    Called from payment-failed endpoint AND webhook (payment.failed event).
    """
    # sp_update_transaction_failed(order_id, reason)
    result = run_sp("sp_update_transaction_failed", (order_id, reason or "Payment failed"))
    if not result["success"]:
        log_exception(f"Failed to mark payment failed [{order_id}]: {result.get('error')}")
    else:
        log_info(f"Payment marked failed: order_id={order_id} reason={reason!r}")
    return result


def update_transaction_from_webhook(
    order_id: str,
    payment_id: str,
    method: str = None,
) -> dict:
    """
    Called by webhook events: payment.captured, invoice.paid, order.paid
    Uses sp_update_transaction_success with signature='webhook-verified'.
    """
    db = run_sp(
        "sp_update_transaction_success",
        (
            order_id, payment_id, "webhook-verified",
            None,
            {"payment_method": method} if method else None,
        ),
    )
    if not db["success"]:
        log_exception(f"Webhook DB update failed [{order_id}]: {db.get('error')}")
    else:
        log_info(f"Webhook: transaction updated [{order_id}] method={method}")
    return db


def get_transaction(order_id: str) -> dict | None:
    """
    Fetch a single transaction by Razorpay order_id.
    Returns dict or None if not found.
    """
    try:
        conn = get_connection()
    except Exception as exc:
        log_exception(f"DB connection failed [get_transaction {order_id}]: {exc}")
        return None

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                t.order_id                                        AS "OrderId",
                c.name                                            AS "CustomerName",
                c.email                                           AS "CustomerEmail",
                c.address                                         AS "Address",
                t.amount                                          AS "Amount",
                t.status                                          AS "Status",
                t.gateway_payment_id                              AS "PaymentId",
                t.after_payment_response_data->>'payment_method'  AS "PaymentMethod",
                t.short_url                                       AS "InvoiceUrl",
                t.created_at                                      AS "CreatedAt"
            FROM  public.transactions t
            JOIN  public.clients c ON c.client_id = t.client_id
            WHERE t.order_id  = %s
              AND t.is_deleted  = FALSE
              AND c.is_deleted  = FALSE
            LIMIT 1
            """,
            (order_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    except Exception as exc:
        log_exception(f"get_transaction failed [{order_id}]: {exc}")
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# Private helpers                                                              #
# --------------------------------------------------------------------------- #

def _invoice_payload(invoice_id, order_id, short_url, amount_paise, status) -> dict:
    return {
        "invoiceId":      invoice_id,
        "razorpayOrderId": order_id,
        "shortUrl":       short_url,
        "amount":         amount_paise,
        "currency":       "INR",
        "status":         status,
        "keyId":          razorpay_client.auth[0],
    }
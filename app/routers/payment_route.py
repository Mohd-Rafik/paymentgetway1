"""
Payment router — all /api/payment/* endpoints + webhook handler.
"""

import json

from fastapi import APIRouter, HTTPException, Request

from app.schemas.payment import (
    CreateInvoiceRequest,
    PaymentFailedRequest,
    TransactionResponse,
    VerifyPaymentRequest,
)
from app.services.payment_service import (
    create_invoice,
    get_transaction,
    mark_payment_failed,
    update_transaction_from_webhook,
    verify_and_complete_payment,
)
from app.utils.logger import log_exception, log_info
from app.utils.Signature import verify_webhook_signature

router = APIRouter()


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def ok(data=None, message: str = "Success") -> dict:
    return {"success": True, "message": message, "data": data}


# --------------------------------------------------------------------------- #
# REST endpoints                                                               #
# --------------------------------------------------------------------------- #

@router.post("/create-invoice", summary="Create Razorpay invoice & save to DB")
def create_invoice_api(body: CreateInvoiceRequest):
    """
    POST /api/payment/create-invoice
    Body: { name, email, address, amount }
    Returns: { invoiceId, razorpayOrderId, shortUrl, amount(paise), currency, status, keyId }
    """
    result = create_invoice(body.name, body.email, body.address, body.amount)

    if not result["success"]:
        raise HTTPException(
            status_code=502,
            detail={"message": result["message"], "error": result.get("error")},
        )

    return ok(result["data"], result["message"])


@router.post("/verify-payment", summary="Verify Razorpay payment signature & update DB")
def verify_payment_api(body: VerifyPaymentRequest):
    """
    POST /api/payment/verify-payment
    Body: { razorpay_order_id, razorpay_payment_id, razorpay_signature }
    Returns: { paymentMethod }
    """
    result = verify_and_complete_payment(
        body.razorpay_order_id,
        body.razorpay_payment_id,
        body.razorpay_signature,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return ok(result.get("data"), "Payment verified and recorded")


@router.post("/payment-failed", summary="Mark a payment as failed in DB")
def payment_failed_api(body: PaymentFailedRequest):
    """
    POST /api/payment/payment-failed
    Body: { razorpay_order_id, reason? }
    """
    result = mark_payment_failed(body.razorpay_order_id, body.reason)

    if not result["success"]:
        raise HTTPException(
            status_code=404,
            detail=result.get("error") or "Failed to update transaction",
        )

    return ok(message="Payment marked as failed")


@router.get(
    "/transaction/{order_id}",
    response_model=TransactionResponse,
    summary="Get transaction details by Razorpay order ID",
)
def get_transaction_api(order_id: str):
    """
    GET /api/payment/transaction/{order_id}
    Returns full transaction + customer info.
    """
    txn = get_transaction(order_id)
    if not txn:
        raise HTTPException(
            status_code=404,
            detail=f"No active transaction found for order_id='{order_id}'",
        )
    return txn


# --------------------------------------------------------------------------- #
# Webhook (registered at both /api/payment/webhook and root /razorpay-webhook)#
# --------------------------------------------------------------------------- #

@router.post("/webhook", summary="Razorpay webhook receiver")
async def razorpay_webhook(request: Request):
    """
    POST /api/payment/webhook   (also mounted at /razorpay-webhook in main.py)

    Razorpay sends HMAC-SHA256 signed events here.
    Events handled:
      - payment.captured  → mark Success
      - payment.failed    → mark Failed
      - invoice.paid      → mark Success (invoice flow)
      - order.paid        → mark Success (order flow)
      - refund.created    → log only
    """
    # ── 1. Read raw body (must happen before .json()) ───────────────────────
    raw_body = await request.body()
    received_sig = request.headers.get("X-Razorpay-Signature", "")

    # ── 2. Verify HMAC-SHA256 signature ─────────────────────────────────────
    if not verify_webhook_signature(raw_body, received_sig):
        log_exception("Webhook rejected — invalid signature")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    # ── 3. Parse JSON payload ────────────────────────────────────────────────
    try:
        payload = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON in webhook body")

    event = payload.get("event", "unknown")
    log_info(f"Webhook received: event={event}")

    # ── 4. Route by event type ───────────────────────────────────────────────
    try:
        if event == "payment.captured":
            entity = payload["payload"]["payment"]["entity"]
            update_transaction_from_webhook(
                entity["order_id"],
                entity["id"],
                entity.get("method"),
            )

        elif event == "payment.failed":
            entity = payload["payload"]["payment"]["entity"]
            reason = (
                entity.get("error_description")
                or entity.get("error_code")
                or "Payment failed"
            )
            mark_payment_failed(entity["order_id"], reason)

        elif event == "invoice.paid":
            entity = payload["payload"]["invoice"]["entity"]
            order_id   = entity.get("order_id")
            payment_id = entity.get("payment_id")
            if order_id and payment_id:
                update_transaction_from_webhook(order_id, payment_id, None)
            log_info(f"invoice.paid: invoice_id={entity.get('id')} order_id={order_id}")

        elif event == "order.paid":
            entity     = payload["payload"]["order"]["entity"]
            order_id   = entity.get("id")
            pay_entity = payload["payload"].get("payment", {}).get("entity", {})
            payment_id = pay_entity.get("id")
            method     = pay_entity.get("method")
            if order_id and payment_id:
                update_transaction_from_webhook(order_id, payment_id, method)
            log_info(f"order.paid: order_id={order_id}")

        elif event == "refund.created":
            entity = payload["payload"]["refund"]["entity"]
            log_info(
                f"refund.created: refund_id={entity.get('id')} "
                f"payment_id={entity.get('payment_id')}"
            )

        else:
            log_info(f"Unhandled webhook event: {event}")

    except (KeyError, TypeError) as exc:
        # Don't crash — log and return 200 so Razorpay won't retry forever
        log_exception(f"Webhook payload parse error [{event}]: {exc}")

    return {"status": "ok", "event": event}
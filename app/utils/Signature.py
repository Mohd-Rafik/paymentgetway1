import os
import hmac
import hashlib

from razorpay.errors import SignatureVerificationError
from app.utils.Razorpayclient import razorpay_client
from app.utils.logger import log_exception


def verify_payment_signature(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })
        return True
    except SignatureVerificationError as e:
        log_exception(f"Payment signature verification failed: {str(e)}")
        return False


def verify_webhook_signature(payload_body: bytes, received_signature: str) -> bool:
    webhook_secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
    if not webhook_secret:
        log_exception("RAZORPAY_WEBHOOK_SECRET not set")
        return False
    generated_signature = hmac.new(
        webhook_secret.encode("utf-8"),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(generated_signature, received_signature)
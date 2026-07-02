import os
import razorpay
from dotenv import load_dotenv

load_dotenv()


def get_razorpay_client():
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")

    if not key_id or not key_secret:
        raise RuntimeError("Razorpay credentials are not configured")

    return razorpay.Client(auth=(key_id, key_secret))


try:
    razorpay_client = get_razorpay_client()
except Exception:
    razorpay_client = None
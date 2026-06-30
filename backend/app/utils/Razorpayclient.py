import os
import razorpay
from dotenv import load_dotenv

load_dotenv()

razorpay_client = razorpay.Client(
    auth=(os.environ["RAZORPAY_KEY_ID"], os.environ["RAZORPAY_KEY_SECRET"])
)
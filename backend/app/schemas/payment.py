

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# =========================================================
# BASE / SHARED FIELDS (inheritance ke liye)
# =========================================================

class OrderIdMixin(BaseModel):
    """Jahan bhi sirf razorpay_order_id chahiye, yahan se inherit karo."""
    razorpay_order_id: str = Field(..., description="Razorpay Order ID (order_XXXX format)")


class CustomerInfoMixin(BaseModel):
    """Customer ke basic details -- create_order aur create_invoice dono mein same hain."""
    name: str = Field(..., min_length=1, max_length=100, description="Customer ka poora naam")
    email: EmailStr = Field(..., description="Customer ka email address")
    address: str = Field(default="", max_length=500, description="Address (optional)")
    amount: float = Field(..., gt=0, description="Payment amount INR mein")


# =========================================================
# INVOICE -- FIRST STEP (ab payment se pehle invoice banta hai)
# =========================================================

class CreateInvoiceRequest(CustomerInfoMixin):
    """POST /api/payment/create-invoice -- amount, name, email, address CustomerInfoMixin se aate hain."""

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Rafik Ahmed",
                "email": "rafik@example.com",
                "address": "123 Street, Hyderabad",
                "amount": 499.00
            }
        }


class CreateInvoiceResponse(BaseModel):
    invoiceId: str = Field(..., description="Razorpay Invoice ID (inv_XXXX)")
    razorpayOrderId: str = Field(..., description="Razorpay Order ID jo invoice ke andar bana")
    shortUrl: str = Field(..., description="Razorpay-hosted invoice payment link")
    amount: int = Field(..., description="Amount paise mein")
    currency: str = Field(default="INR")
    status: str = Field(..., description="Invoice status (issued/draft/paid)")
    keyId: str = Field(..., description="Razorpay public key ID -- checkout.js ke liye")


# =========================================================
# PAYMENT VERIFICATION -- SECOND STEP
# =========================================================

class VerifyPaymentRequest(OrderIdMixin):
    """POST /api/payment/verify-payment -- checkout success ke baad."""

    razorpay_payment_id: str = Field(..., description="Razorpay Payment ID (pay_XXXX format)")
    razorpay_signature: str = Field(..., description="HMAC-SHA256 signature for verification")

    class Config:
        json_schema_extra = {
            "example": {
                "razorpay_order_id": "order_Abc123XYZ",
                "razorpay_payment_id": "pay_Xyz789ABC",
                "razorpay_signature": "abc123def456..."
            }
        }


class PaymentFailedRequest(OrderIdMixin):
    """POST /api/payment/payment-failed -- jab user cancel kare ya payment fail ho."""

    reason: Optional[str] = Field(default=None, description="Failure reason (optional)")

    class Config:
        json_schema_extra = {
            "example": {
                "razorpay_order_id": "order_Abc123XYZ",
                "reason": "User dismissed checkout"
            }
        }


# =========================================================
# TRANSACTION READ
# =========================================================

class TransactionResponse(BaseModel):
    OrderId: str
    CustomerName: Optional[str] = None
    CustomerEmail: Optional[str] = None
    Address: Optional[str] = None
    Amount: Optional[float] = None
    Status: Optional[str] = None
    PaymentId: Optional[str] = None
    PaymentMethod: Optional[str] = None
    InvoiceUrl: Optional[str] = None
    CreatedAt: Optional[str] = None

from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field


# ─── Request Schemas ──────────────────────────────────────────────────────────

class CreateInvoiceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Customer full name")
    email: EmailStr = Field(..., description="Customer email address")
    address: str = Field(default="", max_length=500, description="Address (optional)")
    amount: float = Field(..., gt=0, description="Payment amount in INR")

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str = Field(..., description="Razorpay Order ID (order_XXXX format)")
    razorpay_payment_id: str = Field(..., description="Razorpay Payment ID (pay_XXXX format)")
    razorpay_signature: str = Field(..., description="HMAC-SHA256 signature for verification")


class PaymentFailedRequest(BaseModel):
    razorpay_order_id: str = Field(..., description="Razorpay Order ID (order_XXXX format)")
    reason: Optional[str] = Field(default=None, description="Failure reason (optional)")


# ─── Response Schemas ─────────────────────────────────────────────────────────

class CreateInvoiceResponse(BaseModel):
    invoiceId: str = Field(..., description="Razorpay Invoice ID (inv_XXXX)")
    razorpayOrderId: str = Field(..., description="Razorpay Order ID from invoice")
    shortUrl: str = Field(..., description="Razorpay-hosted invoice payment link")
    amount: int = Field(..., description="Amount in paise")
    currency: str = Field(default="INR")
    status: str = Field(..., description="Invoice status (issued/draft/paid)")
    keyId: str = Field(..., description="Razorpay public key ID for checkout.js")


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
    CreatedAt: Optional[Any] = None  # datetime from DB serialized to ISO string

    class Config:
        json_encoders = {
            __import__("datetime").datetime: lambda v: v.isoformat(),
        }

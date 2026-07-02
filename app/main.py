"""
FastAPI application entry point — SecurePay Payment Gateway.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.middleware.cors import add_cors_middleware
from app.routers.payment_route import razorpay_webhook, router

app = FastAPI(
    title="SecurePay — Razorpay Payment Gateway",
    description="FastAPI backend for Razorpay invoice + payment integration.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ───────────────────────────────────────────────────────────────
add_cors_middleware(app)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(router, prefix="/api/payment", tags=["Payment"])

# ── Legacy webhook mount (Razorpay dashboard may be pointed here) ────────────
# Same handler as /api/payment/webhook — kept for backward compatibility.
@app.post("/razorpay-webhook", tags=["Webhook"], summary="Legacy webhook URL")
async def legacy_razorpay_webhook(request: Request):
    return await razorpay_webhook(request)


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"], summary="Health check")
def health():
    return {"success": True, "message": "Payment Gateway Running", "version": "1.0.0"}


# ── Global error handler ─────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Internal server error", "error": str(exc)},
    )
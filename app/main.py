from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.routers.payment_route import router
from app.middleware.cors import add_cors_middleware

app = FastAPI(
    title="Razorpay Payment Gateway",
    description="SecurePay — FastAPI backend for Razorpay payment integration",
    version="1.0.0",
)

add_cors_middleware(app)

app.include_router(router, prefix="/api/payment", tags=["Payment"])


@app.get("/", summary="Health Check")
def home():
    return {"success": True, "message": "Payment Gateway Running", "version": "1.0.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Internal server error", "error": str(exc)}
    )
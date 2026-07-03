import os
from fastapi.middleware.cors import CORSMiddleware

# Read extra allowed origins from env (for production flexibility)
_extra = os.environ.get("ALLOWED_ORIGINS", "")
_extra_origins = [o.strip() for o in _extra.split(",") if o.strip()]

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    # ── Render deployed URLs ─────────────────────────────────────────────────
    "https://paymentgetwayfrontend-2.onrender.com",  # ✅ actual frontend
    "https://paymentgetway-g49v.onrender.com",        # backend /docs self-calls
    "https://securepay-frontend.onrender.com",
    "https://paymentgetway1.onrender.com",
] + _extra_origins



def add_cors_middleware(app) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

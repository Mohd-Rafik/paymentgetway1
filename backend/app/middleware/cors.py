
from fastapi.middleware.cors import CORSMiddleware
ALLOWED_ORIGINS = [
    "http://localhost:3000",    
    "http://localhost:3001",    
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]


def add_cors_middleware(app) -> None:
    """FastAPI app mein CORS middleware attach karo."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

"""CORS, security headers, and rate limiting middleware for floci API."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse


# ── Rate limiter ────────────────────────────────────────────────────────

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],
    headers_enabled=True,  # X-RateLimit-* headers
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests — slow down.",
            "retry_after_seconds": 60,
        },
    )


# ── Security headers middleware ─────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Strip Server header
        response.headers["Server"] = ""
        return response


# ── Apply middleware ─────────────────────────────────────────────────────

def setup_middleware(app: FastAPI) -> None:
    """Apply CORS, security headers, and rate limiting to the FastAPI app."""

    # 1. Security headers (outermost — wraps everything)
    app.add_middleware(SecurityHeadersMiddleware)

    # 2. CORS — allow readtheplan.dev, playground, and localhost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://readtheplan.dev",
            "https://readtheplan.pages.dev",
            "http://localhost:3000",
            "http://localhost:5173",
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "ETag", "Cache-Control"],
    )

    # 3. Rate limiting (innermost — per-route limits override)
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

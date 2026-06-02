"""Structured JSON error responses for consistent API error formatting."""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


async def not_found_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Return a friendly JSON error ONLY for actual 404 Not Found routes."""
    if exc.status_code != 404:
        # For other HTTP errors (400, 422, etc.), let FastAPI handle normally
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    return JSONResponse(
        status_code=404,
        content={
            "error": "not_found",
            "message": f"Route '{request.url.path}' does not exist.",
            "hint": "Try GET /scenarios, POST /create?scenario=mixed, or visit /docs for the API reference.",
        },
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a structured JSON error for 422 validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Invalid request — check the 'scenario' parameter.",
            "hint": "Available scenarios: simple, full, mixed, update, security. See GET /scenarios for details.",
        },
    )

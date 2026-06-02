"""FastAPI app assembly — pulls together middleware, routes, and error handlers."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .middleware import setup_middleware
from .routes import router
from .errors import not_found_handler, validation_error_handler


def create_app() -> FastAPI:
    app = FastAPI(
        title="floci API",
        version="0.3.0",
        description=(
            "Generate realistic `terraform show -json` output from "
            "Moto-provisioned AWS resources — no AWS account needed.\n\n"
            "**Scenarios:** simple (3), full (7), mixed (5), security (6), update (3)\n\n"
            "**Usage:** `curl -X POST /create?scenario=mixed | readtheplan analyze --framework soc2`"
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Apply middleware (CORS, security headers, rate limiting)
    setup_middleware(app)

    # Register routes
    app.include_router(router)

    # Error handlers
    app.add_exception_handler(StarletteHTTPException, not_found_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    return app


app = create_app()

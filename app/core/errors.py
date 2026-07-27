"""Standardized API error handling.

A single error shape is returned for every failure so clients can rely on a
stable contract:

    {"error": {"code": "CONTRACT_NOT_FOUND", "message": "Contract not found."}}

Routers raise :class:`AppError` (or one of its subclasses) instead of building
ad-hoc ``HTTPException``s with inconsistent bodies. The handlers registered by
:func:`register_exception_handlers` translate those -- plus FastAPI validation
errors and any uncaught exception -- into the shape above.
"""

from enum import Enum

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logger import get_logger


logger = get_logger(__name__)


class ErrorCode(str, Enum):
    """Machine-readable error codes returned in ``error.code``."""

    CONTRACT_NOT_FOUND = "CONTRACT_NOT_FOUND"
    PAYMENT_NOT_FOUND = "PAYMENT_NOT_FOUND"
    AGENT_RUN_NOT_FOUND = "AGENT_RUN_NOT_FOUND"
    SCHEDULER_RUN_NOT_FOUND = "SCHEDULER_RUN_NOT_FOUND"
    NOTIFICATION_NOT_FOUND = "NOTIFICATION_NOT_FOUND"
    INVALID_REFERENCE = "INVALID_REFERENCE"
    EMAIL_ALREADY_REGISTERED = "EMAIL_ALREADY_REGISTERED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


class AppError(Exception):
    """Base application error carrying a code, message and HTTP status.

    Raised by routers (never by services -- services raise their own domain
    exceptions which routers translate) so the response body stays consistent.
    """

    status_code: int = 400
    code: ErrorCode = ErrorCode.VALIDATION_ERROR

    def __init__(self, message: str, *, code: ErrorCode | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message

        if code is not None:
            self.code = code

        if status_code is not None:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = 404
    code = ErrorCode.NOT_FOUND


class UnauthorizedError(AppError):
    status_code = 401
    code = ErrorCode.UNAUTHORIZED


class ForbiddenError(AppError):
    status_code = 403
    code = ErrorCode.FORBIDDEN


class ConflictError(AppError):
    status_code = 409
    code = ErrorCode.VALIDATION_ERROR


class RateLimitedError(AppError):
    status_code = 429
    code = ErrorCode.RATE_LIMITED


def _error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=_error_body(code, message))


# Map bare HTTP status codes (raised by framework internals or third-party
# middleware as plain HTTPExceptions) to a stable error code.
_STATUS_TO_CODE = {
    400: ErrorCode.VALIDATION_ERROR,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    409: ErrorCode.VALIDATION_ERROR,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMITED,
}


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the standardized error handlers to the FastAPI app."""

    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        # Client-caused (4xx) errors are expected; log at info. Server faults log
        # louder. Never include the raw exception args beyond the safe message.
        log = logger.info if exc.status_code < 500 else logger.error
        log(
            "request_failed",
            extra={
                "error_code": exc.code.value,
                "status_code": exc.status_code,
                "path": request.url.path,
            },
        )
        return error_response(exc.code.value, exc.message, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return error_response(
            ErrorCode.VALIDATION_ERROR.value,
            _summarize_validation(exc),
            422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = _STATUS_TO_CODE.get(exc.status_code, ErrorCode.INTERNAL_SERVER_ERROR)
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return error_response(code.value, message, exc.status_code)

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Last-resort handler: never leak internals to the client, but log the
        # full traceback (with correlation id via the logging filter).
        logger.exception(
            "unhandled_exception",
            extra={"path": request.url.path},
        )
        return error_response(
            ErrorCode.INTERNAL_SERVER_ERROR.value,
            "An unexpected error occurred.",
            500,
        )


def _summarize_validation(exc: RequestValidationError) -> str:
    """Turn pydantic's error list into a short human-readable message."""

    parts = []

    for err in exc.errors():
        location = ".".join(str(p) for p in err.get("loc", []) if p != "body")
        message = err.get("msg", "invalid value")
        parts.append(f"{location}: {message}" if location else message)

    return "; ".join(parts) or "Request validation failed."
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import ProviderError
from app.schemas.errors import ErrorDetail, ErrorResponse, FieldError

logger = logging.getLogger(__name__)

# Machine-readable code for each HTTP status we deliberately raise.
_STATUS_CODES: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: "payload_too_large",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "unsupported_media_type",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "unprocessable_entity",
    status.HTTP_502_BAD_GATEWAY: "upstream_provider_error",
}


def _envelope(
    status_code: int, code: str, message: str, details: list[FieldError] | None = None
) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, details=details))
    return JSONResponse(status_code=status_code, content=body.model_dump(exclude_none=True))


async def _http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _STATUS_CODES.get(exc.status_code, "error")
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return _envelope(exc.status_code, code, message)


async def _validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        FieldError(
            field=".".join(str(part) for part in error["loc"] if part != "body") or "body",
            message=error["msg"],
        )
        for error in exc.errors()
    ]
    return _envelope(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "validation_error",
        "Request validation failed",
        details,
    )


async def _provider_error_handler(_: Request, exc: ProviderError) -> JSONResponse:
    logger.warning("Upstream provider error: %s", exc.message)
    return _envelope(status.HTTP_502_BAD_GATEWAY, "upstream_provider_error", exc.message)


async def _unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return _envelope(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "internal_error",
        "An unexpected error occurred",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ProviderError, _provider_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_exception_handler)

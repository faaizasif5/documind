from pydantic import BaseModel


class FieldError(BaseModel):
    """A single request-validation failure, tied to an input field."""

    field: str
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[FieldError] | None = None


class ErrorResponse(BaseModel):
    """Envelope returned for every error response across the API."""

    error: ErrorDetail

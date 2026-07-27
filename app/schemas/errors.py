from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """The standardized error envelope returned by every failing endpoint."""

    error: ErrorDetail
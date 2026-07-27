from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.session import SessionLocal
from app.core.security import create_access_token
from app.core.errors import ConflictError, UnauthorizedError, ErrorCode
from app.core.rate_limit import rate_limit_login, rate_limit_register
from app.container import create_auth_service
from app.services.auth_service import AuthService, EmailAlreadyRegisteredError


router = APIRouter(prefix="/auth", tags=["auth"])


# Minimum viable password strength enforced at the edge (syntax only -- any
# richer policy would be a business rule and belong in the service layer).
_MIN_PASSWORD_LENGTH = 8
_MAX_PASSWORD_LENGTH = 128


class RegisterRequest(BaseModel):

    email: EmailStr
    password: str = Field(
        min_length=_MIN_PASSWORD_LENGTH,
        max_length=_MAX_PASSWORD_LENGTH,
    )


class LoginRequest(BaseModel):

    email: EmailStr
    password: str = Field(min_length=1, max_length=_MAX_PASSWORD_LENGTH)


class UserResponse(BaseModel):

    id: int
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):

    access_token: str
    token_type: str = "bearer"


def get_auth_service():

    db = SessionLocal()

    try:
        yield create_auth_service(db=db)
    finally:
        db.close()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    dependencies=[Depends(rate_limit_register)],
)
def register(
    request: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
):

    try:
        return service.register(request.email, request.password)
    except EmailAlreadyRegisteredError:
        raise ConflictError(
            "Email already registered.",
            code=ErrorCode.EMAIL_ALREADY_REGISTERED,
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_login)],
)
def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service),
):

    user = service.authenticate(request.email, request.password)

    if user is None:
        raise UnauthorizedError(
            "Invalid credentials.",
            code=ErrorCode.INVALID_CREDENTIALS,
        )

    return TokenResponse(access_token=create_access_token(user.id))
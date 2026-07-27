from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from app.db.session import SessionLocal
from app.core.security import create_access_token
from app.container import create_auth_service
from app.services.auth_service import AuthService, EmailAlreadyRegisteredError


router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):

    email: str
    password: str


class LoginRequest(BaseModel):

    email: str
    password: str


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


@router.post("/register", response_model=UserResponse, status_code=201)
def register(
    request: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
):

    try:
        return service.register(request.email, request.password)
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service),
):

    user = service.authenticate(request.email, request.password)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    return TokenResponse(access_token=create_access_token(user.id))
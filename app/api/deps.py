from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.session import SessionLocal
from app.core.security import decode_access_token
from app.core.errors import UnauthorizedError, NotFoundError, ErrorCode
from app.container import create_auth_service
from app.models.user import User
from app.models.contract import Contract
from app.repositories.contract_repository import ContractRepository


_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> User:
    """Resolve the authenticated user from a Bearer JWT, or raise 401."""

    if credentials is None:
        raise UnauthorizedError("Not authenticated.")

    user_id = decode_access_token(credentials.credentials)

    if user_id is None:
        raise UnauthorizedError("Invalid or expired token.")

    db = SessionLocal()

    try:
        user = create_auth_service(db=db).get_user(user_id)
    finally:
        db.close()

    if user is None:
        raise UnauthorizedError("User not found.")

    return user


def require_owned_contract(
    contract_id: int,
    current_user: User = Depends(get_current_user),
) -> Contract:
    """Ensure the authenticated user owns the requested contract, or 404."""

    db = SessionLocal()

    try:
        contract = ContractRepository(db).get_by_id_for_user(
            contract_id,
            current_user.id,
        )
    finally:
        db.close()

    if contract is None:
        raise NotFoundError("Contract not found.", code=ErrorCode.CONTRACT_NOT_FOUND)

    return contract
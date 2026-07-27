from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.session import SessionLocal
from app.core.security import decode_access_token
from app.core.errors import UnauthorizedError, NotFoundError, ForbiddenError, ErrorCode
from app.core.logger import get_logger
from app.container import create_auth_service
from app.models.user import User
from app.models.contract import Contract
from app.repositories.contract_repository import ContractRepository


logger = get_logger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> User:
    """Resolve the authenticated user from a Bearer JWT, or raise 401."""

    if credentials is None:
        logger.info("auth_unauthorized", extra={"reason": "missing_token"})
        raise UnauthorizedError("Not authenticated.")

    user_id = decode_access_token(credentials.credentials)

    if user_id is None:
        # Never log the token itself.
        logger.info("auth_unauthorized", extra={"reason": "invalid_token"})
        raise UnauthorizedError("Invalid or expired token.")

    db = SessionLocal()

    try:
        user = create_auth_service(db=db).get_user(user_id)
    finally:
        db.close()

    if user is None:
        logger.info(
            "auth_unauthorized",
            extra={"reason": "user_not_found", "user_id": user_id},
        )
        raise UnauthorizedError("User not found.")

    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure the authenticated user is an admin, or raise 403."""

    if not getattr(current_user, "is_admin", False):
        logger.info("admin_access_denied", extra={"user_id": current_user.id})
        raise ForbiddenError("Admin privileges required.")

    return current_user


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
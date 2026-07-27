from app.core.security import hash_password, verify_password
from app.core.logger import get_logger
from app.models.user import User
from app.repositories.user_repository import UserRepository


logger = get_logger(__name__)


class EmailAlreadyRegisteredError(Exception):
    pass


class AuthService:

    def __init__(
        self,
        user_repository: UserRepository,
        audit_service=None,
    ):
        self.user_repository = user_repository
        self.audit_service = audit_service

    def register(self, email: str, password: str) -> User:

        # Never log the password; the email is the auth identifier.
        if self.user_repository.get_by_email(email) is not None:
            logger.info(
                "auth_register_failed",
                extra={"email": email, "reason": "email_already_registered"},
            )
            raise EmailAlreadyRegisteredError(email)

        user = self.user_repository.create(
            User(
                email=email,
                hashed_password=hash_password(password),
            )
        )

        logger.info("auth_register_success", extra={"user_id": user.id, "email": email})

        return user

    def authenticate(self, email: str, password: str) -> User | None:

        user = self.user_repository.get_by_email(email)

        if user is None:
            logger.info(
                "auth_login_failed",
                extra={"email": email, "reason": "user_not_found"},
            )
            self._audit_login_failed(email, "user_not_found")
            return None

        if not verify_password(password, user.hashed_password):
            logger.info(
                "auth_login_failed",
                extra={"email": email, "reason": "invalid_password"},
            )
            self._audit_login_failed(email, "invalid_password", user_id=user.id)
            return None

        logger.info("auth_login_success", extra={"user_id": user.id})

        if self.audit_service is not None:
            self.audit_service.record(
                action=self.audit_service.USER_LOGIN,
                user_id=user.id,
                entity_type="user",
                entity_id=user.id,
            )

        return user

    def _audit_login_failed(self, email: str, reason: str, user_id: int | None = None) -> None:
        # Never store the password; only the email + reason.
        if self.audit_service is None:
            return

        self.audit_service.record(
            action=self.audit_service.USER_LOGIN_FAILED,
            user_id=user_id,
            entity_type="user",
            metadata={"email": email, "reason": reason},
        )

    def get_user(self, user_id: int) -> User | None:

        return self.user_repository.get_by_id(user_id)
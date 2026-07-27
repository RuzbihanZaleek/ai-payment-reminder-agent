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
    ):
        self.user_repository = user_repository

    def register(self, email: str, password: str) -> User:

        if self.user_repository.get_by_email(email) is not None:
            # Never log the password; the email is the auth identifier.
            logger.info("registration_rejected_duplicate_email", extra={"email": email})
            raise EmailAlreadyRegisteredError(email)

        user = self.user_repository.create(
            User(
                email=email,
                hashed_password=hash_password(password),
            )
        )

        logger.info("user_registered", extra={"user_id": user.id, "email": email})

        return user

    def authenticate(self, email: str, password: str) -> User | None:

        user = self.user_repository.get_by_email(email)

        if user is None or not verify_password(password, user.hashed_password):
            logger.info("authentication_failed", extra={"email": email})
            return None

        logger.info("authentication_succeeded", extra={"user_id": user.id})

        return user

    def get_user(self, user_id: int) -> User | None:

        return self.user_repository.get_by_id(user_id)
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository


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
            raise EmailAlreadyRegisteredError(email)

        return self.user_repository.create(
            User(
                email=email,
                hashed_password=hash_password(password),
            )
        )

    def authenticate(self, email: str, password: str) -> User | None:

        user = self.user_repository.get_by_email(email)

        if user is None:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user

    def get_user(self, user_id: int) -> User | None:

        return self.user_repository.get_by_id(user_id)
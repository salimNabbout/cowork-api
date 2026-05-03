from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User


class InvalidCredentialsError(Exception):
    """Email/senha invalidos ou usuario inativo."""


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise InvalidCredentialsError()
    if not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError()
    if not user.is_active:
        raise InvalidCredentialsError()
    return user

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserNotFoundError(Exception):
    """Levantada quando um usuario nao e encontrado no banco."""


class EmailAlreadyExistsError(Exception):
    """Levantada quando o email ja esta cadastrado em outro usuario."""


def _get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user_in: UserCreate) -> User:
    if _get_user_by_email(db, user_in.email) is not None:
        raise EmailAlreadyExistsError(user_in.email)
    data = user_in.model_dump()
    password = data.pop("password", None)
    user = User(**data, hashed_password=hash_password(password) if password else None)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_users(db: Session, skip: int = 0, limit: int = 10):
    return db.query(User).offset(skip).limit(limit).all()


def get_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise UserNotFoundError(user_id)
    return user


def update_user(db: Session, user_id: int, user_in: UserCreate) -> User:
    user = get_user(db, user_id)
    if user_in.email != user.email:
        existing = _get_user_by_email(db, user_in.email)
        if existing is not None and existing.id != user_id:
            raise EmailAlreadyExistsError(user_in.email)
    data = user_in.model_dump()
    password = data.pop("password", None)
    for field, value in data.items():
        setattr(user, field, value)
    if password:
        user.hashed_password = hash_password(password)
    db.commit()
    db.refresh(user)
    return user


def patch_user(db: Session, user_id: int, user_in: UserUpdate) -> User:
    user = get_user(db, user_id)
    update_data = user_in.model_dump(exclude_unset=True)
    new_email = update_data.get("email")
    if new_email is not None and new_email != user.email:
        existing = _get_user_by_email(db, new_email)
        if existing is not None and existing.id != user_id:
            raise EmailAlreadyExistsError(new_email)
    password = update_data.pop("password", None)
    for field, value in update_data.items():
        setattr(user, field, value)
    if password is not None:
        user.hashed_password = hash_password(password)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> None:
    user = get_user(db, user_id)
    db.delete(user)
    db.commit()

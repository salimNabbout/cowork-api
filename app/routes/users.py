from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import user_service
from app.services.user_service import EmailAlreadyExistsError, UserNotFoundError

router = APIRouter(prefix="/users", tags=["users"])

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
_EMAIL_CONFLICT = HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        return user_service.create_user(db, payload)
    except EmailAlreadyExistsError:
        raise _EMAIL_CONFLICT


@router.get("", response_model=list[UserRead])
def list_users(
    skip: int = Query(0, ge=0, description="Quantos registros pular"),
    limit: int = Query(10, ge=1, le=100, description="Tamanho da pagina (max 100)"),
    db: Session = Depends(get_db),
):
    return user_service.get_users(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    try:
        return user_service.get_user(db, user_id)
    except UserNotFoundError:
        raise _NOT_FOUND


@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserCreate, db: Session = Depends(get_db)):
    try:
        return user_service.update_user(db, user_id, payload)
    except UserNotFoundError:
        raise _NOT_FOUND
    except EmailAlreadyExistsError:
        raise _EMAIL_CONFLICT


@router.patch("/{user_id}", response_model=UserRead)
def patch_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    try:
        return user_service.patch_user(db, user_id, payload)
    except UserNotFoundError:
        raise _NOT_FOUND
    except EmailAlreadyExistsError:
        raise _EMAIL_CONFLICT


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    try:
        user_service.delete_user(db, user_id)
    except UserNotFoundError:
        raise _NOT_FOUND
    return None

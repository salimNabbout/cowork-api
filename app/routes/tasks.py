from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services import task_service
from app.services.task_service import TaskNotFoundError
from app.services.user_service import UserNotFoundError

router = APIRouter(tags=["tasks"])

_USER_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
_TASK_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")


@router.post("/users/{user_id}/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    user_id: int,
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise _USER_NOT_FOUND
    try:
        return task_service.create_task(db, user_id, payload)
    except UserNotFoundError:
        raise _USER_NOT_FOUND


@router.get("/users/{user_id}/tasks", response_model=list[TaskRead])
def list_user_tasks(
    user_id: int,
    skip: int = Query(0, ge=0, description="Quantos registros pular"),
    limit: int = Query(10, ge=1, le=100, description="Tamanho da pagina (max 100)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise _USER_NOT_FOUND
    try:
        return task_service.get_tasks_by_user(db, user_id, skip=skip, limit=limit)
    except UserNotFoundError:
        raise _USER_NOT_FOUND


@router.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        task = task_service.get_task(db, task_id)
    except TaskNotFoundError:
        raise _TASK_NOT_FOUND
    if task.user_id != current_user.id:
        raise _TASK_NOT_FOUND
    return task


@router.patch("/tasks/{task_id}", response_model=TaskRead)
def patch_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        task = task_service.get_task(db, task_id)
    except TaskNotFoundError:
        raise _TASK_NOT_FOUND
    if task.user_id != current_user.id:
        raise _TASK_NOT_FOUND
    return task_service.patch_task(db, task_id, payload)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        task = task_service.get_task(db, task_id)
    except TaskNotFoundError:
        raise _TASK_NOT_FOUND
    if task.user_id != current_user.id:
        raise _TASK_NOT_FOUND
    task_service.delete_task(db, task_id)
    return None

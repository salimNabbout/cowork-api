from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.user_service import get_user


class TaskNotFoundError(Exception):
    """Levantada quando uma task nao e encontrada."""


def create_task(db: Session, user_id: int, task_in: TaskCreate) -> Task:
    get_user(db, user_id)  # propaga UserNotFoundError se nao existir
    task = Task(**task_in.model_dump(), user_id=user_id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_tasks_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 10):
    get_user(db, user_id)  # 404 se user nao existe
    return (
        db.query(Task)
        .filter(Task.user_id == user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_task(db: Session, task_id: int) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise TaskNotFoundError(task_id)
    return task


def patch_task(db: Session, task_id: int, task_in: TaskUpdate) -> Task:
    task = get_task(db, task_id)
    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: int) -> None:
    task = get_task(db, task_id)
    db.delete(task)
    db.commit()

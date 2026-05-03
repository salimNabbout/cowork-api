from pydantic import BaseModel, ConfigDict


class TaskBase(BaseModel):
    title: str
    description: str | None = None
    completed: bool = False


class TaskCreate(TaskBase):
    """Payload de entrada para criacao de task. user_id vem do path."""
    pass


class TaskUpdate(BaseModel):
    """Payload de PATCH parcial. Todos os campos opcionais."""
    title: str | None = None
    description: str | None = None
    completed: bool | None = None


class TaskRead(TaskBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)

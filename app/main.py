from fastapi import FastAPI

from app.core.config import settings
from app.models import task as task_model  # noqa: F401 - registra no Base.metadata
from app.models import user as user_model  # noqa: F401 - registra no Base.metadata
from app.routes import auth, health, tasks, users

# O schema do banco eh gerenciado por Alembic (ver migrations/).
# Para criar/atualizar tabelas, rode: alembic upgrade head

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

@app.get("/")
def root():
    return {
        "name": "FastAPI API",
        "status": "online",
        "health": "/health",
        "docs": "/docs",
    }

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tasks.router)

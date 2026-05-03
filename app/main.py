from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# CORS - precisa vir antes dos routers. allow_origins lido de
# settings.cors_origins, configuravel via env CORS_ORIGINS (CSV).
# Em producao, defina explicitamente as URLs do(s) frontend(s).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Rotas legadas, mantidas temporariamente durante transição
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tasks.router)

# Rotas versionadas
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")

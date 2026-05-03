from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings


def _normalize_database_url(url: str) -> str:
    """O Render expoe DATABASE_URL como 'postgresql://...' mas a app usa o driver
    psycopg3, que precisa de 'postgresql+psycopg://...'. Mantemos sqlite e qualquer
    URL que ja venha com driver explicito intactos.
    """
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def _build_connect_args(url: str) -> dict:
    """check_same_thread eh especifico do SQLite e quebra com outros drivers."""
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


_DATABASE_URL = _normalize_database_url(settings.DATABASE_URL)

engine = create_engine(
    _DATABASE_URL,
    connect_args=_build_connect_args(_DATABASE_URL),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency do FastAPI para abrir/fechar uma sessao por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

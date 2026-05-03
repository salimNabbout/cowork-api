from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracoes da aplicacao - lidas de env vars ou .env (na raiz do projeto)."""

    APP_NAME: str = "Cowork API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./app.db"

    # JWT
    SECRET_KEY: str = "change-me-in-production-please"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS - origens permitidas como CSV. NAO use "*" em producao.
    # Default cobre Vite dev (5173) e React dev (3000) em localhost.
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://localhost:5173,"
        "http://127.0.0.1:3000,http://127.0.0.1:5173"
    )

    @property
    def cors_origins(self) -> list[str]:
        """Lista parseada de origens permitidas, a partir de CORS_ORIGINS (CSV)."""
        return [s.strip() for s in self.CORS_ORIGINS.split(",") if s.strip()]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()

import sys
from pydantic_settings import BaseSettings
from pathlib import Path

_WEAK_KEY = "pizzaria-secret-key-change-in-production-2024"


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5433/pizzaria_checklist"
    SECRET_KEY: str = _WEAK_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    UPLOAD_DIR: str = "./uploads"
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:8082",
        "http://localhost:8001",
        "http://localhost",
        "http://127.0.0.1:8082",
    ]
    APP_NAME: str = "Pizzaria Checklist"

    # Usuários semente — lidos do .env, nunca hardcoded no código
    SEED_ADMIN_EMAIL: str = "admin@pizzaria.com"
    SEED_ADMIN_PASSWORD: str = "admin123"
    SEED_MANAGER_EMAIL: str = "gerente@pizzaria.com"
    SEED_MANAGER_PASSWORD: str = "gerente123"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def upload_path(self) -> Path:
        p = Path(self.UPLOAD_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def __init__(self, **data):
        super().__init__(**data)
        if self.SECRET_KEY == _WEAK_KEY:
            import os
            if os.getenv("ENV", "development") == "production":
                print(
                    "[SEGURANÇA] SECRET_KEY padrão detectada em produção! "
                    "Defina SECRET_KEY no .env antes de iniciar.",
                    file=sys.stderr,
                )
                sys.exit(1)


settings = Settings()

import secrets
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, EmailStr, HttpUrl, PostgresDsn, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "qxdai"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    TOTP_SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 60 * 30
    REFRESH_TOKEN_EXPIRE_SECONDS: int = 60 * 60 * 24 * 30 # 60 minutes * 24 hours * 8 days = 8 days
    JWT_ALGO: str = "HS512"
    TOTP_ALGO: str = "SHA-1"
    SERVER_NAME: str = "qxd.ai"
    #SERVER_HOST: AnyHttpUrl
    SERVER_HOST: str = "127.0.0.1"
    # BACKEND_CORS_ORIGINS is a JSON-formatted list of origins
    # e.g: '["http://localhost", "http://localhost:4200", "http://localhost:3000", \
    # "http://localhost:8080", "http://app.qxd.ai", "https://app.qxd.ai", \]'
    #BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost", "http://localhost:4200", "http://localhost:3000", "http://localhost:8080"]
    # GENERAL SETTINGS
    MULTI_MAX: int = 20
    # COMPONENT SETTINGS
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "jamesqxd"
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: str  = "qxd-local"
    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None

    @field_validator("SQLALCHEMY_DATABASE_URI")
    def assemble_db_connection(cls, v: Optional[str], info):
        if isinstance(v, str):
            return v
        user = info.data.get("POSTGRES_USER")
        password = info.data.get("POSTGRES_PASSWORD")
        host = info.data.get("POSTGRES_SERVER")
        db = info.data.get("POSTGRES_DB")

        if not all([user, host, db]):
            raise ValueError("Database connection details are incomplete")

        if password:
            return f"postgresql+asyncpg://{user}:{password}@{host}/{db}"
        else:
            return f"postgresql+asyncpg://{user}@{host}/{db}"

settings = Settings()
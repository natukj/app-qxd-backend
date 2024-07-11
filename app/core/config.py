import secrets
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, EmailStr, HttpUrl, PostgresDsn
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    # SECRET_KEY: str = secrets.token_urlsafe(32)
    PROJECT_NAME: str = "qxdai"
    # SERVER_NAME: str
    # SERVER_HOST: AnyHttpUrl
    SERVER_HOST: str = "127.0.0.1"
    # BACKEND_CORS_ORIGINS: List[str] = []
    # SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None
    # FIRST_SUPERUSER: EmailStr
    # FIRST_SUPERUSER_PASSWORD: str
    # USERS_OPEN_REGISTRATION: bool = False
    # BACKEND_CORS_ORIGINS is a JSON-formatted list of origins
    # e.g: '["http://localhost", "http://localhost:4200", "http://localhost:3000", \
    # "http://localhost:8080", "http://app.qxd.ai", "https://app.qxd.ai", \]'
    #BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost", "http://localhost:4200", "http://localhost:3000", "http://localhost:8080"]

settings = Settings()
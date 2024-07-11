from fastapi import APIRouter

from app.api.api_v1.endpoints import (
    login,
    projects,
    chat,
)

api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
from fastapi import APIRouter

from api.api_v1.endpoints import (
    login,
    projects,
    chat,
)

api_router = APIRouter()
api_router.include_router(login.router, prefix='/login', tags=["login"])
# api_router.include_router(projects.router, prefix='/projects', tags=["projects"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
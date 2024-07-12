from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import List
import db

router = APIRouter()

# Use the same secret key and algorithm as in your login.py
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class ProjectAdd(BaseModel):
    projectId: str

class Project(BaseModel):
    id: str
    name: str
    description: str

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception

@router.post("/add")
async def add_project(project: ProjectAdd, current_user: str = Depends(get_current_user)):
    try:
        success = db.add_project(current_user, project.projectId, {})
        if not success:
            raise HTTPException(status_code=400, detail="Failed to add project")
        return {"message": f"Project {project.projectId} added successfully for user {current_user}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get", response_model=List[Project])
async def get_projects(current_user: str = Depends(get_current_user)):
    try:
        projects = db.get_user_projects(current_user)
        return projects
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/get/{project_id}", response_model=Project)
async def get_project(project_id: str, current_user: str = Depends(get_current_user)):
    try:
        project = db.get_user_project(current_user, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

import crud, models, schemas
from api import deps

router = APIRouter()

PROJECT_MAPPING = {
    UUID('badbc443-b870-4fda-ae32-7db2e4bfd8b5'): {
        'name': 'Modern Awards',
        'description': 'Explore the comprehensive guide to Modern Awards in Australian employment law.',
        'project_type': 'qa'
    },
    UUID('5c909c6e-a299-4851-8567-af702cc80a1c'): {
        'name': 'Modern Award Classification',
        'description': 'Classification system within Modern Awards.',
        'project_type': 'table'
    },
    UUID('b160c07a-aa74-4a4c-a08d-016c9a989772'): {
        'name': 'Fair Work Act',
        'description': 'Dive into the Fair Work Act and its impact on Australian employment regulations.',
        'project_type': 'qa'
    },
    UUID('f614291e-9933-4945-be13-99dc0382270d'): {
        'name': 'Income Tax Assessment Act',
        'description': 'Navigate the complexities of the Income Tax Assessment Act and its provisions.',
        'project_type': 'qa'
    },
}

@router.post("/add", response_model=schemas.ProjectSchema)
async def add_project(
    project: schemas.ProjectAdd,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    print(f'project={project}')
    print(current_user)
    project_data = PROJECT_MAPPING.get(project.projectId)
    if not project_data:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    project_create = schemas.ProjectCreate(**project_data)
    new_project = await crud.project.create(db=db, obj_in=project_create, user=current_user)
    return new_project

@router.get("/get", response_model=List[schemas.ProjectSchema])
async def get_projects(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100
):
    projects = await crud.project.get_multi(db=db, user=current_user, skip=skip, limit=limit)
    return projects

@router.get("/{project_id}", response_model=schemas.ProjectSchema)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    project = await crud.project.get(db=db, id=project_id, user=current_user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
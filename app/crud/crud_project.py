from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from app.crud.base import CRUDBase
from app.models import Project, User
from app.schemas.project import ProjectCreate, ProjectUpdate

class CRUDProject(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
    async def create(self, db: AsyncSession, *, obj_in: ProjectCreate, user: User) -> Project:
        db_obj = Project(
            name=obj_in.name,
            description=obj_in.description,
            project_type=obj_in.project_type,
            user_id=user.id
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get(self, db: AsyncSession, *, id: UUID, user: User) -> Optional[Project]:
        result = await db.execute(select(Project).filter(and_(Project.id == id, Project.user_id == user.id)))
        return result.scalars().first()

    async def get_multi(self, db: AsyncSession, *, user: User, skip: int = 0, limit: int = 100) -> List[Project]:
        result = await db.execute(
            select(Project)
            .filter(Project.user_id == user.id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def update(self, db: AsyncSession, *, db_obj: Project, obj_in: ProjectUpdate) -> Project:
        update_data = obj_in.model_dump(exclude_unset=True)
        return await super().update(db, db_obj=db_obj, obj_in=update_data)

    async def remove(self, db: AsyncSession, *, id: UUID, user: User) -> Optional[Project]:
        project = await self.get(db, id=id, user=user)
        if project:
            await db.delete(project)
            await db.commit()
        return project

project = CRUDProject(Project)

from schemas.base_schema import UUIDSchema, BaseSchema
from uuid import UUID

class ProjectAdd(BaseSchema):
    projectId: UUID

class ProjectBase(BaseSchema):
    name: str
    description: str | None = None
    project_type: str

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    pass

class ProjectSchema(UUIDSchema, ProjectBase):
    user_id: UUID

class ProjectInDB(ProjectSchema):
    pass

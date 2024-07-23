from schemas.base_schema import UUIDSchema, BaseSchema
from schemas.agtable import AGTableInDB
from uuid import UUID
from pydantic import ConfigDict

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
    agtable: AGTableInDB | None = None

    model_config = ConfigDict(from_attributes=True, exclude_unset=True)

class ProjectInDB(ProjectSchema):
    pass

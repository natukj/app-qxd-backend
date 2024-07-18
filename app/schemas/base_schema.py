from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class TimestampedSchema(BaseSchema):
    created: datetime
    modified: datetime

class UUIDSchema(TimestampedSchema):
    id: UUID
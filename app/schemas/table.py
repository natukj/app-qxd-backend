from schemas.base_schema import UUIDSchema, BaseSchema
from typing import List, Dict, Any
from uuid import UUID

class ColumnSchema(BaseSchema):
    id: str
    name: str
    additional_info: str | None = None
    order_index: int

class RowSchema(BaseSchema):
    id: str
    checked: bool | None = None
    cells: Dict[str, Any]

class TableBase(BaseSchema):
    columns: List[ColumnSchema]
    rows: List[RowSchema]

class TableCreate(TableBase):
    project_id: UUID

class TableUpdate(TableBase):
    pass

class Table(UUIDSchema, TableBase):
    project_id: UUID

class TableInDB(Table):
    pass

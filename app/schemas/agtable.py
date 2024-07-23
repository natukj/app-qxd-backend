from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import Field
from schemas.base_schema import BaseSchema, UUIDSchema

class AGTableBase(BaseSchema):
    name: str = Field(..., max_length=100)

class AGTableCreate(AGTableBase):
    project_id: UUID

class AGTableUpdate(AGTableBase):
    pass

class AGTableInDB(AGTableBase, UUIDSchema):
    project_id: UUID

class AGTableColumnBase(BaseSchema):
    name: str = Field(..., max_length=100)
    order: int
    additional_info: Optional[str] = Field(None, max_length=500)

class AGTableColumnCreate(AGTableColumnBase):
    table_id: UUID

class AGTableColumnUpdate(AGTableColumnBase):
    pass

class AGTableColumnInDB(AGTableColumnBase, UUIDSchema):
    table_id: UUID

class AGTableRowBase(BaseSchema):
    order: int

class AGTableRowCreate(AGTableRowBase):
    table_id: UUID

class AGTableRowUpdate(AGTableRowBase):
    pass

class AGTableRowInDB(AGTableRowBase, UUIDSchema):
    table_id: UUID

class AGTableCellBase(BaseSchema):
    value: Dict[str, Any]

class AGTableCellCreate(AGTableCellBase):
    row_id: UUID
    column_id: UUID

class AGTableCellUpdate(AGTableCellBase):
    pass

class AGTableCellInDB(AGTableCellBase, UUIDSchema):
    row_id: UUID
    column_id: UUID

# Additional schemas for nested representations

class AGTableColumnWithCells(AGTableColumnInDB):
    cells: List[AGTableCellInDB]

class AGTableRowWithCells(AGTableRowInDB):
    cells: List[AGTableCellInDB]

class AGTableWithColumnsAndRows(AGTableInDB):
    columns: List[AGTableColumnInDB]
    rows: List[AGTableRowWithCells]

# Response models

class AGTableResponse(AGTableInDB):
    pass

class AGTableColumnResponse(AGTableColumnInDB):
    pass

class AGTableRowResponse(AGTableRowInDB):
    pass

class AGTableCellResponse(AGTableCellInDB):
    pass

class AGTableFullResponse(AGTableWithColumnsAndRows):
    pass

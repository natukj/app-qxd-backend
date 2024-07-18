from typing import TYPE_CHECKING, Optional, List
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from uuid import uuid4

from db.base_class import Base

if TYPE_CHECKING:
    from .project import Project

class Table(Base):
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modified: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        server_onupdate=func.now(), 
        nullable=False,
    )
    project_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.id"), unique=True)
    project: Mapped["Project"] = relationship(back_populates="table")
    
    # Store columns as a JSON array
    columns: Mapped[List[dict]] = mapped_column(JSONB)
    
    # Store rows as a JSON array of objects
    rows: Mapped[List[dict]] = mapped_column(JSONB)

class Column:
    def __init__(self, name: str, additional_info: Optional[str] = None, order_index: int = 0):
        self.id: str = str(uuid4())
        self.name: str = name
        self.additional_info: Optional[str] = additional_info
        self.order_index: int = order_index

class Row:
    def __init__(self, id: str, order_index: int = 0, cells: Optional[dict] = None):
        self.id: str = id  # ID passed from the frontend
        self.order_index: int = order_index
        self.cells: dict = cells or {}

# to create a Table instance when a new table project is created, and then manipulate the columns and rows as needed. For example:
# new_table = Table(
#     project_id=project.id,
#     columns=[Column("Name", order_index=0).__dict__, Column("Age", order_index=1).__dict__],
#     rows=[Row(0, {"Name": "John", "Age": "30"}).__dict__, Row(1, {"Name": "Jane", "Age": "25"}).__dict__]
# )

# Example of adding a new row
# frontend_row_id = "emp-123abc..."  # from the frontend
# new_row = Row(id=frontend_row_id, order_index=len(table.rows), cells={"Name": "John", "Age": "30"})
# table.rows.append(new_row.__dict__)


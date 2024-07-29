from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import DateTime, ForeignKey, String, Integer
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from uuid import uuid4

from db.base_class import Base

from .project import Project

class AGTable(Base):
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modified: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        server_onupdate=func.now(), 
        nullable=False,
    )
    project_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.id"))
    name: Mapped[str] = mapped_column(String(length=100), index=True)

    project_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.id"))
    project: Mapped["Project"] = relationship(back_populates="agtable")
    columns: Mapped[list["AGTableColumn"]] = relationship(back_populates="table", cascade="all, delete-orphan")
    rows: Mapped[list["AGTableRow"]] = relationship(back_populates="table", cascade="all, delete-orphan")

class AGTableColumn(Base):
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modified: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        server_onupdate=func.now(), 
        nullable=False,
    )
    table_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agtable.id"))
    name: Mapped[str] = mapped_column(String(length=100), index=True)
    order: Mapped[int] = mapped_column(Integer)
    additional_info: Mapped[Optional[str]] = mapped_column(String(length=500), nullable=True)

    table: Mapped["AGTable"] = relationship(back_populates="columns")
    cells: Mapped[list["AGTableCell"]] = relationship(back_populates="column", cascade="all, delete-orphan")

class AGTableRow(Base):
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modified: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        server_onupdate=func.now(), 
        nullable=False,
    )
    table_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agtable.id"))
    order: Mapped[int] = mapped_column(Integer)

    table: Mapped["AGTable"] = relationship(back_populates="rows")
    cells: Mapped[list["AGTableCell"]] = relationship(back_populates="row", cascade="all, delete-orphan")

class AGTableCell(Base):
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modified: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        server_onupdate=func.now(), 
        nullable=False,
    )
    row_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agtablerow.id"))
    column_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agtablecolumn.id"))
    value: Mapped[dict] = mapped_column(JSONB)

    row: Mapped["AGTableRow"] = relationship(back_populates="cells")
    column: Mapped["AGTableColumn"] = relationship(back_populates="cells")
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4

from app.db.base_class import Base

if TYPE_CHECKING:
    from .user import User
    from .table import Table

class Project(Base):
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modified: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        server_onupdate=func.now(), 
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(length=100), index=True)
    description: Mapped[Optional[str]] = mapped_column(String(length=500), nullable=True)
    project_type: Mapped[str] = mapped_column(String(length=50))  # e.g., 'table', 'qa', etc.
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"))
    user: Mapped["User"] = relationship(back_populates="projects")
    table: Mapped[Optional["Table"]] = relationship(back_populates="project", uselist=False, cascade="all, delete-orphan")

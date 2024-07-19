from typing import List, Optional, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from crud.base import CRUDBase
from models.table import Table
from models.project import Project
from schemas.table import TableCreate, TableUpdate, ColumnSchema, RowSchema

# from models import lazy_load
# lazy_load()

class CRUDTable(CRUDBase[Table, TableCreate, TableUpdate]):
    async def create(self, db: AsyncSession, *, obj_in: TableCreate, project: Project) -> Table:
        db_obj = Table(
            project_id=project.id,
            columns=[column.model_dump() for column in obj_in.columns],
            rows=[row.model_dump() for row in obj_in.rows]
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get(self, db: AsyncSession, *, project_id: UUID) -> Optional[Table]:
        result = await db.execute(select(Table).filter(Table.project_id == project_id))
        return result.scalars().first()

    async def update(self, db: AsyncSession, *, db_obj: Table, obj_in: TableUpdate) -> Table:
        update_data = obj_in.model_dump(exclude_unset=True)
        if 'columns' in update_data:
            update_data['columns'] = [column.model_dump() for column in update_data['columns']]
        if 'rows' in update_data:
            update_data['rows'] = [row.model_dump() for row in update_data['rows']]
        return await super().update(db, db_obj=db_obj, obj_in=update_data)

    async def add_column(self, db: AsyncSession, *, table: Table, column: ColumnSchema) -> Table:
        table.columns.append(column.model_dump())
        await db.commit()
        await db.refresh(table)
        return table

    async def remove_column(self, db: AsyncSession, *, table: Table, column_id: str) -> Table:
        table.columns = [col for col in table.columns if col['id'] != column_id]
        table.rows = [{k: v for k, v in row.items() if k != column_id} for row in table.rows]
        await db.commit()
        await db.refresh(table)
        return table

    async def add_row(self, db: AsyncSession, *, table: Table, row: RowSchema) -> Table:
        table.rows.append(row.model_dump())
        await db.commit()
        await db.refresh(table)
        return table

    async def remove_row(self, db: AsyncSession, *, table: Table, row_id: str) -> Table:
        table.rows = [row for row in table.rows if row['id'] != row_id]
        await db.commit()
        await db.refresh(table)
        return table

    async def update_cell(self, db: AsyncSession, *, table: Table, row_id: str, column_id: str, value: Any) -> Table:
        for row in table.rows:
            if row['id'] == row_id:
                row['cells'][column_id] = value
                break
        await db.commit()
        await db.refresh(table)
        return table

table = CRUDTable(Table)

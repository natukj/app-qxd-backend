from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from crud.base import CRUDBase
from models.agtable import AGTable, AGTableColumn, AGTableRow, AGTableCell
from schemas.agtable import (
    AGTableCreate, AGTableUpdate,
    AGTableColumnCreate, AGTableColumnUpdate,
    AGTableRowCreate, AGTableRowUpdate,
    AGTableCellCreate, AGTableCellUpdate
)

class CRUDAGTable(CRUDBase[AGTable, AGTableCreate, AGTableUpdate]):
    async def get_by_project(self, db: AsyncSession, *, project_id: UUID) -> Optional[AGTable]:
        result = await db.execute(select(AGTable).filter(AGTable.project_id == project_id))
        return result.scalars().first()
    
    async def get_row_count(self, db: AsyncSession, *, table_id: UUID) -> int:
        result = await db.execute(
            select(func.count()).select_from(AGTableRow).filter(AGTableRow.table_id == table_id)
        )
        return result.scalar_one()
    
    async def create_with_columns(
        self, db: AsyncSession, *, obj_in: AGTableCreate, columns: List[AGTableColumnCreate]
    ) -> AGTable:
        db_obj = AGTable(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()

        for col in columns:
            db_column = AGTableColumn(**col.model_dump(), table_id=db_obj.id)
            db.add(db_column)

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_full_table(self, db: AsyncSession, table_id: UUID) -> Optional[Dict[str, Any]]:
        result = await db.execute(
            select(AGTable, AGTableColumn, AGTableRow, AGTableCell)
            .join(AGTableColumn, AGTable.id == AGTableColumn.table_id)
            .join(AGTableRow, AGTable.id == AGTableRow.table_id)
            .join(AGTableCell, (AGTableRow.id == AGTableCell.row_id) & (AGTableColumn.id == AGTableCell.column_id))
            .filter(AGTable.id == table_id)
        )
        rows = result.all()
        if not rows:
            return None

        table_data = {
            "id": rows[0].AGTable.id,
            "name": rows[0].AGTable.name,
            "columns": [],
            "rows": []
        }

        columns = {}
        rows_data = {}

        for row in rows:
            if row.AGTableColumn.id not in columns:
                columns[row.AGTableColumn.id] = {
                    "id": row.AGTableColumn.id,
                    "name": row.AGTableColumn.name,
                    "order": row.AGTableColumn.order,
                    "additional_info": row.AGTableColumn.additional_info
                }

            if row.AGTableRow.id not in rows_data:
                rows_data[row.AGTableRow.id] = {
                    "id": row.AGTableRow.id,
                    "order": row.AGTableRow.order,
                    "cells": {}
                }

            rows_data[row.AGTableRow.id]["cells"][row.AGTableColumn.id] = {
                "id": row.AGTableCell.id,
                "value": row.AGTableCell.value
            }

        table_data["columns"] = sorted(columns.values(), key=lambda x: x["order"])
        table_data["rows"] = sorted(rows_data.values(), key=lambda x: x["order"])

        return table_data

class CRUDAGTableColumn(CRUDBase[AGTableColumn, AGTableColumnCreate, AGTableColumnUpdate]):
    async def get_by_table(self, db: AsyncSession, *, table_id: UUID) -> List[AGTableColumn]:
        result = await db.execute(select(AGTableColumn).filter(AGTableColumn.table_id == table_id))
        return result.scalars().all()

    async def get_by_name(self, db: AsyncSession, *, table_id: UUID, name: str) -> Optional[AGTableColumn]:
        result = await db.execute(
            select(AGTableColumn).filter(AGTableColumn.table_id == table_id, AGTableColumn.name == name)
        )
        return result.scalars().first()

    async def get_column_count(self, db: AsyncSession, *, table_id: UUID) -> int:
        result = await db.execute(
            select(func.count()).select_from(AGTableColumn).filter(AGTableColumn.table_id == table_id)
        )
        return result.scalar_one()

class CRUDAGTableRow(CRUDBase[AGTableRow, AGTableRowCreate, AGTableRowUpdate]):
    async def create_with_cells(
        self, db: AsyncSession, *, obj_in: AGTableRowCreate, cells: List[AGTableCellCreate]
    ) -> AGTableRow:
        db_obj = AGTableRow(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()

        for cell in cells:
            db_cell = AGTableCell(**cell.model_dump(), row_id=db_obj.id)
            db.add(db_cell)

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_by_table(self, db: AsyncSession, *, table_id: UUID) -> List[AGTableRow]:
        result = await db.execute(select(AGTableRow).filter(AGTableRow.table_id == table_id))
        return result.scalars().all()

class CRUDAGTableCell(CRUDBase[AGTableCell, AGTableCellCreate, AGTableCellUpdate]):
    async def get_by_row(self, db: AsyncSession, *, row_id: UUID) -> List[AGTableCell]:
        result = await db.execute(select(AGTableCell).filter(AGTableCell.row_id == row_id))
        return result.scalars().all()

    async def update_or_create(self, db: AsyncSession, *, obj_in: AGTableCellCreate) -> AGTableCell:
        result = await db.execute(
            select(AGTableCell).filter(
                AGTableCell.row_id == obj_in.row_id,
                AGTableCell.column_id == obj_in.column_id
            )
        )
        cell = result.scalars().first()

        if cell:
            cell.value = obj_in.value
        else:
            cell = AGTableCell(**obj_in.model_dump())
            db.add(cell)

        await db.commit()
        await db.refresh(cell)
        return cell

agtable = CRUDAGTable(AGTable)
agtable_column = CRUDAGTableColumn(AGTableColumn)
agtable_row = CRUDAGTableRow(AGTableRow)
agtable_cell = CRUDAGTableCell(AGTableCell)

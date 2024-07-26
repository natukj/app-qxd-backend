from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from neo4j import AsyncSession as Neo4jAsyncSession
import asyncio
from typing import List, Dict, Any
from uuid import UUID
import json

import crud, models, schemas, dummy, agents
from db import ma_db
from api import deps

router = APIRouter()

PROJECT_MAPPING = {
    UUID('badbc443-b870-4fda-ae32-7db2e4bfd8b5'): {
        'name': 'Modern Awards',
        'description': 'Explore the comprehensive guide to Modern Awards in Australian employment law.',
        'project_type': 'qa'
    },
    UUID('5c909c6e-a299-4851-8567-af702cc80a1c'): {
        'name': 'Modern Award Classification',
        'description': 'Classification system within Modern Awards.',
        'project_type': 'table'
    },
    UUID('b160c07a-aa74-4a4c-a08d-016c9a989772'): {
        'name': 'Fair Work Act',
        'description': 'Dive into the Fair Work Act and its impact on Australian employment regulations.',
        'project_type': 'qa'
    },
    UUID('f614291e-9933-4945-be13-99dc0382270d'): {
        'name': 'Income Tax Assessment Act',
        'description': 'Navigate the complexities of the Income Tax Assessment Act and its provisions.',
        'project_type': 'qa'
    },
}

@router.post("/add", response_model=schemas.ProjectSchema)
async def add_project(
    project: schemas.ProjectAdd,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    project_data = PROJECT_MAPPING.get(project.projectId)
    if not project_data:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    project_create = schemas.ProjectCreate(**project_data)
    new_project = await crud.project.create(db=db, obj_in=project_create, user=current_user)

    if new_project.project_type == 'table':
        agtable_create = schemas.AGTableCreate(name=new_project.name, project_id=new_project.id)
        await crud.agtable.create(db=db, obj_in=agtable_create)
        await db.refresh(new_project, ['agtable'])

    return new_project

@router.get("/get", response_model=List[schemas.ProjectSchema])
async def get_projects(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100
):
    projects = await crud.project.get_multi(db=db, user=current_user, skip=skip, limit=limit)
    return projects

@router.get("/{project_id}", response_model=schemas.ProjectSchema)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    project = await crud.project.get(db=db, id=project_id, user=current_user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

### Modern Award Classification endpoints
@router.get("/{project_id}/table")
async def get_project_table(
    project_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    table = await crud.agtable.get_by_project(db=db, project_id=project_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    full_table = await crud.agtable.get_full_table(db=db, table_id=table.id)
    return full_table


@router.post("/{project_id}/rows/add")
async def add_project_row(
    project_id: UUID,
    row_data: Dict[str, Any],
    db: AsyncSession = Depends(deps.get_db),
    gdb: Neo4jAsyncSession = Depends(deps.get_gdb),
    current_user: models.User = Depends(deps.get_current_user)
):  
    print(row_data)
    project = await crud.project.get(db=db, id=project_id, user=current_user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.agtable:
        raise HTTPException(status_code=400, detail="This project does not have an associated table")

    employee_column = await crud.agtable_column.get_by_name(db=db, table_id=project.agtable.id, name='Employee')
    if not employee_column:
        employee_column = await crud.agtable_column.create(db=db, obj_in=schemas.AGTableColumnCreate(
            table_id=project.agtable.id,
            name='Employee',
            order=1
        ))

    row_count = await crud.agtable.get_row_count(db=db, table_id=project.agtable.id)

    row_create_data = {
        "table_id": project.agtable.id,
        "order": row_count + 1
    }

    # include the ID if it's present in row_data
    if 'id' in row_data:
        row_create_data["id"] = UUID(row_data['id'])
        new_row = await crud.agtable_row.create_with_id(db=db, obj_in=schemas.AGTableRowCreate(**row_create_data))
    else:
        new_row = await crud.agtable_row.create(db=db, obj_in=schemas.AGTableRowCreate(**row_create_data))

    # create the 'Employee' cell with EmployeeData (conforming to FE schema)
    employee_data = row_data.get('EmployeeData', {})
    employee_name = employee_data.get('fullName', '')
    employee_cell_data = schemas.AGTableCellCreate(
        row_id=new_row.id,
        column_id=employee_column.id,
        value={
            "Employee": employee_name,
            "EmployeeData": employee_data
        }
    )
    await crud.agtable_cell.create(db=db, obj_in=employee_cell_data)

    # gdb retrieval
    industry = employee_data.get('industry')
    subindustry = employee_data.get('subIndustry')

    award_data = ma_db.get_awards(industry, subindustry)

    if not award_data:
        print("No awards found for the given industry and subindustry.")
        # Handle the case where no awards are found
        return {"error": "No awards found for the given industry and subindustry."}

    tasks = [crud.ma_gdb.get_award_coverage_clauses(gdb, [award]) for award in award_data]
    results = await asyncio.gather(*tasks)
    award_info = ""
    for award, (output_str, references) in zip(award_data, results):
        print('\n\n\n')
        print(f"Award: {award}")  # Print the entire award dictionary
        print(f"Output preview: {output_str[:200]}...")
        print(f"Number of references: {len(references)}")
        award_info += output_str

    # function to stream the row data
    async def generate_row_data_stream():
        async for result in agents.generate_row_data(gdb, row_data, award_info):
            # For each piece of generated data, create or update the corresponding cell
            for column_name, value in result.items():
                # get or create the column
                column = await crud.agtable_column.get_by_name(db=db, table_id=project.agtable.id, name=column_name)
                if not column:
                    column_count = await crud.agtable_column.get_column_count(db=db, table_id=project.agtable.id)
                    column = await crud.agtable_column.create(db=db, obj_in=schemas.AGTableColumnCreate(
                        table_id=project.agtable.id,
                        name=column_name,
                        order=column_count + 1
                    ))

                # create or update the cell
                cell_data = schemas.AGTableCellCreate(
                    row_id=new_row.id,
                    column_id=column.id,
                    value=value
                )
                await crud.agtable_cell.update_or_create(db=db, obj_in=cell_data)
            # TODO send references
            yield json.dumps(result) + "\n"

    return StreamingResponse(generate_row_data_stream(), media_type="application/x-ndjson")

@router.post("/{project_id}/rows/delete")
async def delete_project_rows(
    project_id: UUID,
    row_ids: List[UUID] = Body(..., embed=True),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    project = await crud.project.get(db=db, id=project_id, user=current_user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.agtable:
        raise HTTPException(status_code=400, detail="This project does not have an associated table")

    # delete the rows (and associated cells first)
    deleted_rows = await crud.agtable_row.remove_multi(db=db, ids=row_ids, table_id=project.agtable.id)

    if len(deleted_rows) != len(row_ids):
        raise HTTPException(status_code=400, detail="Some rows could not be deleted")

    return {"message": f"Successfully deleted {len(deleted_rows)} rows and their associated cells"}

@router.post("/{project_id}/columns/add")
async def add_project_column(
    project_id: UUID,
    column_data: Dict[str, str] = Body(..., embed=True),
    rows: List[Dict[str, Any]] = Body(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    project = await crud.project.get(db=db, id=project_id, user=current_user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.agtable:
        raise HTTPException(status_code=400, detail="This project does not have an associated table")

    column_count = await crud.agtable_column.get_column_count(db=db, table_id=project.agtable.id)

    new_column = await crud.agtable_column.create(
        db=db,
        obj_in=schemas.AGTableColumnCreate(
            table_id=project.agtable.id,
            name=column_data['name'],
            order=column_count + 1,
            additional_info=column_data.get('additionalInfo', '')
        )
    )

    async def generate_column_data_stream():
        async for result in dummy.generate_column_data(column_data['name'], column_data.get('additionalInfo', ''), rows):
            for row_id, column_value in result.items():
                # create or update the cell for this row and the new column
                cell_data = schemas.AGTableCellCreate(
                    row_id=UUID(row_id),
                    column_id=new_column.id,
                    value=column_value
                )
                await crud.agtable_cell.update_or_create(db=db, obj_in=cell_data)

                yield json.dumps({row_id: column_value}) + "\n"

    return StreamingResponse(generate_column_data_stream(), media_type="application/x-ndjson")

@router.post("/{project_id}/columns/delete")
async def delete_project_column(
    project_id: UUID,
    column_data: Dict[str, str] = Body(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    project = await crud.project.get(db=db, id=project_id, user=current_user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.agtable:
        raise HTTPException(status_code=400, detail="This project does not have an associated table")

    column_name = column_data.get('column_name') # column names are enforced unique on frontend
    if not column_name:
        raise HTTPException(status_code=400, detail="Column name is required")

    column = await crud.agtable_column.get_by_name(db, table_id=project.agtable.id, name=column_name)
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")

    # delete the column and its associated cells
    await crud.agtable_column.remove(db, id=column.id)
    # reorder remaining columns
    await crud.agtable_column.reorder_columns(db, table_id=project.agtable.id)

    return {"message": f"Column '{column_name}' and its associated cells have been deleted"}
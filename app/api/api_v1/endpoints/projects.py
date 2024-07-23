from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from uuid import UUID
import json

import crud, models, schemas, dummy
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

@router.post("/{project_id}/rows/add")
async def add_project_row(
    project_id: UUID,
    row_data: Dict[str, Any],
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    # Check if the project exists and the user has access to it
    project = await crud.project.get(db=db, id=project_id, user=current_user)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if the project has an associated AGTable
    if not project.agtable:
        raise HTTPException(status_code=400, detail="This project does not have an associated table")

    # Get the current row count
    row_count = await crud.agtable.get_row_count(db=db, table_id=project.agtable.id)

    # Create a new row in the database
    new_row = await crud.agtable_row.create(
        db=db, 
        obj_in=schemas.AGTableRowCreate(table_id=project.agtable.id, order=row_count + 1)
    )

    # Function to stream the row data
    async def generate_row_data_stream():
        async for result in dummy.generate_row_data(row_data):
            # For each piece of generated data, create or update the corresponding cell
            for column_name, value in result.items():
                # Get or create the column
                column = await crud.agtable_column.get_by_name(db=db, table_id=project.agtable.id, name=column_name)
                if not column:
                    column_count = await crud.agtable_column.get_column_count(db=db, table_id=project.agtable.id)
                    column = await crud.agtable_column.create(db=db, obj_in=schemas.AGTableColumnCreate(
                        table_id=project.agtable.id,
                        name=column_name,
                        order=column_count + 1
                    ))

                # Create or update the cell
                cell_data = schemas.AGTableCellCreate(
                    row_id=new_row.id,
                    column_id=column.id,
                    value=value
                )
                await crud.agtable_cell.update_or_create(db=db, obj_in=cell_data)

            # Yield the result
            yield json.dumps(result) + "\n"

    return StreamingResponse(generate_row_data_stream(), media_type="application/x-ndjson")

# ### Modern Award Classification endpoints
# @router.get("/{project_id}/rows", response_model=List[schemas.RowSchema])
# async def get_project_rows(
#     project_id: UUID,
#     db: AsyncSession = Depends(deps.get_db),
#     current_user: models.User = Depends(deps.get_current_user)
# ):
#     project = await crud.project.get(db=db, id=project_id, user=current_user)
#     if not project:
#         raise HTTPException(status_code=404, detail="Project not found")
    
#     table = await crud.table.get(db=db, project_id=project_id)
#     if not table:
#         raise HTTPException(status_code=404, detail="Table not found")
    
#     return table.rows

# @router.post("/{project_id}/rows/add")
# async def add_project_row(
#     project_id: UUID,
#     row_data: Dict[str, Any],
#     db: AsyncSession = Depends(deps.get_db),
#     current_user: models.User = Depends(deps.get_current_user)
# ):
#     project = await crud.project.get(db=db, id=project_id, user=current_user)
#     if not project:
#         raise HTTPException(status_code=404, detail="Project not found")
    
#     table = await crud.table.get(db=db, project_id=project_id)
#     if not table:
#         raise HTTPException(status_code=404, detail="Table not found")
    
#     print(f'row_data={row_data}')
    
#     # Add the initial row data
#     initial_row_schema = schemas.RowSchema(
#         id=row_data['id'],
#         cells={
#             'Employee': row_data['Employee'],
#             'EmployeeData': row_data['EmployeeData']
#         }
#     )
#     table = await crud.table.add_row(db=db, table=table, row=initial_row_schema)

#     async def generate():
#         try:
#             # Generate and yield additional data
#             async for result in dummy.generate_row_data(row_data):
#                 yield json.dumps(result) + "\n"
                
#                 # Update the row in the database
#                 for row in table.rows:
#                     if row['id'] == row_data['id']:
#                         row['cells'].update(result)
#                         break
                
#                 await db.commit()
#                 await db.refresh(table)
                
#         except Exception as e:
#             yield json.dumps({"error": str(e)}) + "\n"

#     return StreamingResponse(generate(), media_type="application/x-ndjson")


# @router.post("/{project_id}/columns/add")
# async def add_project_column(
#     project_id: UUID,
#     column_data: schemas.ColumnSchema,
#     db: AsyncSession = Depends(deps.get_db),
#     current_user: models.User = Depends(deps.get_current_user)
# ):
#     project = await crud.project.get(db=db, id=project_id, user=current_user)
#     if not project:
#         raise HTTPException(status_code=404, detail="Project not found")
    
#     table = await crud.table.get(db=db, project_id=project_id)
#     if not table:
#         raise HTTPException(status_code=404, detail="Table not found")

#     async def generate():
#         try:
#             # Add the new column to the table
#             updated_table = await crud.table.add_column(db=db, table=table, column=column_data)
            
#             # Generate dummy data for the new column
#             async for result in dummy.generate_column_data(column_data.name, column_data.additional_info, updated_table.rows):
#                 yield json.dumps(result) + "\n"
                
#                 # Update the cell in the database
#                 for row_id, cell_data in result.items():
#                     await crud.table.update_cell(db=db, table=updated_table, row_id=row_id, column_id=column_data.id, value=cell_data[column_data.name])
#         except Exception as e:
#             yield json.dumps({"error": str(e)}) + "\n"

#     return StreamingResponse(generate(), media_type="application/x-ndjson")

# @router.put("/{project_id}/columns/edit")
# async def edit_project_column(
#     project_id: UUID,
#     old_column_id: str,
#     new_column_data: schemas.ColumnSchema,
#     db: AsyncSession = Depends(deps.get_db),
#     current_user: models.User = Depends(deps.get_current_user)
# ):
#     project = await crud.project.get(db=db, id=project_id, user=current_user)
#     if not project:
#         raise HTTPException(status_code=404, detail="Project not found")
    
#     table = await crud.table.get(db=db, project_id=project_id)
#     if not table:
#         raise HTTPException(status_code=404, detail="Table not found")

#     async def generate():
#         try:
#             # Remove old column
#             table = await crud.table.remove_column(db=db, table=table, column_id=old_column_id)
            
#             # Add new column
#             updated_table = await crud.table.add_column(db=db, table=table, column=new_column_data)
            
#             # Generate dummy data for the new column
#             async for result in dummy.generate_column_data(new_column_data.name, new_column_data.additional_info, updated_table.rows):
#                 yield json.dumps(result) + "\n"
                
#                 # Update the cell in the database
#                 for row_id, cell_data in result.items():
#                     await crud.table.update_cell(db=db, table=updated_table, row_id=row_id, column_id=new_column_data.id, value=cell_data[new_column_data.name])
#         except Exception as e:
#             yield json.dumps({"error": str(e)}) + "\n"

#     return StreamingResponse(generate(), media_type="application/x-ndjson")

# @router.delete("/{project_id}/columns/{column_id}", response_model=schemas.Table)
# async def delete_project_column(
#     project_id: UUID,
#     column_id: str,
#     db: AsyncSession = Depends(deps.get_db),
#     current_user: models.User = Depends(deps.get_current_user)
# ):
#     project = await crud.project.get(db=db, id=project_id, user=current_user)
#     if not project:
#         raise HTTPException(status_code=404, detail="Project not found")
    
#     table = await crud.table.get(db=db, project_id=project_id)
#     if not table:
#         raise HTTPException(status_code=404, detail="Table not found")
    
#     updated_table = await crud.table.remove_column(db=db, table=table, column_id=column_id)
#     return updated_table

# @router.post("/{project_id}/rows/delete", response_model=schemas.Table)
# async def delete_project_rows(
#     project_id: UUID,
#     row_ids: List[str],
#     db: AsyncSession = Depends(deps.get_db),
#     current_user: models.User = Depends(deps.get_current_user)
# ):
#     project = await crud.project.get(db=db, id=project_id, user=current_user)
#     if not project:
#         raise HTTPException(status_code=404, detail="Project not found")
    
#     table = await crud.table.get(db=db, project_id=project_id)
#     if not table:
#         raise HTTPException(status_code=404, detail="Table not found")
    
#     for row_id in row_ids:
#         table = await crud.table.remove_row(db=db, table=table, row_id=row_id)
    
#     return table


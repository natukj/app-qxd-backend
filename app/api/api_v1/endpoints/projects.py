# from fastapi import APIRouter, Depends, HTTPException
# from fastapi.responses import StreamingResponse
# from fastapi.security import OAuth2PasswordBearer
# from jose import JWTError, jwt
# from pydantic import BaseModel
# from typing import List, Dict, Any, Optional
# import json
# import db

# router = APIRouter()

# # Use the same secret key and algorithm as in your login.py
# SECRET_KEY = "your-secret-key"
# ALGORITHM = "HS256"

# class Row(BaseModel):
#     id: str
#     checked: Optional[bool] = False
#     data: Dict[str, Any]

# class ColumnAdd(BaseModel):
#     name: str
#     additionalInfo: str

# class ColumnEdit(BaseModel):
#     oldName: str
#     newName: str
#     additionalInfo: str

# class RowsDelete(BaseModel):
#     rowIds: List[str]

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# class ProjectAdd(BaseModel):
#     projectId: str

# class Projecttest(BaseModel):
#     id: str
#     name: str
#     description: str

# def get_current_user(token: str = Depends(oauth2_scheme)):
#     credentials_exception = HTTPException(
#         status_code=401,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         username: str = payload.get("sub")
#         if username is None:
#             raise credentials_exception
#         return username
#     except JWTError:
#         raise credentials_exception

# @router.post("/add")
# async def add_project(project: ProjectAdd, current_user: str = Depends(get_current_user)):
#     try:
#         success = db.add_project(current_user, project.projectId, {})
#         if not success:
#             raise HTTPException(status_code=400, detail="Failed to add project")
#         return {"message": f"Project {project.projectId} added successfully for user {current_user}"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @router.get("/get", response_model=List[Projecttest])
# async def get_projects(current_user: str = Depends(get_current_user)):
#     try:
#         projects = db.get_user_projects(current_user)
#         return projects
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
    
# @router.get("/get/{project_id}", response_model=Projecttest)
# async def get_project(project_id: str, current_user: str = Depends(get_current_user)):
#     try:
#         project = db.get_user_project(current_user, project_id)
#         if not project:
#             raise HTTPException(status_code=404, detail="Project not found")
#         return project
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
    
# # modern award classification endpoints
# @router.get("/get/{project_id}/rows", response_model=List[Row])
# async def get_project_rows(project_id: str, current_user: str = Depends(get_current_user)):
#     try:
#         rows = db.get_project_rows(current_user, project_id)
#         return rows
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/get/{project_id}/rows/add")
# async def add_project_row(project_id: str, row_data: Dict[str, Any], current_user: str = Depends(get_current_user)):
#     async def generate():
#         try:
#             async for result in db.add_project_row(current_user, project_id, row_data):
#                 yield json.dumps(result) + "\n"
#         except Exception as e:
#             yield json.dumps({"error": str(e)}) + "\n"

#     return StreamingResponse(generate(), media_type="application/x-ndjson")

# @router.post("/get/{project_id}/columns/add")
# async def add_project_column(
#     project_id: str, 
#     column_data: Dict[str, Any], 
#     rows: List[Dict[str, Any]],
#     current_user: str = Depends(get_current_user)
# ):
#     column_name = column_data['name']
#     additional_info = column_data.get('additionalInfo', '')

#     async def generate():
#         try:
#             async for result in db.add_project_column(current_user, project_id, column_name, additional_info, rows):
#                 yield json.dumps(result) + "\n"
#         except Exception as e:
#             yield json.dumps({"error": str(e)}) + "\n"

#     return StreamingResponse(generate(), media_type="application/x-ndjson")


# @router.put("/get/{project_id}/columns/edit")
# async def edit_project_column_endpoint(
#     project_id: str,
#     column_data: Dict[str, Any],
#     rows: List[Dict[str, Any]],
#     current_user: str = Depends(get_current_user)
# ):
#     old_column_name = column_data['oldColumnName']
#     new_column_name = column_data['newColumnName']
#     additional_info = column_data['additionalInfo']
    
#     async def generate():
#         try:
#             async for result in db.edit_project_column(current_user, project_id, old_column_name, new_column_name, additional_info, rows):
#                 yield json.dumps(result) + "\n"
#         except Exception as e:
#             yield json.dumps({"error": str(e)}) + "\n"

#     return StreamingResponse(generate(), media_type="application/x-ndjson")

# @router.delete("/get/{project_id}/columns/{column_name}", response_model=Dict[str, Any])
# async def delete_project_column(project_id: str, column_name: str, current_user: str = Depends(get_current_user)):
#     try:
#         updated_columns = db.delete_project_column(current_user, project_id, column_name)
#         return {"columns": updated_columns}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/get/{project_id}/rows/delete", response_model=Dict[str, Any])
# async def delete_project_rows(project_id: str, rows: RowsDelete, current_user: str = Depends(get_current_user)):
#     try:
#         remaining_rows = db.delete_project_rows(current_user, project_id, rows.rowIds)
#         return {"remainingRows": remaining_rows}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

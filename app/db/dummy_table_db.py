import json
import asyncio
from typing import AsyncGenerator, Dict, List, Any, Tuple
from pathlib import Path
import random

TABLE_DB_PATH = Path(__file__).parent / "dummy_table_db.json"

def read_table_db() -> Dict[str, Any]:
    if not TABLE_DB_PATH.exists():
        return {"users": {}}
    with open(TABLE_DB_PATH, "r") as f:
        return json.load(f)

def write_table_db(data: Dict[str, Any]):
    with open(TABLE_DB_PATH, "w") as f:
        json.dump(data, f, indent=4)

def get_user_project_data(user: str, project_id: str) -> Dict[str, Any]:
    db = read_table_db()
    user_data = db["users"].get(user, {})
    return user_data.get("projects", {}).get(project_id, {"rows": [], "columns": []})

def get_project_rows(user: str, project_id: str) -> List[Dict[str, Any]]:
    project = get_user_project_data(user, project_id)
    return project.get("rows", [])

def get_project_columns(user: str, project_id: str) -> List[Dict[str, Any]]:
    project = get_user_project_data(user, project_id)
    return project.get("columns", [])

async def add_project_row(user: str, project_id: str, row_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    db = read_table_db()
    if user not in db["users"]:
        db["users"][user] = {"projects": {}}
    if project_id not in db["users"][user]["projects"]:
        db["users"][user]["projects"][project_id] = {"rows": [], "columns": []}

    # # Store the initial row as received from the frontend
    # db["users"][user]["projects"][project_id]["rows"].append(row_data)
    # write_table_db(db)

    columns_to_process = row_data.pop('Columns', {})
    # Determine Classification and Award
    award, classification = await determine_classification_and_award(row_data["EmployeeData"])
    row_data["Award"] = award
    row_data["Classification"] = classification
    yield {"Award": award, "Classification": classification}

    # # Update the stored row
    # for row in db["users"][user]["projects"][project_id]["rows"]:
    #     if row["id"] == row_data["id"]:
    #         row["Award"] = award
    #         row["Classification"] = classification
    #         break
    # write_table_db(db)

    async def process_column(column_name: str, value: str) -> Tuple[str, str]:
        if value == "":
            print(f"Processing column: {column_name}")
            column_data = await determine_column_data(column_name, row_data)
            return column_name, column_data
        return column_name, value
    
    columns_to_process = {k: v for k, v in columns_to_process.items() if k not in ["Award", "Classification"]}
    tasks = [process_column(column_name, value) for column_name, value in columns_to_process.items()]

    for future in asyncio.as_completed(tasks):
        column_name, column_data = await future
        row_data[column_name] = column_data
        print(f"Yielding data for column {column_name}: {column_data}")
        yield {column_name: column_data}

        # # Update the stored row
        # for row in db["users"][user]["projects"][project_id]["rows"]:
        #     if row["id"] == row_data["id"]:
        #         row[column_name] = column_data
        #         break
        # write_table_db(db)

async def determine_classification_and_award(employee_data: Dict[str, Any]) -> tuple[str, str]:
    load_time = random.randint(1, 5)
    await asyncio.sleep(load_time)
    full_name = employee_data["fullName"]
    award_name = f"{full_name} Award"
    award_id = f"MA000{random.randint(10, 99)}"
    
    award_data = {
        award_name: {
            "award_id": award_id
        }
    }
    classification = f"{full_name} Classification"
    return award_data, classification

async def add_project_column(user: str, project_id: str, column_name: str, additional_info: str, rows: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
    db = read_table_db()
    if user not in db["users"]:
        db["users"][user] = {"projects": {}}
    if project_id not in db["users"][user]["projects"]:
        db["users"][user]["projects"][project_id] = {"rows": [], "columns": []}
    
    new_column = {
        "name": column_name,
        "additionalInfo": additional_info
    }
    # db["users"][user]["projects"][project_id]["columns"].append(new_column)
    # write_table_db(db)

    print(f"Processing new column {column_name} for all rows")

    async def process_row_column(row: Dict[str, Any]) -> Tuple[str, str, Any]:
        row_id = row['id']
        column_data = await determine_column_data(column_name, row)
        return row_id, column_name, column_data

    # Create tasks for processing the new column for each row
    tasks = [process_row_column(row) for row in rows]

    # Process rows concurrently and yield results as they become available
    for future in asyncio.as_completed(tasks):
        row_id, column, data = await future
        print(f"Yielding data for row {row_id}, column {column}: {data}")
        yield {row_id: {column: data}}

        # # Update the stored row
        # for row in db["users"][user]["projects"][project_id]["rows"]:
        #     if row["id"] == row_id:
        #         row[column] = data
        #         break
        # write_table_db(db)

async def determine_column_data(column_name: str, row_data: Dict[str, Any]) -> str:
    load_time = random.randint(1, 5)
    await asyncio.sleep(load_time) 
    full_name = row_data["EmployeeData"]["fullName"]
    # This is a placeholder. In a real scenario, this would involve specific logic for each column
    return f"{full_name}: {column_name}"

async def edit_project_column(user: str, project_id: str, old_column_name: str, new_column_name: str, additional_info: str, rows: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
    delete_project_column(user, project_id, old_column_name)
    
    async for result in add_project_column(user, project_id, new_column_name, additional_info, rows):
        yield result


def delete_project_column(user: str, project_id: str, column_name: str) -> List[Dict[str, Any]]:
    db = read_table_db()
    if user not in db["users"] or project_id not in db["users"][user]["projects"]:
        raise ValueError("Project not found")
    
    db["users"][user]["projects"][project_id]["columns"] = [col for col in db["users"][user]["projects"][project_id]["columns"] if col["name"] != column_name]
    
    # Remove the column from all rows
    for row in db["users"][user]["projects"][project_id]["rows"]:
        row["data"].pop(column_name, None)
    
    write_table_db(db)
    return db["users"][user]["projects"][project_id]["columns"]

def delete_project_rows(user: str, project_id: str, row_ids: List[str]) -> List[Dict[str, Any]]:
    db = read_table_db()
    if user not in db["users"] or project_id not in db["users"][user]["projects"]:
        raise ValueError("Project not found")
    
    db["users"][user]["projects"][project_id]["rows"] = [row for row in db["users"][user]["projects"][project_id]["rows"] if row["id"] not in row_ids]
    write_table_db(db)
    return db["users"][user]["projects"][project_id]["rows"]

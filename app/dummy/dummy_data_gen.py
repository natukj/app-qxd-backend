import asyncio
import random
from typing import Dict, Any, Tuple, List, AsyncGenerator

async def determine_classification_and_award(employee_data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    load_time = random.randint(1, 5)
    await asyncio.sleep(load_time)
    full_name = employee_data["fullName"]
    award_name = f"{full_name} Award"
    award_id = f"MA000{random.randint(10, 99)}"
    classification = f"{full_name} Classification"
    classification_id = f"MA000{random.randint(10, 99)}"
    
    award_data = {
        award_name: {
            "award_id": award_id
        }
    }
    classification_data = {
        classification: {
            "classification_id": classification_id
        }
    }
    
    return award_data, classification_data

async def determine_column_data(column_name: str, additional_info: str, row_data: Dict[str, Any]) -> str:
    load_time = random.randint(1, 5)
    await asyncio.sleep(load_time) 
    full_name = row_data["EmployeeData"]["fullName"]
    column_name = f"{full_name} {column_name}"
    column_data = {
        column_name: f"{full_name} {additional_info}"
    }
    return column_data

async def generate_row_data(row_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    columns_to_process = row_data.pop('Columns', {})
    
    # Determine Classification and Award
    award, classification = await determine_classification_and_award(row_data["EmployeeData"])
    row_data["Award"] = award
    row_data["Classification"] = classification
    yield {"Award": award, "Classification": classification}

    async def process_column(column_name: str, value: str) -> Tuple[str, str]:
        if value == "":
            column_data = await determine_column_data(column_name, row_data)
            return column_name, column_data
        return column_name, value
    
    columns_to_process = {k: v for k, v in columns_to_process.items() if k not in ["Award", "Classification"]}
    tasks = [process_column(column_name, value) for column_name, value in columns_to_process.items()]

    for future in asyncio.as_completed(tasks):
        column_name, column_data = await future
        row_data[column_name] = column_data
        yield {column_name: column_data}

async def generate_column_data(column_name: str, additional_info: str, rows: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
    async def process_row_column(row: Dict[str, Any]) -> Tuple[str, str, Any]:
        row_id = row['id']
        column_data = await determine_column_data(column_name, additional_info, row)
        return row_id, column_name, column_data

    tasks = [process_row_column(row) for row in rows]

    for future in asyncio.as_completed(tasks):
        row_id, column, data = await future
        yield {row_id: {column: data}}

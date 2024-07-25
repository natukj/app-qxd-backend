from typing import Dict, Any, Tuple, List, AsyncGenerator
import asyncio
import llm, prompts
from agents.tools import classify_tools
import json
import random

# groq
llama_tool_models = ["llama3-groq-70b-8192-tool-use-preview", "llama3-groq-8b-8192-tool-use-preview"]
llama_models = ["llama-3.1-405b-reasoning", "llama-3.1-70b-versatile", "llama-3.1-8b-instant", "llama3-70b-8192", "llama3-8b-8192"]

async def classify_employee(employee_data: Dict[str, Any], award_info: str) -> Tuple[Dict[str, Any], str]:
    employee_info = json.dumps(employee_data)
    messages = [
        {"role": "system", "content": prompts.classify_sys_message},
        {"role": "user", "content": prompts.classify_user_message.format(employee_info=employee_info, coverage_info=award_info)}
    ]
    response = await llm.openai_client_tool_completion_request(messages, classify_tools, tool_choice={"type": "function", "function": {"name": "classify_employee"}})
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    if tool_calls:
        for tool_call in tool_calls:
            function_args = json.loads(tool_call.function.arguments)
            for key, value in function_args.items():
                print(f"{key}: {value}")

            award_data = {
                function_args["award_id"]: {
                    "reasoning": function_args["award_reasoning"],
                    "references": function_args["award_clauses"]
                }
            }
            classification_data = {
                function_args["level"]: {
                    "reasoning": function_args["level_reasoning"],
                    "references": function_args["level_clauses"]
                }
            }
            return award_data, classification_data
    else:
        full_name = employee_data["fullName"]
        award_name = f"{full_name} Award"
        award_id = f"MA000{random.randint(10, 99)}"
        classification = f"{full_name} Classification"
        classification_id = f"Level {random.randint(1, 9)}"
        
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
    
async def determine_column_data(column_name: str, row_data: Dict[str, Any]) -> str:
    load_time = random.randint(1, 5)
    await asyncio.sleep(load_time) 
    full_name = row_data["EmployeeData"]["fullName"]
    column_name = f"{full_name} {column_name}"
    column_data = {
        column_name: f"{full_name} Data"
    }
    return column_data

async def generate_row_data(row_data: Dict[str, Any], award_info: str) -> AsyncGenerator[Dict[str, Any], None]:
    columns_to_process = row_data.pop('Columns', {})
    
    # Determine Classification and Award
    award, classification = await classify_employee(row_data["EmployeeData"], award_info)
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
        column_data = await determine_column_data(column_name, row)
        return row_id, column_name, column_data

    tasks = [process_row_column(row) for row in rows]

    for future in asyncio.as_completed(tasks):
        row_id, column, data = await future
        yield {row_id: {column: data}}
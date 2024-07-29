from typing import Dict, Any, Tuple, List, AsyncGenerator
import asyncio
from neo4j import AsyncSession as Neo4jAsyncSession
from crud.crud_gdb import ma_gdb
import llm, prompts
from agents.tools import classify_tools, section_choice_tools, provisions_tools
import json
import random
from pydantic import BaseModel

class ReferenceContent(BaseModel):
    id: str
    key: str
    title: str
    content: str

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
    
async def choose_sections(field: str, award: str, classification: str, sections: str, additional_info: str = None) -> List[str]:
    if additional_info:
        additional_info = f"Additional Information:\n{additional_info}"
    else:
        additional_info = ""
    messages = [
        {"role": "system", "content": "You are a helpful assistant. You are tasked with determining relevant section(s) from a document to will help answer a question."},
        {"role": "user", "content": prompts.section_choice_user_message.format(field=field, award=award, classification=classification, additional_info=additional_info, sections=sections)}
    ]
    response = await llm.groq_client_chat_completion_request(messages, section_choice_tools, tool_choice={"type": "function", "function": {"name": "choose_sections"}})
    response_message = response.choices[0].message
    print(response_message)
    tool_calls = response_message.tool_calls
    if tool_calls:
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            if function_name == "choose_sections":
                function_args = json.loads(tool_call.function.arguments)
                selected_sections = function_args["sections"]
                for selected_section in selected_sections:
                    print(selected_section)
                return selected_sections
    else:
        return []
    
async def determine_column_data(gdb: Neo4jAsyncSession, award_dict: Dict[str, Any], classification: str, column_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, ReferenceContent]]:
    award = list(award_dict.keys())[0]
    award_json = json.dumps(award_dict)
    column_name = column_data.get('name', '')
    additional_info = column_data.get('additionalInfo', '')
    sections = await ma_gdb.get_formatted_award_section_hierarchy(gdb, award)
    selected_sections = await choose_sections(column_name, award_json, classification, sections, additional_info)
    clauses, references = await ma_gdb.get_clauses(gdb, award, selected_sections)
    messages = [
        {"role": "system", "content": prompts.ma_sys_col_message},
        {"role": "user", "content": prompts.ma_sys_user_message.format(award=award_json, classification=classification, field=column_name, additional_info=additional_info, clauses=clauses)}
    ]
    response = await llm.openai_client_tool_completion_request(messages, provisions_tools, tool_choice={"type": "function", "function": {"name": "employee_provisions"}})
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    if tool_calls:
        for tool_call in tool_calls:
            function_args = json.loads(tool_call.function.arguments)
            for key, value in function_args.items():
                print(f"{key}: {value}")

            column_data = {
                function_args["provision_id"]: {
                    "answer": function_args["provision"],
                    "references": function_args["provision_clauses"]
                }
            }
        return column_data, references
    else:
        column_data = {
            award: f"{column_name} Data"
        }
        return column_data, {}

async def generate_row_data(gdb: Neo4jAsyncSession, row_data: Dict[str, Any], award_info: str) -> AsyncGenerator[Dict[str, Any], None]:
    columns_to_process = row_data.pop('Columns', {})
    
    # Determine Classification and Award
    award, classification = await classify_employee(row_data["EmployeeData"], award_info)
    row_data["Award"] = award
    row_data["Classification"] = classification
    yield {"Award": award, "Classification": classification}

    classification_json = json.dumps(classification)

    async def process_column(column_name: str, column_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        if column_data['value'] == "":
            column_value, references = await determine_column_data(gdb, award, classification_json, column_data)
            return column_name, column_value, references
        return column_name, {"value": column_data['value'], "additionalInfo": column_data['additionalInfo']}, {}
    
    columns_to_process = {k: v for k, v in columns_to_process.items() if k not in ["Award", "Classification"]}
    tasks = [process_column(column_name, column_data) for column_name, column_data in columns_to_process.items()]

    for future in asyncio.as_completed(tasks):
        column_name, column_value, ref = await future
        row_data[column_name] = column_value
        yield {column_name: column_value}

async def determine_fake_column_data(column_name: str, additional_info: str, row_data: Dict[str, Any]) -> str:
    load_time = random.randint(1, 5)
    await asyncio.sleep(load_time) 
    full_name = row_data["EmployeeData"]["fullName"]
    column_name = f"{full_name} {column_name}"
    column_data = {
        column_name: f"{full_name} {additional_info}"
    }
    return column_data


async def generate_column_data(column_name: str, additional_info: str, rows: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
    async def process_row_column(row: Dict[str, Any]) -> Tuple[str, str, Any]:
        row_id = row['id']
        column_data = await determine_fake_column_data(column_name, row)
        return row_id, column_name, column_data

    tasks = [process_row_column(row) for row in rows]

    for future in asyncio.as_completed(tasks):
        row_id, column, data = await future
        yield {row_id: {column: data}}
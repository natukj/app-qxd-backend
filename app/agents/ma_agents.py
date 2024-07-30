from typing import Dict, Any, Tuple, List, AsyncGenerator
import asyncio
from neo4j import AsyncSession as Neo4jAsyncSession
from neo4j import AsyncDriver
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
                    "citations": function_args["award_clauses"]
                }
            }
            classification_data = {
                function_args["level"]: {
                    "reasoning": function_args["level_reasoning"],
                    "citations": function_args["level_clauses"]
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
    
async def determine_column_data(gdb: Neo4jAsyncSession, award_dict: Dict[str, Any], classification_dict: Dict[str, Any], column_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, ReferenceContent]]:
    award = list(award_dict.keys())[0]
    award_json = json.dumps(award_dict)
    classification_json = json.dumps(classification_dict)
    column_name = column_data.get('name', '')
    additional_info = column_data.get('additionalInfo', '')
    sections = await ma_gdb.get_formatted_award_section_hierarchy(gdb, award)
    selected_sections = await choose_sections(column_name, award_json, classification_json, sections, additional_info)
    clauses, references = await ma_gdb.get_clauses(gdb, award, selected_sections)
    messages = [
        {"role": "system", "content": prompts.ma_sys_col_message},
        {"role": "user", "content": prompts.ma_sys_user_message.format(award=award_json, classification=classification_json, field=column_name, additional_info=additional_info, clauses=clauses)}
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
                "Completed": {
                    "answer": function_args["provision"],
                    "citations": function_args["provision_clauses"]
                }
            }
        return column_data, references
    else:
        column_data = {
            award: f"{column_name} Data"
        }
        return column_data, {}
    
async def determine_new_column_data(gdb: Neo4jAsyncSession, column_data: Dict[str, str], row: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    award_dict = row.get('Award', {})
    classification_dict = row.get('Classification', {})
    award = list(award_dict.keys())[0]
    award_json = json.dumps(award_dict)
    classification_json = json.dumps(classification_dict)
    column_name = column_data.get('name', '')
    additional_info = column_data.get('additionalInfo', '')
    sections = await ma_gdb.get_formatted_award_section_hierarchy(gdb, award)
    selected_sections = await choose_sections(column_name, award_json, classification_json, sections, additional_info)
    clauses, references = await ma_gdb.get_clauses(gdb, award, selected_sections)
    messages = [
        {"role": "system", "content": prompts.ma_sys_col_message},
        {"role": "user", "content": prompts.ma_sys_user_message.format(award=award_json, classification=classification_json, field=column_name, additional_info=additional_info, clauses=clauses)}
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
                "Completed": {
                    "answer": function_args["provision"],
                    "citations": function_args["provision_clauses"]
                }
            }
        return column_data, references
    else:
        column_data = {
            award: f"{column_name} Data"
        }
        return column_data, {}

async def generate_row_data(gdb: Neo4jAsyncSession, row_data: Dict[str, Any], award_data: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
    tasks = [ma_gdb.get_award_coverage_clauses(gdb, [award]) for award in award_data]
    results = await asyncio.gather(*tasks)
    award_info = ""
    all_references = {}
    for award, (output_str, references) in zip(award_data, results):
        award_info += output_str
        all_references[award['award_id']] = references

    columns_to_process = row_data.pop('Columns', {})
    
    # this process seems ugly
    award, classification = await classify_employee(row_data["EmployeeData"], award_info)
    award_id = list(award.keys())[0]
    award_references = all_references.get(award_id, {})
    award_ref_content = {
        key: award_references[key] 
        for key in award[award_id]['citations'] 
        if key in award_references
    }
    award_result = {
        **award,
        "ref_content": award_ref_content
    }
    classification_level = list(classification.keys())[0]
    classification_ref_content = {
        key: award_references[key] 
        for key in classification[classification_level]['citations'] 
        if key in award_references
    }
    classification_result = {
        **classification,
        "ref_content": classification_ref_content
    }
    yield {"Award": award_result, "Classification": classification_result}

    async def process_column(column_name: str, column_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        if column_data['value'] == "":
            column_value, column_references = await determine_column_data(gdb, award, classification, column_data)
            column_key = list(column_value.keys())[0]
            column_ref_content = {
                key: column_references[key] 
                for key in column_value[column_key]['citations'] 
                if key in column_references
            }
            column_value_result = {**column_value, "ref_content": column_ref_content}
            return column_name, column_value_result
        return column_name, column_data
    
    columns_to_process = {k: v for k, v in columns_to_process.items() if k not in ["Award", "Classification"]}
    tasks = [process_column(column_name, column_data) for column_name, column_data in columns_to_process.items()]

    for future in asyncio.as_completed(tasks):
        column_name, column_value = await future
        row_data[column_name] = column_value
        yield {column_name: column_value}


async def generate_column_data(gdb_driver: AsyncDriver, column_data: Dict[str, str], rows: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
    async def process_row_column(row: Dict[str, Any]) -> Tuple[str, str, Any]:
        async with gdb_driver.session() as session:
            row_id = row['id']
            column_value, column_references = await determine_new_column_data(session, column_data, row)
            column_key = list(column_value.keys())[0]

            column_value[column_key]["ref_content"] = {
                key: column_references[key] 
                for key in column_value[column_key]["citations"] 
                if key in column_references
            }
            
            return row_id, column_value

    tasks = [process_row_column(row) for row in rows]

    for future in asyncio.as_completed(tasks):
        row_id, data = await future
        yield {row_id: data}
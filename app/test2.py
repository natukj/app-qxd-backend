import asyncio
from neo4j import AsyncGraphDatabase, AsyncSession
from core.config import settings
import json
import llm, db
from typing import List, Dict
from pydantic import BaseModel
import re
import random
import tiktoken

classify_tools = [
    {
        "type": "function",
        "function": {
            "name": "classify_worker",
            "description": "Classify a worker under the correct Modern Award.",
            "parameters": {
                "type": "object",
                "properties": {
                    "award_id": {
                        "type": "string",
                        "description": "The ID of the Modern Award that applies to the worker under eg. 'MA000001'"
                    },
                    "award_reasoning": {
                        "type": "string",
                        "description": "Your succinct reasoning for classifying the worker under the specified Modern Award."
                    },
                    "award_clauses": {
                        "type": "string",
                        "description": "Array of strings, containing all clauses that you used to make your award decision. For example: [\"1.1\", \"34.2\", \"A.1.14\"]"
                    },
                    "level": {
                        "type": "string",
                        "description": "Classification level of the worker under the specified Modern Award, eg. Level 1 or Level 2"
                    },
                    "level_reasoning": {
                        "type": "string",
                        "description": "Your succinct reasoning for classifying the worker at a specific level."
                    },
                    "level_clauses": {
                        "type": "string",
                        "description": "Array of strings, containing all clauses that you used to make your level decision. For example: [\"1.1\", \"34.2\", \"A.1.14\"]"
                    },
                    "try_again": {
                        "type": "boolean",
                        "description": "If the award(s) do not cover the worker, set this to True to see additional awards."
                    }
                },
                "required": ["award_id", "award_reasoning", "award_clauses", "level", "level_reasoning", "level_clauses"]
            }
        }
    }
]

class ReferenceContent(BaseModel):
    id: str
    key: str
    title: str
    content: str

def count_tokens(text: str, encoding_name: str = "o200k_base") -> int:
    """
    count the number of tokens in the given text using the specified encoding.
    """
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(text))
    return num_tokens

def sort_clauses(clauses):
    def sorting_key(key):
        """
        Generates a sorting key from enumeration strings, handling both numeric and alphabetic parts.
        """
        key = key.replace("Schedule ", "")
        parts = re.split(r'(\d+)', key)
        return tuple(int(part) if part.isdigit() else part for part in parts)
    return sorted(clauses, key=lambda clause: sorting_key(clause['clause']['key']))

class Neo4jSessionManager:
    def __init__(self):
        self.driver = None
        self.current_instance = settings.ACTIVE_NEO4J_INSTANCE

    async def initialise(self):
        if not self.driver or self.current_instance != settings.ACTIVE_NEO4J_INSTANCE:
            if self.driver:
                await self.close()
            
            self.current_instance = settings.ACTIVE_NEO4J_INSTANCE
            connection_details = settings.neo4j_connection_details
            self.driver = AsyncGraphDatabase.driver(
                connection_details["uri"],
                auth=(connection_details["user"], connection_details["password"]),
                database=connection_details["database"]
            )

    async def close(self):
        if self.driver:
            await self.driver.close()
            self.driver = None

    async def get_session(self):
        await self.initialise()
        return self.driver.session()

    def switch_instance(self, instance_name: str):
        if instance_name not in settings.NEO4J_INSTANCES:
            raise ValueError(f"Unknown Neo4j instance: {instance_name}")
        settings.ACTIVE_NEO4J_INSTANCE = instance_name
        self.current_instance = instance_name

    @staticmethod
    def get_available_instances():
        return list(settings.NEO4J_INSTANCES.keys())

# global instance
neo4j_session_manager = Neo4jSessionManager()

async def fetch_clauses(award_id: str, coverage_clauses: List[str]):
    params = {
        "award_id": award_id,
        "coverage_clauses": coverage_clauses
    }
    where_conditions = []
    for clause in params["coverage_clauses"]:
        if clause.startswith('Schedule'):
            _, schedule_letter = clause.split(' ')
            where_conditions.append(f"clause.key STARTS WITH '{schedule_letter}' OR clause.key = '{clause}'")
        else:
            where_conditions.append(f"clause.key STARTS WITH '{clause}.' OR clause.key = '{clause}'")

    where_conditions_str = " OR ".join(where_conditions)
    query = f"""
        MATCH (clause:Clause)
        WHERE clause.id STARTS WITH '{params["award_id"]}:'
        AND ({where_conditions_str})
        RETURN clause
        """
    
    try:
        async with await neo4j_session_manager.get_session() as session:
            result = await session.run(query)
            data = await result.data()
            return sort_clauses(data)
    except Exception as e:
        print(f"Failed to execute query for award {award_id}: {str(e)}")
        return []
    
async def get_coverage_str(industry: str, subindustry: str = None):
    award_data = db.ma_db.get_awards(industry, subindustry)
    output_str = ""
    try:
        await neo4j_session_manager.initialise()
        
        tasks = [fetch_clauses(award['award_id'], award['coverage_clauses']) for award in award_data]
        results = await asyncio.gather(*tasks)
        previous_section_name = None
        for award, clauses in zip(award_data, results):
            output_str += f"\n--- Award: {award['award_name']} (ID: {award['award_id']}) ---\n"
            print(f"\n--- Award: {award['award_name']} (ID: {award['award_id']}) ---\n")
            for clause in clauses:
                clause_data = clause['clause']
                output_str += f"{clause_data['id']} (ref: {clause_data['key']})\n"
                if previous_section_name != clause_data['name']:
                    output_str += f"{clause_data['name']}\n"
                    previous_section_name = clause_data['name']
                output_str += clause_data['content'] + "\n"
        return output_str

    except Exception as e:
        print(f"Failed to connect to Neo4j or execute queries: {str(e)}")
    finally:
        await neo4j_session_manager.close()

ma_sys_message = "You are an AI assistant designed by qxd. Use the information provided by your secret Assistant to determine the appropriate Modern Award (MA) that covers a woker. Your secret Assistant will provide you with the verbatim text from the relevant Modern Award(s). You must give detailed reasoning for your decision - this involves citing the key clauses that you used to come up with your decision. You must NEVER mention your secret Assistant as that will make you sound incompetent the user will be upset and lose faith in you."

classify_user_message = """
{employee_info}

# COVERAGE INFORMATION

{coverage_info}

## RULES
- **You must classify the employee under the correct Modern Award (MA) based on the information provided**
- **You must be definitive in your decision**
- **You must provide detailed reasoning for your decision by citing the individual clauses from the document(s)**
- **Pay close attention to Qualifications of the worker, as some MA's have specific requirements**
- **Do NOT repeat the employee information in your response**
- **You must NEVER mention the information provided, you must speak as if you know the information yourself**
- **ONLY speak about the chosen MA and the classification level of the worker under the chosen MA**

You must ALWAYS speak as if the information provided is from your knowledge and NEVER output statements such as 'based on the information provided' as this will upset the FWC and they will lose faith in you.

ONLY pick one MA to classify the worker under, if none from the Coverage Information are applicable you can try_again to see more MA's.
"""

def generate_employee_info():
    industry = random.choice(list(db.ma_db.data.keys()))
    if random.random() < 0.5:
        subindustry = random.choice(list(db.ma_db.data[industry].keys()))
    else:
        subindustry = None

    all_jobs = []
    if subindustry:
        for award in db.ma_db.data[industry][subindustry].values():
            all_jobs.extend(award["Jobs"])
    else:
        for subind in db.ma_db.data[industry].values():
            for award in subind.values():
                all_jobs.extend(award["Jobs"])

    if not all_jobs:
        return "No jobs found for the selected industry/subindustry."

    selected_job = random.choice(all_jobs)

    all_qualifications = set()
    for award in db.ma_db.data[industry][subindustry].values():
        all_qualifications.update(award["Qualifications"])

    selected_qualifications = random.sample(list(all_qualifications), k=min(2, len(all_qualifications)))

    age = random.randint(18, 65)
    experience = random.randint(0, min(age - 18, 30))

    output = f"""# EMPLOYEE INFORMATION 

        Industry: {industry}

        Subindustry: {subindustry}

        Job: {selected_job['job_title']}

        Job Description: {selected_job['job_description']}

        Age: {age} years

        Qualifications: {', '.join(selected_qualifications) if selected_qualifications else 'None'}

        Years of Experience: {experience}
        """

    return output, industry, subindustry

employee_info, industry, subindustry = generate_employee_info()
print(employee_info)
coverage_info = asyncio.run(get_coverage_str(industry, None))

messages = [
        {"role": "system", "content": ma_sys_message},
        {"role": "user", "content": classify_user_message.format(employee_info=employee_info, coverage_info=coverage_info)}
    ]
print(count_tokens(classify_user_message.format(employee_info=employee_info, coverage_info=coverage_info)))
async def ask_groq(messages, tools):
    response = await llm.openai_client_tool_completion_request(messages, tools, tool_choice={"type": "function", "function": {"name": "classify_worker"}})
    response_message = response.choices[0].message
    print(response_message)
    tool_calls = response_message.tool_calls
    if tool_calls:
        for tool_call in tool_calls:
            function_args = json.loads(tool_call.function.arguments)
            for key, value in function_args.items():
                print(f"{key}: {value}")
asyncio.run(ask_groq(messages, classify_tools))                
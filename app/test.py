import asyncio
from neo4j import AsyncGraphDatabase, AsyncSession
from core.config import settings
import json
import llm

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

def safe_str(input):
    try:
        return str(input)
    except Exception as e:
        print(f"Error converting to string: {e}")
        return ""

async def print_hierarchy(hierarchy, indent=0, sections="", depth=0):
    local_sections = sections  # Work with a local copy that accumulates the changes
    prefix = "\t" * indent  # Using tab for indentation
    if depth > 0:  # Add dash only for subsections and deeper
        prefix += "- "

    for section, details in hierarchy.items():
        section_str = safe_str(section)  # Safely convert section name to string
        local_sections += (prefix + section_str + "\n")
        
        if 'subsections' in details and details['subsections']:
            local_sections = await print_hierarchy(details['subsections'], indent + 1, local_sections, depth + 1)
    return local_sections

async def get_award_section_hierarchy(award_id: str):
    async with await neo4j_session_manager.get_session() as session:
        query = """
        MATCH (doc:Document {name: $award_id})-[:CONTAINS]->(section:Section)
        OPTIONAL MATCH (section)-[:CONTAINS]->(subsection:Subsection)
        OPTIONAL MATCH (subsection)-[:CONTAINS]->(subsubsection:Subsubsection)
        RETURN section.name AS section_name,
               subsection.name AS subsection_name,
               subsubsection.name AS subsubsection_name
        ORDER BY section_name, subsection_name, subsubsection_name
        """
        result = await session.run(query, award_id=award_id)
        
        sections = {}
        
        async for record in result:
            section_name = record["section_name"]
            subsection_name = record["subsection_name"]
            subsubsection_name = record["subsubsection_name"]
            
            if section_name not in sections:
                sections[section_name] = {"subsections": {}}
            
            if subsection_name:
                if subsection_name not in sections[section_name]["subsections"]:
                    sections[section_name]["subsections"][subsection_name] = {"subsubsections": []}
                
                if subsubsection_name:
                    sections[section_name]["subsections"][subsection_name]["subsubsections"].append(subsubsection_name)
        
        return sections

def truncate_text(text, max_length=100):
    return (text if len(text) <= max_length else text[:max_length] + '...').replace('\n', ' ')
async def get_subsection_clauses(section_name):
    async with await neo4j_session_manager.get_session() as session:
        query = """
        MATCH (sec:Section {name: $section_name})-[:CONTAINS]->(sub:Subsection)
        OPTIONAL MATCH (sub)-[:CONTAINS]->(clause:Clause)
        OPTIONAL MATCH (clause)-[:REFERENCES]->(refClause:Clause)
        RETURN sub.name AS subsection_name, 
               clause.name AS clause_name, 
               clause.id AS clause_id, 
               clause.key AS clause_key, 
               clause.content AS clause_content,
               collect(refClause.name) AS ref_names, 
               collect(refClause.id) AS ref_ids, 
               collect(refClause.key) AS ref_keys, 
               collect(refClause.content) AS ref_contents
        """
        result = await session.run(query, section_name=section_name)
        subsection_clauses = {}
        async for record in result:
            subsection_name = record["subsection_name"]
            if subsection_name not in subsection_clauses:
                subsection_clauses[subsection_name] = []

            clause_info = f"{record['clause_name']} ({record['clause_key']}): {truncate_text(record['clause_content'])}"
            ref_names = record["ref_names"]
            ref_ids = record["ref_ids"]
            ref_keys = record["ref_keys"]
            ref_contents = record["ref_contents"]
            references = []
            for name, id, key, content in zip(ref_names, ref_ids, ref_keys, ref_contents):
                if name:  # Ensure non-null reference
                    references.append(f"Referenced: {name} ({key}): {truncate_text(content)}")
            clause_entry = {"clause": clause_info, "references": references}
            subsection_clauses[subsection_name].append(clause_entry)
        return subsection_clauses

section_name = "Wages and Allowances"
subsection_clauses = asyncio.run(get_subsection_clauses(section_name))

async def print_formatted_hierarchy(subsection_clauses):
    for subsection, clauses in subsection_clauses.items():
        print(f"Subsection: {subsection}")
        for entry in clauses:
            print(f"  - {entry['clause']}")
            if entry['references']:
                print("    References:")
                for ref in entry['references']:
                    print(f"      {ref}")
        print("")
asyncio.run(print_formatted_hierarchy(subsection_clauses))
exit()
award_id = "MA000065"
hierarchy = asyncio.run(get_award_section_hierarchy(award_id))
#asyncio.run(print_hierarchy(hierarchy))
sections = asyncio.run(print_hierarchy(hierarchy))
print('#'*50)
print(sections)

tools = [
        {
            "type": "function",
            "function": {
                "name": "choose_sections",
                "description": "Choose relevant sections from an Australian Modern Award",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sections": {
                            "type": "array",
                            "description": "Verbatim sections from an Australian Modern Award",
                        }
                    },
                    "required": ["sections"],
                },
            },
        }
    ]
prompt = """From document sections below, choose the section(s) that are most relevant to the question: 'What are the leave and public holiday provisions?'

The sections below are hierarchically structured to help you. Top level sections have no indentation and are followed by subsections that are indented with a \\t and a dash. You may choose one or more sections, however, if all subsections of a section are relevant, you can choose the section without choosing the subsections.

The sections are:

{sections}""".format(sections=sections)
messages = [
        {"role": "system", "content": "You are a helpful assistant. You are tasked with determining relevant section(s) from a document to will help answer a question."},
        {"role": "user", "content": prompt}
    ]

async def ask_groq(messages, tools):
    response = await llm.groq_client_chat_completion_request(messages, tools, tool_choice={"type": "function", "function": {"name": "choose_sections"}})
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
                
                
        

asyncio.run(ask_groq(messages, tools))


import asyncio
from neo4j import AsyncGraphDatabase, AsyncSession
from core.config import settings
from typing import List, Dict, Any, Tuple, Set
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

async def format_hierarchy(hierarchy, indent=0, sections="", depth=0):
    local_sections = sections
    prefix = "\t" * indent
    if depth > 0:
        prefix += "- "

    for section, details in hierarchy.items():
        section_str = safe_str(section)  # Safely convert section name to string
        local_sections += (prefix + section_str + "\n")
        
        if 'subsections' in details and details['subsections']:
            local_sections = await format_hierarchy(details['subsections'], indent + 1, local_sections, depth + 1)
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

async def get_clauses(award_id: str, sections: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    async with await neo4j_session_manager.get_session() as session:
        conditions = " OR ".join([f"section.name = '{section}' OR subsection.name = '{section}'" for section in sections])
    
        query = f"""
        MATCH (doc:Document {{name: $award_id}})-[:CONTAINS]->(section:Section)
        OPTIONAL MATCH (section)-[:CONTAINS]->(subsection:Subsection)
        OPTIONAL MATCH (section)-[:CONTAINS]->(clause:Clause)
        OPTIONAL MATCH (subsection)-[:CONTAINS]->(subClause:Clause)
        WITH section, subsection, clause, subClause
        WHERE {conditions}
        WITH section, subsection, 
            CASE WHEN clause IS NOT NULL THEN clause ELSE subClause END AS finalClause
        OPTIONAL MATCH (finalClause)-[:REFERENCES]->(refClause:Clause)
        RETURN section.name AS section_name,
            subsection.name AS subsection_name, 
            finalClause.name AS clause_name, 
            finalClause.id AS clause_id, 
            finalClause.key AS clause_key, 
            finalClause.content AS clause_content,
            collect({{
                name: refClause.name, 
                id: refClause.id, 
                key: refClause.key, 
                content: refClause.content
            }}) AS references
        ORDER BY section.name, subsection.name, finalClause.key
        """
        
        result = await session.run(query, award_id=award_id)
        clauses_dict: Dict[str, List[Dict[str, Any]]] = {}
        processed_clauses: Set[str] = set()
        all_references: Dict[str, Dict[str, Any]] = {}

        async for record in result:
            section_name = record["section_name"]
            subsection_name = record["subsection_name"]
            
            # Use section name if subsection is not available
            key = subsection_name if subsection_name else section_name
            
            if key not in clauses_dict:
                clauses_dict[key] = []
            
            clause_id = record["clause_id"]
            if clause_id and clause_id not in processed_clauses:
                processed_clauses.add(clause_id)
                
                clause_info = {
                    "name": record["clause_name"],
                    "id": clause_id,
                    "key": record["clause_key"],
                    "content": record["clause_content"],
                    "references": []
                }
                
                # Process references
                for ref in record["references"]:
                    if ref["id"]:
                        if ref["id"] not in all_references:
                            all_references[ref["id"]] = ref
                        clause_info["references"].append(ref["id"])
                
                clauses_dict[key].append(clause_info)
        
        # Replace reference IDs with full reference information
        for section_clauses in clauses_dict.values():
            for clause in section_clauses:
                clause["references"] = [all_references[ref_id] for ref_id in clause["references"] if ref_id in all_references]
        
        return clauses_dict

section_name = ["Payment of wages", "Hours of Work"]
award_id = "MA000065"
clauses = asyncio.run(get_clauses(award_id, section_name))
def print_formatted_clauses(clauses_dict: Dict[str, List[Dict[str, Any]]]):
    for section, clauses in clauses_dict.items():
        print(f"\n{'=' * 80}")
        print(f"SECTION: {section}")
        print(f"{'=' * 80}")
        
        for clause in clauses:
            print(f"\n  CLAUSE: {clause['name']} (ID: {clause['id']}, Key: {clause['key']})")
            print(f"  {'~' * 50}")
            
            # Print content (first 100 characters)
            content_preview = clause['content'][:100] + "..." if len(clause['content']) > 100 else clause['content']
            print(f"  Content: {content_preview}")
            
            # Print references
            if clause['references']:
                print("\n  References:")
                for ref in clause['references']:
                    ref_content_preview = ref['content'][:50] + "..." if len(ref['content']) > 50 else ref['content']
                    print(f"    - {ref['name']} (ID: {ref['id']}, Key: {ref['key']})")
                    print(f"      Content: {ref_content_preview}")
            
            print()  # Extra line for readability

    print(f"\n{'=' * 80}")
    print("END OF CLAUSES")
    print(f"{'=' * 80}")

print_formatted_clauses(clauses)

exit()
award_id = "MA000065"
hierarchy = asyncio.run(get_award_section_hierarchy(award_id))
#asyncio.run(print_hierarchy(hierarchy))
sections = asyncio.run(format_hierarchy(hierarchy))
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


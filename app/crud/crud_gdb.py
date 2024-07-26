import re
from typing import List, Dict, Any, Tuple, Set
from neo4j import AsyncSession
from pydantic import BaseModel

class ReferenceContent(BaseModel):
    id: str
    key: str
    title: str
    content: str

class CRUDGDB:
    @staticmethod
    def sort_clauses(clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def sorting_key(key):
            key = key.replace("Schedule ", "")
            parts = re.split(r'(\d+)', key)
            return tuple(int(part) if part.isdigit() else part for part in parts)
        return sorted(clauses, key=lambda clause: sorting_key(clause['clause']['key']))
    
    @staticmethod
    def format_hierarchy(hierarchy: Dict[str, Any], indent: int = 0, sections: str = "", depth: int = 0) -> str:
        local_sections = sections
        prefix = "\t" * indent
        if depth > 0:
            prefix += "- "

        for section, details in hierarchy.items():
            local_sections += (prefix + str(section) + "\n")
            
            if 'subsections' in details and details['subsections']:
                local_sections = CRUDGDB.format_hierarchy(details['subsections'], indent + 1, local_sections, depth + 1)
        return local_sections
    
    @staticmethod
    async def get_award_section_hierarchy(session: AsyncSession, award_id: str) -> Dict[str, Any]:
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
    
    @staticmethod
    async def get_formatted_award_section_hierarchy(session: AsyncSession, award_id: str) -> str:
        hierarchy = await CRUDGDB.get_award_section_hierarchy(session, award_id)
        return CRUDGDB.format_hierarchy(hierarchy)

    @staticmethod
    async def fetch_coverage_clauses(session: AsyncSession, award_id: str, coverage_clauses: List[str]) -> List[Dict[str, Any]]:
        where_conditions = []
        for clause in coverage_clauses:
            if clause.startswith('Schedule'):
                _, schedule_letter = clause.split(' ')
                where_conditions.append(f"clause.key STARTS WITH '{schedule_letter}' OR clause.key = '{clause}'")
            else:
                where_conditions.append(f"clause.key STARTS WITH '{clause}.' OR clause.key = '{clause}'")

        where_conditions_str = " OR ".join(where_conditions)
        query = f"""
            MATCH (clause:Clause)
            WHERE clause.id STARTS WITH '{award_id}:'
            AND ({where_conditions_str})
            RETURN clause
            """
        
        try:
            result = await session.run(query)
            data = await result.data()
            return CRUDGDB.sort_clauses(data)
        except Exception as e:
            print(f"Failed to execute query for award {award_id}: {str(e)}")
            return []

    @staticmethod
    async def get_award_coverage_clauses(session: AsyncSession, award_data: List[Dict[str, Any]]) -> Tuple[str, Dict[str, ReferenceContent]]:
        output_str = ""
        references = {}
        for award in award_data:
            output_str += f"\n--- Award: {award['award_name']} (ID: {award['award_id']}) ---\n"
            clauses = await CRUDGDB.fetch_coverage_clauses(session, award['award_id'], award['coverage_clauses'])
            previous_section_name = None
            for clause in clauses:
                clause_data = clause['clause']
                output_str += f"{clause_data['id']} (ref: {clause_data['key']})\n"
                if previous_section_name != clause_data['name']:
                    output_str += f"{clause_data['name']}\n"
                    previous_section_name = clause_data['name']
                output_str += clause_data['content'] + "\n"
                if clause_data['key'] not in references:
                    references[clause_data['key']] = ReferenceContent(
                        id=clause_data['id'],
                        key=clause_data['key'],
                        title=clause_data['name'],
                        content=clause_data['content']
                    )
        return output_str, references
    
    @staticmethod
    async def fetch_clauses(session: AsyncSession, award_id: str, sections: List[str]) -> Dict[str, List[Dict[str, Any]]]:
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
    
    @staticmethod
    async def get_clauses(session: AsyncSession, award_id: str, sections: List[str]) -> Tuple[str, Dict[str, ReferenceContent]]:
        output_str = ""
        references = {}
        clauses_dict = await CRUDGDB.fetch_clauses(session, award_id, sections)
        for section, clauses in clauses_dict.items():
            output_str += f"\n--- {section} ---\n"
            for clause in clauses:
                output_str += f"{clause['id']} (ref: {clause['key']})\n"
                output_str += clause['content'] + "\n"
                if clause['references']:
                    output_str += "Clause References:\n"
                    for ref in clause['references']:
                        output_str += f"{ref['id']} (ref: {ref['key']})\n"
                        output_str += ref['content'] + "\n"
                        references[ref['key']] = ReferenceContent(
                            id=ref['id'],
                            key=ref['key'],
                            title=ref['name'],
                            content=ref['content']
                        )
        return output_str, references


        
    
ma_gdb = CRUDGDB()
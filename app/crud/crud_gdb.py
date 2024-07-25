import re
from typing import List, Dict, Any, Tuple
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
    
ma_gdb = CRUDGDB()
import asyncio
import db, gdb # type: ignore
from typing import List, Dict
from pydantic import BaseModel
import re

class ReferenceContent(BaseModel):
    id: str
    key: str
    title: str
    content: str

def sort_clauses(clauses):
    def sorting_key(key):
        """
        Generates a sorting key from enumeration strings, handling both numeric and alphabetic parts.
        """
        key = key.replace("Schedule ", "")
        parts = re.split(r'(\d+)', key)
        return tuple(int(part) if part.isdigit() else part for part in parts)
    return sorted(clauses, key=lambda clause: sorting_key(clause['clause']['key']))

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
        async with await gdb.neo4j_session_manager.get_session() as session:
            result = await session.run(query)
            data = await result.data()
            return sort_clauses(data)
    except Exception as e:
        print(f"Failed to execute query for award {award_id}: {str(e)}")
        return []

async def test_neo4j_connection():
    award_data = db.ma_db.get_awards("Agriculture and Aquaculture", "Agriculture")
    
    try:
        await gdb.neo4j_session_manager.initialise()
        
        tasks = [fetch_clauses(award['award_id'], award['coverage_clauses']) for award in award_data]
        results = await asyncio.gather(*tasks)
        previous_section_name = None
        for award, clauses in zip(award_data, results):
            print(f"\n--- Award: {award['award_name']} (ID: {award['award_id']}) ---")
            for clause in clauses:
                clause_data = clause['clause']
                print(f"{clause_data['id']}: {clause_data['key']}")
                if previous_section_name != clause_data['name']:
                    print(f"{clause_data['name']}")
                    previous_section_name = clause_data['name']
                print(f"Content: {clause_data['content'][:100]}...")  # Truncate content for readability

    except Exception as e:
        print(f"Failed to connect to Neo4j or execute queries: {str(e)}")
    finally:
        await gdb.neo4j_session_manager.close()

if __name__ == "__main__":
    asyncio.run(test_neo4j_connection())

from typing import Any, Dict, List, Optional, TypeVar, Generic
from pydantic import BaseModel
from neo4j import AsyncSession

NodeType = TypeVar("NodeType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

# NOT USING ATM BUT KEEPING FOR REFERENCE
class CRUDBaseGDB(Generic[NodeType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, label: str):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD) for Neo4j.
        **Parameters**
        * `label`: A Neo4j node label
        """
        self.label = label

    async def get(self, db: AsyncSession, id: str) -> Optional[Dict[str, Any]]:
        query = f"MATCH (n:{self.label} {{id: $id}}) RETURN n"
        result = await db.run(query, id=id)
        record = await result.single()
        return record['n'] if record else None

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        query = f"MATCH (n:{self.label}) RETURN n ORDER BY n.id SKIP $skip LIMIT $limit"
        result = await db.run(query, skip=skip, limit=limit)
        return [record['n'] for record in await result.data()]

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> Dict[str, Any]:
        properties = obj_in.model_dump()
        query = f"CREATE (n:{self.label} $properties) RETURN n"
        result = await db.run(query, properties=properties)
        return (await result.single())['n']

    async def update(
        self,
        db: AsyncSession,
        *,
        id: str,
        obj_in: UpdateSchemaType
    ) -> Dict[str, Any]:
        update_data = obj_in.model_dump(exclude_unset=True)
        set_clause = ", ".join([f"n.{k} = ${k}" for k in update_data.keys()])
        query = f"MATCH (n:{self.label} {{id: $id}}) SET {set_clause} RETURN n"
        result = await db.run(query, id=id, **update_data)
        return (await result.single())['n']

    async def remove(self, db: AsyncSession, *, id: str) -> Dict[str, Any]:
        query = f"MATCH (n:{self.label} {{id: $id}}) DETACH DELETE n RETURN n"
        result = await db.run(query, id=id)
        return (await result.single())['n']

    async def by_embedding(
        self,
        db: AsyncSession,
        embedding: List[float],
        index_name: str,
        top_k: int = 5,
        **filters
    ) -> List[Dict[str, Any]]:
        query = f"""
        CALL db.index.vector.queryNodes($index_name, $top_k, $embedding)
        YIELD node, score
        WHERE node:{self.label}
        """
        
        for key, value in filters.items():
            if isinstance(value, list):
                query += f" AND node.{key} IN ${key}"
            else:
                query += f" AND node.{key} = ${key}"

        query += " RETURN node, score ORDER BY score DESC"
        
        result = await db.run(query, embedding=embedding, index_name=index_name, top_k=top_k, **filters)
        return [{"node": record['node'], "score": record['score']} for record in await result.data()]
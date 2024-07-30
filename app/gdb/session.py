from neo4j import AsyncGraphDatabase, AsyncSession, AsyncDriver
from core.config import settings

class Neo4jSessionLocal:
    def __init__(self):
        self.driver = None
        self.current_instance = settings.ACTIVE_NEO4J_INSTANCE

    async def __aenter__(self) -> tuple[AsyncSession, AsyncDriver]:
        await self.initialise()
        return self.driver.session(), self.driver

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            await self.driver.close()
        self.driver = None

    async def initialise(self):
        if not self.driver or self.current_instance != settings.ACTIVE_NEO4J_INSTANCE:
            if self.driver:
                await self.driver.close()
            
            self.current_instance = settings.ACTIVE_NEO4J_INSTANCE
            connection_details = settings.neo4j_connection_details
            self.driver = AsyncGraphDatabase.driver(
                connection_details["uri"],
                auth=(connection_details["user"], connection_details["password"]),
                database=connection_details["database"]
            )

    @staticmethod
    def get_available_instances():
        return list(settings.NEO4J_INSTANCES.keys())

# class Neo4jSessionManager:
#     def __init__(self):
#         self.driver = None
#         self.current_instance = settings.ACTIVE_NEO4J_INSTANCE

#     async def initialise(self):
#         if not self.driver or self.current_instance != settings.ACTIVE_NEO4J_INSTANCE:
#             if self.driver:
#                 await self.close()
            
#             self.current_instance = settings.ACTIVE_NEO4J_INSTANCE
#             connection_details = settings.neo4j_connection_details
#             self.driver = AsyncGraphDatabase.driver(
#                 connection_details["uri"],
#                 auth=(connection_details["user"], connection_details["password"]),
#                 database=connection_details["database"]
#             )

#     async def close(self):
#         if self.driver:
#             await self.driver.close()
#             self.driver = None

#     async def get_session(self):
#         await self.initialise()
#         return self.driver.session()

#     def switch_instance(self, instance_name: str):
#         if instance_name not in settings.NEO4J_INSTANCES:
#             raise ValueError(f"Unknown Neo4j instance: {instance_name}")
#         settings.ACTIVE_NEO4J_INSTANCE = instance_name
#         self.current_instance = instance_name

#     @staticmethod
#     def get_available_instances():
#         return list(settings.NEO4J_INSTANCES.keys())

# # global instance
# neo4j_session_manager = Neo4jSessionManager()

# async def get_neo4j_session():
#     async with await neo4j_session_manager.get_session() as session:
#         yield session

# # dependency for FastAPI
# async def get_neo4j_db():
#     await neo4j_session_manager.initialise()
#     return neo4j_session_manager

# # aux function to get available Neo4j instances
# def get_available_instances():
#     return list(settings.NEO4J_INSTANCES.keys())
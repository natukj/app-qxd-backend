import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings
from db.base import Base

async def init_db():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all) # CARE DROP ALL TABLES
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()

    print("Database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())
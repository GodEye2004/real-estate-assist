from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

# DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:mo90mo80@localhost:5432/ai_assist")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ai_assist_db_user:bRVilvyHJNV83skNohDDag9VcGQ5kshZ@dpg-d40u25f5r7bs73881ur0-a/ai_assist_db")


engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from sqlalchemy.orm import sessionmaker
# import os
#
# # DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:mo90mo80@localhost:5432/ai_assist")
# DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ai_assist_db_user:bRVilvyHJNV83skNohDDag9VcGQ5kshZ@dpg-d40u25f5r7bs73881ur0-a/ai_assist_db")
#
#
# engine = create_async_engine(DATABASE_URL)
# AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
#
# async def get_db():
#     async with AsyncSessionLocal() as session:
#         yield session


from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

# Get the DATABASE_URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL environment variable not set!")

# Ensure the URL uses asyncpg
if not DATABASE_URL.startswith("postgresql+asyncpg://"):
    raise ValueError("❌ DATABASE_URL must start with 'postgresql+asyncpg://' for async connections")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)  # echo=True for debug

# Create async session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency for FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

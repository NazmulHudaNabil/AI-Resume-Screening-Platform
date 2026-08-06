from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# Use asyncpg driver for async SQLAlchemy with PostgreSQL
db_url = settings.database_url
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql+psycopg://") or db_url.startswith("postgresql+psycopg2://"):
    db_url = db_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
    db_url = db_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)

engine = create_async_engine(db_url, echo=False)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing a database session."""
    async with async_session_maker() as session:
        yield session

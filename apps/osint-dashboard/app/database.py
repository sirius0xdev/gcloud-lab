import os

from sqlalchemy import MetaData, event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DB_USER = os.getenv("DB_USER", "osint")
DB_PASS = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "osint-pgdb-rw.customer1.svc.cluster.local")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "osint_data")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(
    DATABASE_URL, echo=False, pool_size=5, max_overflow=10, pool_recycle=300
)
async_session = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
metadata = MetaData()


async def init_extensions():
    """Initialize PostGIS and TimescaleDB extensions on first connection."""
    async with engine.connect() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
        await conn.commit()

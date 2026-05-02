from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import MetaData

# Connection to hermes-pgdb CNPG cluster
DATABASE_URL = (
    f"postgresql+asyncpg://{db_user}:{db_pass}"
    f"@hermes-pgdb-rw.customer1.svc.cluster.local:5432/trading_data"
).format(
    db_user="trading",
    db_pass="TRADING_DB_PASSWORD",  # overridden by env
)

import os

DB_USER = os.getenv("DB_USER", "trading")
DB_PASS = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "hermes-pgdb-rw.customer1.svc.cluster.local")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "trading_data")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5, max_overflow=10)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
metadata = MetaData()

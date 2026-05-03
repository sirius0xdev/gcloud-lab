from sqlalchemy import Column, String, Numeric, Enum, DateTime, JSON, func, Table
from sqlalchemy.dialects.postgresql import UUID
import uuid

from database import metadata

positions = Table(
    "positions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("symbol", String(32), nullable=False, index=True),
    Column("direction", Enum("long", "short", name="position_direction"), nullable=False),
    Column("entry_price", Numeric(precision=16, scale=8), nullable=False),
    Column("exit_price", Numeric(precision=16, scale=8)),
    Column("quantity", Numeric(precision=16, scale=8), nullable=False),
    Column("exchange", String(32), nullable=False, index=True),
    Column("opened_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("closed_at", DateTime(timezone=True)),
    Column("pnl", Numeric(precision=16, scale=2)),
    Column("metadata", JSON),
)

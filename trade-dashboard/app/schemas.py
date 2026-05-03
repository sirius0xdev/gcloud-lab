from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class Direction(str, Enum):
    long = "long"
    short = "short"


# ─── Request schemas ──────────────────────────────────────────────

class PositionCreate(BaseModel):
    symbol: str
    direction: Direction
    entry_price: Decimal
    quantity: Decimal
    exchange: str
    metadata: Optional[dict] = None


class PositionUpdate(BaseModel):
    entry_price: Optional[Decimal] = None
    exit_price: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    metadata: Optional[dict] = None


class WebhookTrade(BaseModel):
    """Payload from automated scanner scripts."""
    symbol: str
    direction: Direction
    entry_price: Decimal
    quantity: Decimal
    exchange: str
    strategy: Optional[str] = None


# ─── Response schemas ─────────────────────────────────────────────

class PositionOut(BaseModel):
    id: UUID
    symbol: str
    direction: Direction
    entry_price: Decimal
    exit_price: Optional[Decimal]
    quantity: Decimal
    exchange: str
    opened_at: datetime
    closed_at: Optional[datetime]
    pnl: Optional[Decimal]
    metadata: Optional[dict]

    model_config = {"from_attributes": True}


class PnLSnapshot(BaseModel):
    today_pnl: Decimal
    week_pnl: Decimal
    month_pnl: Decimal
    all_time_pnl: Decimal
    total_trades: int
    open_positions: int


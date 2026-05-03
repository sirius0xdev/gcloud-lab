"""Trade Dashboard — FastAPI service for tracking PnL and open positions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import positions
from schemas import (
    Direction,
    PnLSnapshot,
    PositionCreate,
    PositionOut,
    PositionUpdate,
    WebhookTrade,
)

app = FastAPI(title="Trade Dashboard", version="0.1.0")

STATIC_DIR = Path(__file__).parent / "static"


# ── Helpers ─────────────────────────────────────────────────────────────

def position_to_out(row: dict) -> PositionOut:
    return PositionOut(
        id=row["id"],
        symbol=row["symbol"],
        direction=row["direction"],
        entry_price=row["entry_price"],
        exit_price=row["exit_price"],
        quantity=row["quantity"],
        exchange=row["exchange"],
        opened_at=row["opened_at"],
        closed_at=row["closed_at"],
        pnl=row["pnl"],
        metadata=row["metadata"],
    )


# ── Health ─────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    async with async_session() as session:
        result = await session.execute(select(func.now()))
        db_time = result.scalar()
    return {"status": "ok", "db_time": db_time.isoformat()}


# ── Positions ────────────────────────────────────────────────────────────

@app.get("/api/positions", response_model=list[PositionOut])
async def list_positions(
    open_only: bool = Query(True, description="Only show open positions"),
):
    async with async_session() as session:
        if open_only:
            stmt = select(positions).where(positions.c.closed_at.is_(None)).order_by(positions.c.opened_at.desc())
        else:
            stmt = select(positions).order_by(positions.c.opened_at.desc())
        rows = (await session.execute(stmt)).mappings().all()
    return [position_to_out(r) for r in rows]


@app.post("/api/positions", status_code=201)
async def create_position(payload: PositionCreate):
    async with async_session() as session:
        values = payload.model_dump()
        result = await session.execute(positions.insert().values(**values))
        session.commit()
        pk = result.inserted_primary_key[0]
    return {"id": str(pk)}


@app.patch("/api/positions/{position_id}")
async def update_position(position_id: UUID, payload: PositionUpdate):
    async with async_session() as session:
        row = await session.execute(
            select(positions).where(positions.c.id == position_id)
        )
        row = row.mappings().one_or_none()
        if not row:
            raise HTTPException(404, "Position not found")

        updates = payload.model_dump(exclude_unset=True)

        # Auto-compute PnL if closing
        if "exit_price" in updates:
            entry = row["entry_price"]
            qty = row["quantity"]
            exit_p = updates["exit_price"]
            direction = row["direction"]
            if direction == "long":
                updates["pnl"] = float((exit_p - entry) * qty)
            else:
                updates["pnl"] = float((entry - exit_p) * qty)
            updates["closed_at"] = datetime.now(timezone.utc)

        await session.execute(
            positions.update().where(positions.c.id == position_id).values(**updates)
        )
        session.commit()

    return {"ok": True}


@app.delete("/api/positions/{position_id}")
async def close_position(position_id: UUID, exit_price: Decimal = Query(None)):
    async with async_session() as session:
        row = await session.execute(
            select(positions).where(positions.c.id == position_id)
        )
        row = row.mappings().one_or_none()
        if not row:
            raise HTTPException(404, "Position not found")

        if row["closed_at"]:
            raise HTTPException(400, "Position already closed")

        exit_p = exit_price or row["entry_price"]  # breakeven default
        entry = row["entry_price"]
        qty = row["quantity"]
        direction = row["direction"]

        if direction == "long":
            pnl = float((exit_p - entry) * qty)
        else:
            pnl = float((entry - exit_p) * qty)

        await session.execute(
            positions.update()
            .where(positions.c.id == position_id)
            .values(exit_price=exit_p, closed_at=datetime.now(timezone.utc), pnl=pnl)
        )
        session.commit()

    return {"ok": True, "pnl": pnl, "exit_price": float(exit_p)}


# ── PnL ─────────────────────────────────────────────────────────────────

@app.get("/api/pnl", response_model=PnLSnapshot)
async def get_pnl():
    async with async_session() as session:
        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=now.weekday())
        month_start = today.replace(day=1)

        # Summary for closed trades
        closed = select(
            func.coalesce(func.sum(positions.c.pnl), 0).label("total"),
            func.count(positions.c.id).label("count"),
        ).where(positions.c.closed_at.isnot(None))

        result = (await session.execute(closed)).mappings().one()
        all_time_pnl = float(result["total"])
        total_trades = result["count"]

        # PnL by period
        def period_query(start):
            return select(
                func.coalesce(func.sum(positions.c.pnl), 0)
            ).where(
                and_(
                    positions.c.closed_at.isnot(None),
                    positions.c.closed_at >= start,
                )
            )

        today_pnl = float((await session.execute(period_query(today))).scalar())
        week_pnl = float((await session.execute(period_query(week_start))).scalar())
        month_pnl = float((await session.execute(period_query(month_start))).scalar())

        # Open count
        open_count = (await session.execute(
            select(func.count()).where(positions.c.closed_at.is_(None))
        )).scalar()

    return PnLSnapshot(
        today_pnl=Decimal(str(today_pnl)),
        week_pnl=Decimal(str(week_pnl)),
        month_pnl=Decimal(str(month_pnl)),
        all_time_pnl=Decimal(str(all_time_pnl)),
        total_trades=total_trades,
        open_positions=open_count,
    )


@app.get("/api/pnl/history", response_model=list[PositionOut])
async def pnl_history(
    limit: int = Query(50, ge=1, le=500),
):
    async with async_session() as session:
        stmt = (
            select(positions)
            .where(positions.c.closed_at.isnot(None))
            .order_by(positions.c.closed_at.desc())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).mappings().all()
    return [position_to_out(r) for r in rows]


# ── Webhook (for scanner scripts) ───────────────────────────────────────

@app.post("/webhook/trade", status_code=201)
async def webhook_trade(payload: WebhookTrade):
    meta = {"strategy": payload.strategy} if payload.strategy else {}
    async with async_session() as session:
        result = await session.execute(positions.insert().values(**{
            "symbol": payload.symbol,
            "direction": payload.direction,
            "entry_price": payload.entry_price,
            "quantity": payload.quantity,
            "exchange": payload.exchange,
            "metadata": meta,
        }))
        session.commit()
        pk = result.inserted_primary_key[0]
    return {"id": str(pk)}


# ── Frontend ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


# ── Startup: run Alembic migrations ──────────────────────────────────────

@app.on_event("startup")
async def startup():
    import alembic.config
    cfg = alembic.config.Config(
        str(Path(__file__).parent.parent / "alembic.ini")
    )
    alembic.config.main.main(command="upgrade", args=["head"], config=cfg)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

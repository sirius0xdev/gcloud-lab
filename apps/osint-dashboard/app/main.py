"""OSINT Dashboard — FastAPI backend.

Real-time geospatial OSINT dashboard API:
- Event ingestion via NATS JetStream consumers
- Full-text search across events (PostgreSQL tsvector)
- Entity tracking and relationship mapping
- Alert management
- Document storage (MinIO-backed)
- Sentiment aggregation and timeline analytics
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import structlog
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session, init_extensions
from models import (
    alerts, documents, entities, entity_events, events, feed_sources
)
from schemas import (
    AlertCreate, AlertOut, AlertSeverity, AlertType, AlertUpdate,
    DashboardSummary, EntityCreate, EntityKind, EntityOut,
    EventCreate, EventOut,
    FeedSourceCreate, FeedSourceOut,
    SearchResult, SentimentSummary, SourceType,
    SearchQuery, TimelinePoint,
)
from ingestor import ingest_event, fetch_and_process
from sources import ingest_rss_feed, ingest_gdelt, ingest_earthquakes, ingest_social_signals

logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger("osint.dashboard")

app = FastAPI(
    title="OSINT Dashboard",
    description="Real-time geospatial OSINT intelligence dashboard",
    version="0.1.0",
)

STATIC_DIR = Path(__file__).parent / "static"


# ── Helpers ───────────────────────────────────────────────────────────────

def event_to_out(row: dict) -> EventOut:
    """Convert DB row dict to EventOut schema."""
    return EventOut(
        id=row["id"],
        source_type=row["source_type"],
        source_id=row["source_id"],
        title=row["title"],
        body=row["body"],
        url=row["url"],
        sentiment_score=row["sentiment_score"],
        sentiment_label=row["sentiment_label"],
        location_lat=row["location_lat"],
        location_lon=row["location_lon"],
        location_name=row["location_name"],
        entities=row["entities"],
        tags=row["tags"],
        ingested_at=row["ingested_at"],
        source_timestamp=row["source_timestamp"],
    )


def entity_to_out(row: dict) -> EntityOut:
    """Convert DB row dict to EntityOut schema."""
    return EntityOut(
        id=row["id"],
        name=row["name"],
        entity_type=row["entity_type"],
        aliases=row["aliases"],
        description=row["description"],
        metadata=row["metadata"],
        location_lat=row["location_lat"],
        location_lon=row["location_lon"],
        event_count=row["event_count"],
        first_seen=row["first_seen"],
        last_seen=row["last_seen"],
    )


def alert_to_out(row: dict) -> AlertOut:
    """Convert DB row dict to AlertOut schema."""
    return AlertOut(
        id=row["id"],
        alert_type=row["alert_type"],
        entity_id=row["entity_id"],
        event_id=row["event_id"],
        severity=row["severity"],
        title=row["title"],
        message=row["message"],
        context=row["context"],
        acknowledged=bool(row["acknowledged"]),
        acknowledged_by=row["acknowledged_by"],
        created_at=row["created_at"],
        resolved_at=row["resolved_at"],
    )


# ── Health ────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    """Health check with database connectivity."""
    async with async_session() as session:
        result = await session.execute(select(func.now()))
        db_time = result.scalar()
    return {"status": "ok", "db_time": db_time.isoformat() if db_time else None}


# ── Startup ───────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Initialize extensions and run migrations."""
    await init_extensions()
    from alembic import command
    from alembic.config import Config
    alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")


# ── Feed Sources ──────────────────────────────────────────────────────────

@app.get("/api/sources", response_model=list[FeedSourceOut])
async def list_sources(enabled_only: bool = Query(True)):
    """List all configured feed sources."""
    async with async_session() as session:
        stmt = select(feed_sources).order_by(feed_sources.c.name)
        if enabled_only:
            stmt = stmt.where(feed_sources.c.enabled == 1)
        rows = (await session.execute(stmt)).mappings().all()
    return [FeedSourceOut(
        id=r["id"], name=r["name"], source_type=r["source_type"],
        url=r["url"], config=r["config"], enabled=bool(r["enabled"]),
        created_at=r["created_at"],
    ) for r in rows]


@app.post("/api/sources", status_code=201)
async def create_source(payload: FeedSourceCreate):
    """Add a new feed source."""
    async with async_session() as session:
        values = payload.model_dump()
        result = await session.execute(feed_sources.insert().values(**values))
        await session.commit()
        pk = result.inserted_primary_key[0]  # type: ignore
    return {"id": str(pk)}


@app.patch("/api/sources/{source_id}")
async def update_source(source_id: UUID, payload: dict):
    """Update a feed source (e.g., toggle enabled)."""
    async with async_session() as session:
        row = (await session.execute(
            select(feed_sources).where(feed_sources.c.id == source_id)
        )).mappings().one_or_none()
        if not row:
            raise HTTPException(404, "Source not found")
        await session.execute(
            feed_sources.update()
            .where(feed_sources.c.id == source_id)
            .values(**payload)
        )
        await session.commit()
    return {"ok": True}


# ── Events ────────────────────────────────────────────────────────────────

@app.get("/api/events", response_model=list[EventOut])
async def list_events(
    source_type: SourceType | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List recent ingested events."""
    async with async_session() as session:
        stmt = select(events).order_by(events.c.ingested_at.desc())
        if source_type:
            stmt = stmt.where(events.c.source_type == source_type.value)
        stmt = stmt.limit(limit).offset(offset)
        rows = (await session.execute(stmt)).mappings().all()
    return [event_to_out(r) for r in rows]


@app.get("/api/events/{event_id}", response_model=EventOut)
async def get_event(event_id: UUID):
    """Get a single event by ID."""
    async with async_session() as session:
        row = (await session.execute(
            select(events).where(events.c.id == event_id)
        )).mappings().one_or_none()
        if not row:
            raise HTTPException(404, "Event not found")
    return event_to_out(row)


@app.post("/api/events", status_code=201)
async def create_event(payload: EventCreate):
    """Manually ingest an event (bypasses NATS)."""
    values = payload.model_dump(exclude_unset=True)
    if not values.get("source_timestamp"):
        values["source_timestamp"] = datetime.now(timezone.utc)
    event_id = await ingest_event(values)
    return {"id": str(event_id)}


# ── Search ────────────────────────────────────────────────────────────────

@app.post("/api/search", response_model=SearchResult)
async def search_events(query: SearchQuery):
    """Full-text search across events with optional filters."""
    async with async_session() as session:
        # Build query with tsvector full-text search (parameterized to avoid SQL injection)
        tsquery_param = text("plainto_tsquery('english', :q)")
        
        base_stmt = select(
            events,
            func.count().over().label("total")
        ).where(
            events.c.search_vector.op("@@")(tsquery_param)
        )

        # Apply filters
        if query.source_type:
            base_stmt = base_stmt.where(events.c.source_type == query.source_type.value)
        if query.entity_id:
            base_stmt = base_stmt.join(
                entity_events, entity_events.c.event_id == events.c.id
            ).where(entity_events.c.entity_id == query.entity_id)
        if query.sentiment:
            base_stmt = base_stmt.where(events.c.sentiment_label == query.sentiment.value)
        if query.min_date:
            base_stmt = base_stmt.where(events.c.source_timestamp >= query.min_date)
        if query.max_date:
            base_stmt = base_stmt.where(events.c.source_timestamp <= query.max_date)
        if query.min_lat is not None and query.max_lat is not None:
            base_stmt = base_stmt.where(
                and_(
                    events.c.location_lat >= query.min_lat,
                    events.c.location_lat <= query.max_lat,
                )
            )
        if query.min_lon is not None and query.max_lon is not None:
            base_stmt = base_stmt.where(
                and_(
                    events.c.location_lon >= query.min_lon,
                    events.c.location_lon <= query.max_lon,
                )
            )

        base_stmt = base_stmt.order_by(events.c.ingested_at.desc())
        base_stmt = base_stmt.limit(query.limit).offset(query.offset)

        result = (await session.execute(base_stmt, {"q": query.q})).mappings().all()
        if result:
            total = result[0]["total"]
        else:
            total = 0
        evts = [event_to_out(r) for r in result]

    return SearchResult(
        events=evts,
        total=total,
        has_more=query.offset + len(evts) < total,
    )


# ── Entities ──────────────────────────────────────────────────────────────

@app.get("/api/entities", response_model=list[EntityOut])
async def list_entities(
    entity_type: EntityKind | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    """List tracked entities."""
    async with async_session() as session:
        stmt = select(entities).order_by(entities.c.event_count.desc())
        if entity_type:
            stmt = stmt.where(entities.c.entity_type == entity_type.value)
        stmt = stmt.limit(limit)
        rows = (await session.execute(stmt)).mappings().all()
    return [entity_to_out(r) for r in rows]


@app.get("/api/entities/{entity_id}", response_model=EntityOut)
async def get_entity(entity_id: UUID):
    """Get entity details with recent events."""
    async with async_session() as session:
        row = (await session.execute(
            select(entities).where(entities.c.id == entity_id)
        )).mappings().one_or_none()
        if not row:
            raise HTTPException(404, "Entity not found")
    return entity_to_out(row)


@app.post("/api/entities", status_code=201)
async def create_entity(payload: EntityCreate):
    """Create or update a tracked entity."""
    async with async_session() as session:
        # Check if entity already exists by name
        existing = (await session.execute(
            select(entities).where(entities.c.name == payload.name)
        )).mappings().one_or_none()

        if existing:
            # Update
            updates = payload.model_dump(exclude_unset=True)
            updates["last_seen"] = datetime.now(timezone.utc)
            await session.execute(
                entities.update()
                .where(entities.c.id == existing["id"])
                .values(**updates)
            )
            await session.commit()
            return {"id": str(existing["id"]), "created": False}

        # Create
        values = payload.model_dump()
        result = await session.execute(entities.insert().values(**values))
        await session.commit()
        pk = result.inserted_primary_key[0]  # type: ignore
    return {"id": str(pk), "created": True}


@app.get("/api/entities/{entity_id}/events", response_model=list[EventOut])
async def get_entity_events(
    entity_id: UUID,
    limit: int = Query(50, ge=1, le=500),
):
    """Get events linked to a specific entity."""
    async with async_session() as session:
        stmt = (
            select(events)
            .join(entity_events, entity_events.c.event_id == events.c.id)
            .where(entity_events.c.entity_id == entity_id)
            .order_by(events.c.source_timestamp.desc())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).mappings().all()
    return [event_to_out(r) for r in rows]


# ── Alerts ────────────────────────────────────────────────────────────────

@app.get("/api/alerts", response_model=list[AlertOut])
async def list_alerts(
    severity: AlertSeverity | None = Query(None),
    acknowledged: bool | None = Query(None),
    entity_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    """List alerts with optional filters."""
    async with async_session() as session:
        stmt = select(alerts).order_by(
            alerts.c.severity.desc(), alerts.c.created_at.desc()
        )
        if severity:
            stmt = stmt.where(alerts.c.severity == severity.value)
        if acknowledged is not None:
            stmt = stmt.where(alerts.c.acknowledged == int(acknowledged))
        if entity_id:
            stmt = stmt.where(alerts.c.entity_id == entity_id)
        stmt = stmt.limit(limit)
        rows = (await session.execute(stmt)).mappings().all()
    return [alert_to_out(r) for r in rows]


@app.post("/api/alerts", status_code=201)
async def create_alert(payload: AlertCreate):
    """Create a new alert."""
    async with async_session() as session:
        values = payload.model_dump()
        result = await session.execute(alerts.insert().values(**values))
        await session.commit()
        pk = result.inserted_primary_key[0]  # type: ignore
    return {"id": str(pk)}


@app.patch("/api/alerts/{alert_id}")
async def update_alert(alert_id: UUID, payload: AlertUpdate):
    """Update alert (acknowledge, resolve)."""
    async with async_session() as session:
        row = (await session.execute(
            select(alerts).where(alerts.c.id == alert_id)
        )).mappings().one_or_none()
        if not row:
            raise HTTPException(404, "Alert not found")
        updates = payload.model_dump(exclude_unset=True)
        if "acknowledged" in updates:
            updates["acknowledged"] = int(updates["acknowledged"])
        await session.execute(
            alerts.update().where(alerts.c.id == alert_id).values(**updates)
        )
        await session.commit()
    return {"ok": True}


# ── Documents ─────────────────────────────────────────────────────────────

@app.get("/api/documents", response_model=dict)
async def list_documents(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List documents indexed in MinIO."""
    async with async_session() as session:
        stmt = select(documents).order_by(documents.c.uploaded_at.desc()).limit(limit).offset(offset)
        rows = (await session.execute(stmt)).mappings().all()
    return {
        "documents": [{
            "id": str(r["id"]), "bucket": r["bucket"], "object_key": r["object_key"],
            "content_type": r["content_type"], "size_bytes": r["size_bytes"],
            "description": r["description"], "tags": r["tags"],
            "event_id": str(r["event_id"]) if r["event_id"] else None,
            "uploaded_at": r["uploaded_at"].isoformat() if r["uploaded_at"] else None,
        } for r in rows],
    }


# ── Ingestion Triggers ───────────────────────────────────────────────────

@app.post("/api/ingest/rss")
async def trigger_rss_ingest(feed_url: str, source_id: str | None = None):
    """Trigger RSS feed ingestion."""
    count = await ingest_rss_feed(feed_url, source_id)
    return {"status": "ok", "items_ingested": count}


@app.post("/api/ingest/gdelt")
async def trigger_gdelt_ingest(query: str = "", max_articles: int = 50):
    """Trigger GDELT data ingestion."""
    count = await ingest_gdelt(query, max_articles)
    return {"status": "ok", "articles_ingested": count}


@app.post("/api/ingest/earthquakes")
async def trigger_earthquake_ingest():
    """Trigger USGS earthquake ingestion."""
    count = await ingest_earthquakes()
    return {"status": "ok", "events_ingested": count}


@app.post("/api/ingest/social")
async def trigger_social_ingest(query: str = "", max_items: int = 50):
    """Trigger social signals ingestion."""
    count = await ingest_social_signals(query, max_items)
    return {"status": "ok", "signals_ingested": count}


@app.post("/api/ingest/process")
async def trigger_nats_processing(batch_size: int = 100):
    """Process pending NATS JetStream messages."""
    count = await fetch_and_process(batch_size)
    return {"status": "ok", "processed": count}


# ── Analytics / Aggregation ───────────────────────────────────────────────

@app.get("/api/analytics/summary", response_model=DashboardSummary)
async def get_dashboard_summary():
    """Dashboard overview: event counts, sentiment, top entities, alerts."""
    async with async_session() as session:
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(hours=24)

        # Total events
        total = (await session.execute(
            select(func.count()).select_from(events)
        )).scalar() or 0

        # Events in last 24h
        events_24h = (await session.execute(
            select(func.count()).where(events.c.ingested_at >= yesterday)
        )).scalar() or 0

        # Active sources
        active = (await session.execute(
            select(func.count()).where(feed_sources.c.enabled == 1)
        )).scalar() or 0

        # Open alerts
        open_alerts = (await session.execute(
            select(func.count()).where(alerts.c.acknowledged == 0)
        )).scalar() or 0

        # Tracked entities
        ent_count = (await session.execute(
            select(func.count()).select_from(entities)
        )).scalar() or 0

        # Sentiment breakdown (last 24h)
        def sentiment_query():
            return select(
                func.count().where(events.c.sentiment_label == "positive").label("pos"),
                func.count().where(events.c.sentiment_label == "neutral").label("neu"),
                func.count().where(events.c.sentiment_label == "negative").label("neg"),
                func.avg(events.c.sentiment_score).label("avg"),
            ).where(events.c.ingested_at >= yesterday)

        sent_row = (await session.execute(sentiment_query())).mappings().one()
        sentiment = SentimentSummary(
            period="24h",
            positive_count=sent_row["pos"] or 0,
            neutral_count=sent_row["neu"] or 0,
            negative_count=sent_row["neg"] or 0,
            avg_score=float(sent_row["avg"] or 0),
        )

        # Top entities by event count
        top_ent = (await session.execute(
            select(entities).order_by(entities.c.event_count.desc()).limit(10)
        )).mappings().all()

    return DashboardSummary(
        total_events=total,
        events_last_24h=events_24h,
        active_sources=active,
        open_alerts=open_alerts,
        tracked_entities=ent_count,
        sentiment=sentiment,
        top_entities=[entity_to_out(r) for r in top_ent],
    )


@app.get("/api/analytics/timeline")
async def get_timeline(
    hours: int = Query(24, ge=1, le=168),
    bucket_hours: int = Query(1, ge=1, le=24),
):
    """Event timeline: counts and avg sentiment per time bucket."""
    async with async_session() as session:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        # Use date_trunc for bucketing
        buckets = await session.execute(text(f"""
            SELECT
                date_trunc('hour', source_timestamp) AS ts,
                COUNT(*) AS event_count,
                COALESCE(AVG(sentiment_score), 0) AS avg_sentiment
            FROM events
            WHERE source_timestamp >= :cutoff
            GROUP BY ts
            ORDER BY ts
        """), {"cutoff": cutoff})
        rows = buckets.mappings().all()

    return [TimelinePoint(timestamp=r["ts"], event_count=r["event_count"],
                           avg_sentiment=float(r["avg_sentiment"])) for r in rows]


@app.get("/api/analytics/sentiment/by-source")
async def sentiment_by_source(hours: int = 24):
    """Sentiment breakdown grouped by source type."""
    async with async_session() as session:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await session.execute(text(f"""
            SELECT
                source_type,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE sentiment_label = 'positive') AS positive,
                COUNT(*) FILTER (WHERE sentiment_label = 'neutral') AS neutral,
                COUNT(*) FILTER (WHERE sentiment_label = 'negative') AS negative,
                COALESCE(AVG(sentiment_score), 0) AS avg_score
            FROM events
            WHERE ingested_at >= :cutoff
            GROUP BY source_type
            ORDER BY total DESC
        """), {"cutoff": cutoff})
        rows = result.mappings().all()
    return [{
        "source_type": r["source_type"],
        "total": r["total"],
        "positive": r["positive"],
        "neutral": r["neutral"],
        "negative": r["negative"],
        "avg_score": float(r["avg_score"]),
    } for r in rows]


# ── Frontend ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

"""NATS JetStream consumer — ingests OSINT events from NATS streams."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import nats
from nats.errors import TimeoutError

from database import async_session
from models import events as events_table

logger = logging.getLogger("osint.ingestor")

# NATS connection settings
NATS_URLS = "nats://osint-nats.customer1.svc.cluster.local:4222"
NATS_STREAM = "events"
NATS_DURABLE = "osint-ingestor"

# Redis cache settings
REDIS_URL = "redis://osint-redis-sentinel.customer1.svc.cluster.local:26379/0"


async def ingest_event(msg: dict):
    """Ingest a single event from NATS into PostgreSQL."""
    event_row = {
        "source_type": msg.get("source_type", "rss"),
        "source_id": msg.get("source_id"),
        "title": msg.get("title"),
        "body": msg.get("body"),
        "url": msg.get("url"),
        "sentiment_score": msg.get("sentiment_score"),
        "sentiment_label": msg.get("sentiment_label"),
        "location_lat": msg.get("location_lat"),
        "location_lon": msg.get("location_lon"),
        "location_name": msg.get("location_name"),
        "entities": msg.get("entities", []),
        "tags": msg.get("tags", []),
        "raw": msg.get("raw"),
        "source_timestamp": msg.get("source_timestamp", datetime.now(timezone.utc).isoformat()),
    }

    # Parse timestamp if string
    if isinstance(event_row["source_timestamp"], str):
        event_row["source_timestamp"] = datetime.fromisoformat(event_row["source_timestamp"])

    async with async_session() as session:
        result = await session.execute(events_table.insert().values(**event_row))
        await session.commit()
        event_id = result.inserted_primary_key[0]  # type: ignore[union-attr]
    logger.info("Ingested event %s from source %s", event_id, msg.get("source_type"))
    return event_id


async def start_nats_consumer():
    """Start NATS JetStream consumer for OSINT events."""
    nc = await nats.connect(NATS_URLS)
    js = nc.jetstream()

    # Create stream if not exists
    try:
        await js.add_stream(
            name=NATS_STREAM,
            subjects=[
                "events.gdelt", "events.rss", "events.social",
                "events.earthquake", "events.disaster", "events.weather",
                "events.fire", "events.satellite", "events.new", "events.alert",
            ],
            retention=nats.js.api.RetentionPolicy.INTERESTS,
            max_msgs=1_000_000,
        )
        logger.info("Created NATS stream %s", NATS_STREAM)
    except Exception:
        logger.debug("Stream %s already exists", NATS_STREAM)

    # Create durable consumer
    sub = await js.pull_subscribe(
        subject="events.>",
        durable_name=NATS_DURABLE,
    )

    logger.info("NATS consumer started, durable=%s", NATS_DURABLE)
    return nc, sub


async def fetch_and_process(batch_size: int = 100):
    """Fetch a batch of messages and process them."""
    nc, sub = await start_nats_consumer()
    js = nc.jetstream()

    msgs = await sub.fetch(batch_size, timeout=5)
    processed = 0

    for msg in msgs:
        try:
            data = json.loads(msg.data)
            await ingest_event(data)
            await msg.ack()
            processed += 1
        except Exception:
            logger.error("Failed to process message: %s", msg.data, exc_info=True)

    await nc.close()
    logger.info("Processed %d messages in batch", processed)
    return processed

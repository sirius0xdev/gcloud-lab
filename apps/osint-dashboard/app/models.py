"""OSINT Dashboard — SQLAlchemy models (async, declarative)."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Column, Enum, Float, Index, Integer, String, Text,
    DateTime, JSON, func, Table,
)
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR

from database import metadata


# ── Feed Sources ──────────────────────────────────────────────────────────

feed_sources = Table(
    "feed_sources",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid4),
    Column("name", String(256), nullable=False),
    Column("source_type", Enum(
        "rss", "gdel-t2", "social", "earthquake", "disaster",
        "weather", "fire", "satellite", name="feed_source_type"
    ), nullable=False),
    Column("url", Text),
    Column("config", JSON),
    Column("enabled", Integer, server_default="1", nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
)


# ── Events (hypertable via TimescaleDB) ──────────────────────────────────

events = Table(
    "events",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid4),
    Column("source_type", Enum(
        "rss", "gdel-t2", "social", "earthquake", "disaster",
        "weather", "fire", "satellite", name="event_source_type"
    ), nullable=False, index=True),
    Column("source_id", UUID(as_uuid=True)),
    Column("title", Text),
    Column("body", Text),
    Column("url", Text),
    Column("sentiment_score", Float),
    Column("sentiment_label", Enum("positive", "neutral", "negative", name="sentiment_label")),
    Column("location_lat", Float),
    Column("location_lon", Float),
    Column("location_name", String(512)),
    Column("entities", JSON),
    Column("tags", JSON),
    Column("raw", JSON),
    Column("ingested_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("source_timestamp", DateTime(timezone=True), nullable=False),
    # Full-text search vector
    Column(
        "search_vector",
        TSVECTOR,
        nullable=True,
    ),
)

# GIN index for full-text search
Index("ix_events_search_vector", events.c.search_vector, postgresql_using="gin")
# Spatial index on location
Index("ix_events_location", events.c.location_lat, events.c.location_lon)


# ── Entities (people, organizations, locations of interest) ──────────────

entities = Table(
    "entities",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid4),
    Column("name", String(512), nullable=False, index=True),
    Column("entity_type", Enum(
        "person", "organization", "location", "topic", "asset",
        name="entity_type"
    ), nullable=False),
    Column("aliases", JSON),
    Column("description", Text),
    Column("metadata", JSON),
    Column("location_lat", Float),
    Column("location_lon", Float),
    Column("event_count", Integer, server_default="0"),
    Column("first_seen", DateTime(timezone=True), server_default=func.now()),
    Column("last_seen", DateTime(timezone=True), server_default=func.now()),
)


# ── Entity-Event Link ────────────────────────────────────────────────────

entity_events = Table(
    "entity_events",
    metadata,
    Column("entity_id", UUID(as_uuid=True), primary_key=True),
    Column("event_id", UUID(as_uuid=True), primary_key=True),
    Column("relevance_score", Float),
    Column("linked_at", DateTime(timezone=True), server_default=func.now()),
)


# ── Alerts ───────────────────────────────────────────────────────────────

alerts = Table(
    "alerts",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid4),
    Column("alert_type", Enum(
        "entity_mention", "sentiment_shift", "geo_proximity",
        "keyword_match", "threshold", "anomaly",
        name="alert_type"
    ), nullable=False),
    Column("entity_id", UUID(as_uuid=True)),
    Column("event_id", UUID(as_uuid=True)),
    Column("severity", Enum("low", "medium", "high", "critical", name="alert_severity"), nullable=False),
    Column("title", Text, nullable=False),
    Column("message", Text),
    Column("context", JSON),
    Column("acknowledged", Integer, server_default="0"),
    Column("acknowledged_by", String(256)),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("resolved_at", DateTime(timezone=True)),
)

Index("ix_alerts_severity_created", alerts.c.severity, alerts.c.created_at.desc())
Index("ix_alerts_entity", alerts.c.entity_id)


# ── Documents (stored in MinIO, indexed here) ────────────────────────────

documents = Table(
    "documents",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid4),
    Column("bucket", String(256), nullable=False),
    Column("object_key", String(1024), nullable=False),
    Column("content_type", String(256)),
    Column("size_bytes", Integer),
    Column("description", Text),
    Column("tags", JSON),
    Column("event_id", UUID(as_uuid=True)),
    Column("uploaded_at", DateTime(timezone=True), server_default=func.now()),
)

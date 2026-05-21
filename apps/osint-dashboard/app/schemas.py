"""OSINT Dashboard — Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ─── Enums ───────────────────────────────────────────────────────────────

class SourceType(str, Enum):
    rss = "rss"
    gdel_t2 = "gdel-t2"
    social = "social"
    earthquake = "earthquake"
    disaster = "disaster"
    weather = "weather"
    fire = "fire"
    satellite = "satellite"


class EntityKind(str, Enum):
    person = "person"
    organization = "organization"
    location = "location"
    topic = "topic"
    asset = "asset"


class Sentiment(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class AlertType(str, Enum):
    entity_mention = "entity_mention"
    sentiment_shift = "sentiment_shift"
    geo_proximity = "geo_proximity"
    keyword_match = "keyword_match"
    threshold = "threshold"
    anomaly = "anomaly"


class AlertSeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


# ─── Feed Sources ───────────────────────────────────────────────────────

class FeedSourceCreate(BaseModel):
    name: str
    source_type: SourceType
    url: Optional[str] = None
    config: Optional[dict] = None


class FeedSourceOut(BaseModel):
    id: UUID
    name: str
    source_type: SourceType
    url: Optional[str]
    config: Optional[dict]
    enabled: bool
    created_at: datetime


# ─── Events ─────────────────────────────────────────────────────────────

class EventCreate(BaseModel):
    source_type: SourceType
    source_id: Optional[UUID] = None
    title: Optional[str] = None
    body: Optional[str] = None
    url: Optional[str] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[Sentiment] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    location_name: Optional[str] = None
    entities: Optional[list[dict]] = None
    tags: Optional[list[str]] = None
    raw: Optional[dict] = None
    source_timestamp: Optional[datetime] = None


class EventOut(BaseModel):
    id: UUID
    source_type: SourceType
    source_id: Optional[UUID]
    title: Optional[str]
    body: Optional[str]
    url: Optional[str]
    sentiment_score: Optional[float]
    sentiment_label: Optional[Sentiment]
    location_lat: Optional[float]
    location_lon: Optional[float]
    location_name: Optional[str]
    entities: Optional[list[dict]]
    tags: Optional[list[str]]
    ingested_at: datetime
    source_timestamp: datetime


# ─── Search ──────────────────────────────────────────────────────────────

class SearchQuery(BaseModel):
    q: str = Field(..., min_length=1, max_length=500)
    source_type: Optional[SourceType] = None
    entity_id: Optional[UUID] = None
    sentiment: Optional[Sentiment] = None
    min_date: Optional[datetime] = None
    max_date: Optional[datetime] = None
    min_lat: Optional[float] = None
    max_lat: Optional[float] = None
    min_lon: Optional[float] = None
    max_lon: Optional[float] = None
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)


class SearchResult(BaseModel):
    events: list[EventOut]
    total: int
    has_more: bool


# ─── Entities ────────────────────────────────────────────────────────────

class EntityCreate(BaseModel):
    name: str
    entity_type: EntityKind
    aliases: Optional[list[str]] = None
    description: Optional[str] = None
    metadata: Optional[dict] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None


class EntityOut(BaseModel):
    id: UUID
    name: str
    entity_type: EntityKind
    aliases: Optional[list[str]]
    description: Optional[str]
    metadata: Optional[dict]
    location_lat: Optional[float]
    location_lon: Optional[float]
    event_count: int
    first_seen: datetime
    last_seen: datetime


# ─── Alerts ──────────────────────────────────────────────────────────────

class AlertCreate(BaseModel):
    alert_type: AlertType
    entity_id: Optional[UUID] = None
    event_id: Optional[UUID] = None
    severity: AlertSeverity
    title: str
    message: Optional[str] = None
    context: Optional[dict] = None


class AlertUpdate(BaseModel):
    acknowledged: Optional[bool] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None


class AlertOut(BaseModel):
    id: UUID
    alert_type: AlertType
    entity_id: Optional[UUID]
    event_id: Optional[UUID]
    severity: AlertSeverity
    title: str
    message: Optional[str]
    context: Optional[dict]
    acknowledged: bool
    acknowledged_by: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]


# ─── Documents ───────────────────────────────────────────────────────────

class DocumentCreate(BaseModel):
    bucket: str
    object_key: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    event_id: Optional[UUID] = None


class DocumentOut(BaseModel):
    id: UUID
    bucket: str
    object_key: str
    content_type: Optional[str]
    size_bytes: Optional[int]
    description: Optional[str]
    tags: Optional[list[str]]
    event_id: Optional[UUID]
    uploaded_at: datetime


# ─── Aggregations ────────────────────────────────────────────────────────

class SentimentSummary(BaseModel):
    period: str
    positive_count: int
    neutral_count: int
    negative_count: int
    avg_score: float


class TimelinePoint(BaseModel):
    timestamp: datetime
    event_count: int
    avg_sentiment: float


class DashboardSummary(BaseModel):
    total_events: int
    events_last_24h: int
    active_sources: int
    open_alerts: int
    tracked_entities: int
    sentiment: SentimentSummary
    top_entities: list[EntityOut]


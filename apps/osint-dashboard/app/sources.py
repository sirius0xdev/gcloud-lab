"""Data source ingestors — fetch from external APIs and push to NATS."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx
import feedparser
import nats

logger = logging.getLogger("osint.sources")


def _parse_rfc822(date_str: object) -> str | None:
    """Parse RFC-822 date string from feedparser entries."""
    if not isinstance(date_str, str):
        return None
    try:
        return parsedate_to_datetime(date_str).astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError):
        return None

# NATS connection
NATS_URLS = "nats://osint-nats.customer1.svc.cluster.local:4222"


async def publish_event(subject: str, event: dict):
    """Publish an event to NATS JetStream."""
    nc = await nats.connect(NATS_URLS)
    js = nc.jetstream()
    await js.publish(subject, json.dumps(event).encode())
    await nc.close()
    logger.debug("Published event to %s", subject)


# ─── RSS Feed Ingestor ──────────────────────────────────────────────────

async def ingest_rss_feed(feed_url: str, source_id: str = None):
    """Fetch and parse an RSS feed, publish items to NATS."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(feed_url)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)

    count = 0
    for entry in feed.entries[:100]:  # max 100 per run
        event = {
            "source_type": "rss",
            "source_id": source_id,
            "title": entry.get("title"),
            "body": entry.get("summary") or entry.get("description"),
            "url": entry.get("link"),
            "source_timestamp": _parse_rfc822(entry.get("published"))
                or datetime.now(timezone.utc).isoformat(),
            "tags": [t.get("term") for t in entry.get("tags", []) if t.get("term")],
            "raw": {
                "feed_title": feed.feed.get("title"),
                "author": entry.get("author"),
                "categories": [c.get("term") for c in entry.get("categories", [])],
            },
        }
        await publish_event("events.rss", event)
        count += 1

    logger.info("Ingested %d items from RSS feed %s", count, feed_url)
    return count


# ─── GDELT 2.0 Ingestor ─────────────────────────────────────────────────

GDELT_API = "https://api.gdeltproject.org/gdeltv2"


async def ingest_gdelt(query: str = "", max_articles: int = 50):
    """Fetch articles from GDELT 2.0 API."""
    params = {
        "mode": "artlist",
        "format": "json",
        "maxrecords": max_articles,
        "mode": "artlist",
    }
    if query:
        params["search"] = query

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(GDELT_API, params=params)
        resp.raise_for_status()
        data = resp.json()

    count = 0
    for article in data.get("articles", []):
        event = {
            "source_type": "gdel-t2",
            "title": article.get("title"),
            "body": article.get("articleBody"),
            "url": article.get("url"),
            "sentiment_score": _parse_gdelt_tone(article.get("Tone", "0")),
            "location_lat": article.get("Latitude"),
            "location_lon": article.get("Longitude"),
            "location_name": article.get("Location"),
            "source_timestamp": article.get("FirstCreated"),
            "entities": [
                {"name": e.get("Topic"), "type": "topic"}
                for e in article.get("Mentions", [])
                if e.get("Topic")
            ],
            "raw": article,
        }
        await publish_event("events.gdelt", event)
        count += 1

    logger.info("Ingested %d articles from GDELT", count)
    return count


def _parse_gdelt_tone(tone: str) -> float | None:
    """Parse GDELT tone string to a -1..1 sentiment score."""
    try:
        tone_float = float(tone)
        return max(-1.0, min(1.0, tone_float / 4249.0))  # GDELT tone range
    except (ValueError, TypeError):
        return None


# ─── Earthquake Ingestor (USGS) ─────────────────────────────────────────

USGS_API = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"


async def ingest_earthquakes():
    """Fetch recent earthquakes from USGS."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(USGS_API)
        resp.raise_for_status()
        data = resp.json()

    count = 0
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {}).get("coordinates", [])
        event = {
            "source_type": "earthquake",
            "title": props.get("title"),
            "body": props.get("description"),
            "url": props.get("url"),
            "location_lat": geometry[1] if len(geometry) > 1 else None,
            "location_lon": geometry[0] if len(geometry) > 0 else None,
            "location_name": props.get("place"),
            "sentiment_label": "neutral",
            "tags": [f"magnitude:{props.get('mag')}"] if props.get("mag") else [],
            "source_timestamp": (
                datetime.utcfromtimestamp(props.get("time", 0) / 1000)
                .replace(tzinfo=timezone.utc)
                .isoformat()
            ),
            "raw": props,
        }
        await publish_event("events.earthquake", event)
        count += 1

    logger.info("Ingested %d earthquake events", count)
    return count


# ─── Social Signals (Twitter/X-like placeholder) ────────────────────────

async def ingest_social_signals(query: str = "", max_items: int = 50):
    """Placeholder for social media signal ingestion.

    In production, this would connect to Twitter API, Reddit, NewsAPI, etc.
    For now, it publishes a heartbeat to signal the pipeline is active.
    """
    event = {
        "source_type": "social",
        "title": f"Social signal scan: {query}",
        "body": f"Scanned for '{query}' — placeholder connector",
        "source_timestamp": datetime.now(timezone.utc).isoformat(),
        "tags": [query] if query else [],
        "raw": {"query": query, "max_items": max_items, "connector": "placeholder"},
    }
    await publish_event("events.social", event)
    logger.info("Social signal scan complete for '%s'", query)
    return 1

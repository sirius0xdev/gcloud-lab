"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-05-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR, ENUM

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enums
    op.execute("CREATE TYPE feed_source_type AS ENUM ('rss', 'gdel-t2', 'social', 'earthquake', 'disaster', 'weather', 'fire', 'satellite')")
    op.execute("CREATE TYPE event_source_type AS ENUM ('rss', 'gdel-t2', 'social', 'earthquake', 'disaster', 'weather', 'fire', 'satellite')")
    op.execute("CREATE TYPE sentiment_label AS ENUM ('positive', 'neutral', 'negative')")
    op.execute("CREATE TYPE entity_type AS ENUM ('person', 'organization', 'location', 'topic', 'asset')")
    op.execute("CREATE TYPE alert_type AS ENUM ('entity_mention', 'sentiment_shift', 'geo_proximity', 'keyword_match', 'threshold', 'anomaly')")
    op.execute("CREATE TYPE alert_severity AS ENUM ('low', 'medium', 'high', 'critical')")

    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    # feed_sources
    op.create_table(
        'feed_sources',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('source_type', sa.Enum('rss', 'gdel-t2', 'social', 'earthquake', 'disaster', 'weather', 'fire', 'satellite', name='feed_source_type'), nullable=False),
        sa.Column('url', sa.Text()),
        sa.Column('config', sa.JSON()),
        sa.Column('enabled', sa.Integer, server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # events (will become hypertable)
    op.create_table(
        'events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('source_type', sa.Enum('rss', 'gdel-t2', 'social', 'earthquake', 'disaster', 'weather', 'fire', 'satellite', name='event_source_type'), nullable=False, index=True),
        sa.Column('source_id', UUID(as_uuid=True)),
        sa.Column('title', sa.Text()),
        sa.Column('body', sa.Text()),
        sa.Column('url', sa.Text()),
        sa.Column('sentiment_score', sa.Float()),
        sa.Column('sentiment_label', sa.Enum('positive', 'neutral', 'negative', name='sentiment_label')),
        sa.Column('location_lat', sa.Float()),
        sa.Column('location_lon', sa.Float()),
        sa.Column('location_name', sa.String(512)),
        sa.Column('entities', sa.JSON()),
        sa.Column('tags', sa.JSON()),
        sa.Column('raw', sa.JSON()),
        sa.Column('ingested_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('source_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('search_vector', TSVECTOR),
    )

    # Convert events to TimescaleDB hypertable
    op.execute("SELECT create_hypertable('events', 'ingested_at', if_not_exists => TRUE)")

    # GIN index for full-text search
    op.create_index('ix_events_search_vector', 'events', ['search_vector'], postgresql_using='gin')
    # Spatial index
    op.create_index('ix_events_location', 'events', ['location_lat', 'location_lon'])

    # entities
    op.create_table(
        'entities',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(512), nullable=False, index=True),
        sa.Column('entity_type', sa.Enum('person', 'organization', 'location', 'topic', 'asset', name='entity_type'), nullable=False),
        sa.Column('aliases', sa.JSON()),
        sa.Column('description', sa.Text()),
        sa.Column('metadata', sa.JSON()),
        sa.Column('location_lat', sa.Float()),
        sa.Column('location_lon', sa.Float()),
        sa.Column('event_count', sa.Integer, server_default='0'),
        sa.Column('first_seen', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_seen', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # entity_events
    op.create_table(
        'entity_events',
        sa.Column('entity_id', UUID(as_uuid=True), primary_key=True),
        sa.Column('event_id', UUID(as_uuid=True), primary_key=True),
        sa.Column('relevance_score', sa.Float()),
        sa.Column('linked_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # alerts
    op.create_table(
        'alerts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('alert_type', sa.Enum('entity_mention', 'sentiment_shift', 'geo_proximity', 'keyword_match', 'threshold', 'anomaly', name='alert_type'), nullable=False),
        sa.Column('entity_id', UUID(as_uuid=True)),
        sa.Column('event_id', UUID(as_uuid=True)),
        sa.Column('severity', sa.Enum('low', 'medium', 'high', 'critical', name='alert_severity'), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('message', sa.Text()),
        sa.Column('context', sa.JSON()),
        sa.Column('acknowledged', sa.Integer, server_default='0'),
        sa.Column('acknowledged_by', sa.String(256)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_alerts_severity_created', 'alerts', ['severity', 'created_at'])
    op.create_index('ix_alerts_entity', 'alerts', ['entity_id'])

    # documents
    op.create_table(
        'documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('bucket', sa.String(256), nullable=False),
        sa.Column('object_key', sa.String(1024), nullable=False),
        sa.Column('content_type', sa.String(256)),
        sa.Column('size_bytes', sa.Integer()),
        sa.Column('description', sa.Text()),
        sa.Column('tags', sa.JSON()),
        sa.Column('event_id', UUID(as_uuid=True)),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('documents')
    op.drop_table('alerts')
    op.drop_table('entity_events')
    op.drop_table('entities')
    op.execute("SELECT drop_hypertable('events', cascade => TRUE)")
    op.drop_table('events')
    op.drop_table('feed_sources')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS feed_source_type")
    op.execute("DROP TYPE IF EXISTS event_source_type")
    op.execute("DROP TYPE IF EXISTS sentiment_label")
    op.execute("DROP TYPE IF EXISTS entity_type")
    op.execute("DROP TYPE IF EXISTS alert_type")
    op.execute("DROP TYPE IF EXISTS alert_severity")

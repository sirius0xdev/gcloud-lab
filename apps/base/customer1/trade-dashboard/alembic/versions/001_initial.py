"""initial schema — positions table

Revision ID: 001_initial
Create Date: 2026-05-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE TYPE position_direction AS ENUM (\'long\', \'short\')')

    op.create_table(
        "positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("direction", postgresql.ENUM("long", "short", name="position_direction", create_type=False), nullable=False),
        sa.Column("entry_price", sa.Numeric(precision=16, scale=8), nullable=False),
        sa.Column("exit_price", sa.Numeric(precision=16, scale=8)),
        sa.Column("quantity", sa.Numeric(precision=16, scale=8), nullable=False),
        sa.Column("exchange", sa.String(32), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("pnl", sa.Numeric(precision=16, scale=2)),
        sa.Column("metadata", sa.JSON),
    )

    op.create_index(op.f("ix_positions_symbol"), "positions", ["symbol"])
    op.create_index(op.f("ix_positions_exchange"), "positions", ["exchange"])


def downgrade() -> None:
    op.drop_index(op.f("ix_positions_exchange"), table_name="positions")
    op.drop_index(op.f("ix_positions_symbol"), table_name="positions")
    op.drop_table("positions")
    op.execute("DROP TYPE IF EXISTS position_direction")

"""endpoint responses: the body and headers a probed endpoint answered with

Revision ID: e7a1c4d92f60
Revises: b4d2e7c91a35
Create Date: 2026-09-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e7a1c4d92f60"
down_revision: str | None = "b4d2e7c91a35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "endpoint_responses",
        sa.Column("endpoint_id", sa.Uuid(), primary_key=True),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("raw_response_header", sa.Text(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["endpoint_id"], ["endpoints.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_endpoint_responses_scan_id", "endpoint_responses", ["scan_id"])


def downgrade() -> None:
    op.execute(
        "UPDATE secret_coverage SET source = 'stored_responses' "
        "WHERE source = 'web_asset_responses'"
    )
    op.drop_index("ix_endpoint_responses_scan_id", table_name="endpoint_responses")
    op.drop_table("endpoint_responses")

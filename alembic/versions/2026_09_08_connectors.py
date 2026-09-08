"""connectors: proxy connections, the shapes they see, and the browsing sessions

Revision ID: d41c7b9e2a10
Revises: b93f27c05ea8
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d41c7b9e2a10"
down_revision: str | None = "b93f27c05ea8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "connectors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="burp"),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("token_prefix", sa.String(length=32), nullable=False),
        sa.Column(
            "import_mode",
            sa.String(length=16),
            nullable=False,
            server_default="in_scope",
        ),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "sync_trigger",
            sa.String(length=16),
            nullable=False,
            server_default="manual",
        ),
        sa.Column("quiet_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("queue_threshold", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("ingest_tools", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "capture_bodies", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "capture_sessions", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "include_static", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "scan_safe_methods_only",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column("context_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("paused", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requests_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "dropped_out_of_scope", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("candidates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scans_launched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_client", sa.String(length=120), nullable=True),
        sa.Column("last_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_connectors_project_id", "connectors", ["project_id"])
    op.create_index("ix_connectors_kind", "connectors", ["kind"])
    op.create_index("ix_connectors_token_hash", "connectors", ["token_hash"])
    op.create_index("ix_connectors_last_seen_at", "connectors", ["last_seen_at"])

    op.create_table(
        "connector_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "connector_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("connectors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signature", sa.String(length=64), nullable=False),
        sa.Column("url", sa.String(length=2000), nullable=False),
        sa.Column("scheme", sa.String(length=8), nullable=False),
        sa.Column("host", sa.String(length=500), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False, server_default="443"),
        sa.Column("path", sa.String(length=1500), nullable=False),
        sa.Column("dir_path", sa.String(length=1500), nullable=False),
        sa.Column("filename", sa.String(length=300), nullable=True),
        sa.Column("extension", sa.String(length=16), nullable=True),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("methods", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("params", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("param_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("endpoint_class", sa.String(length=24), nullable=True),
        sa.Column("interests", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("notices", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("content_length", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column(
            "authenticated", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "source_tool", sa.String(length=16), nullable=False, server_default="proxy"
        ),
        sa.Column("request_sample", sa.Text(), nullable=True),
        sa.Column("known", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="new"),
        sa.Column("hits", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "connector_id", "signature", name="uq_connector_candidate_signature"
        ),
    )
    for column in (
        "connector_id",
        "project_id",
        "target_id",
        "signature",
        "host",
        "param_count",
        "endpoint_class",
        "status_code",
        "authenticated",
        "known",
        "state",
        "first_seen_at",
        "last_seen_at",
    ):
        op.create_index(
            f"ix_connector_candidates_{column}", "connector_candidates", [column]
        )

    op.create_table(
        "connector_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "connector_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("connectors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client", sa.String(length=120), nullable=True),
        sa.Column("hosts", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("novel", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_connector_sessions_connector_id", "connector_sessions", ["connector_id"]
    )
    op.create_index(
        "ix_connector_sessions_last_event_at", "connector_sessions", ["last_event_at"]
    )


def downgrade() -> None:
    op.drop_table("connector_sessions")
    op.drop_table("connector_candidates")
    op.drop_table("connectors")

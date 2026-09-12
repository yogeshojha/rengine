"""program watches

Revision ID: 7c2e9a41b5d8
Revises: d7b3f09a4e15
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7c2e9a41b5d8"
down_revision: str | None = "d7b3f09a4e15"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'WATCH'")

    op.add_column(
        "scan_schedules", sa.Column("intensity", sa.String(length=16), nullable=True)
    )

    op.create_table(
        "program_watches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("context_id", sa.Uuid(), nullable=True),
        sa.Column("schedule_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("engine_id", sa.Uuid(), nullable=True),
        sa.Column("cadence", sa.String(length=16), nullable=False),
        sa.Column("intensity", sa.String(length=16), nullable=True),
        sa.Column("rate_limit", sa.Integer(), nullable=True),
        sa.Column("probe_on_resolve", sa.Boolean(), nullable=False),
        sa.Column("probe_engine_id", sa.Uuid(), nullable=True),
        sa.Column("follow_scope", sa.Boolean(), nullable=False),
        sa.Column("alert_unresolved", sa.Boolean(), nullable=False),
        sa.Column("alert_query", sa.String(length=2000), nullable=False),
        sa.Column("channel_ids", sa.JSON(), nullable=False),
        sa.Column("notify_in_app", sa.Boolean(), nullable=False),
        sa.Column("watch_items", sa.JSON(), nullable=False),
        sa.Column("unenforceable", sa.JSON(), nullable=False),
        sa.Column("hosts_seen", sa.Integer(), nullable=False),
        sa.Column("hosts_alerted", sa.Integer(), nullable=False),
        sa.Column("last_certificate_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_alert_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(
            ["program_id"], ["bounty_programs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "program_id", name="uq_program_watch"),
    )
    op.create_index("ix_program_watches_project_id", "program_watches", ["project_id"])
    op.create_index("ix_program_watches_program_id", "program_watches", ["program_id"])
    op.create_index("ix_program_watches_status", "program_watches", ["status"])

    op.create_table(
        "watch_hosts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("watch_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("matched_item", sa.String(length=500), nullable=True),
        sa.Column("cert_sha256", sa.String(length=64), nullable=True),
        sa.Column("issuer", sa.String(length=500), nullable=True),
        sa.Column("not_before", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sightings", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_ips", sa.JSON(), nullable=False),
        sa.Column("cname", sa.String(length=500), nullable=True),
        sa.Column("is_wildcard", sa.Boolean(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scan_id", sa.Uuid(), nullable=True),
        sa.Column("probed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=1000), nullable=True),
        sa.Column("tech", sa.JSON(), nullable=False),
        sa.Column("screenshot_path", sa.String(length=500), nullable=True),
        sa.Column("fingerprint", sa.String(length=64), nullable=True),
        sa.Column("alerted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("alerts", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["watch_id"], ["program_watches.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("watch_id", "name", name="uq_watch_host"),
    )
    op.create_index("ix_watch_hosts_watch_id", "watch_hosts", ["watch_id"])
    op.create_index("ix_watch_hosts_project_id", "watch_hosts", ["project_id"])
    op.create_index("ix_watch_hosts_target_id", "watch_hosts", ["target_id"])
    op.create_index("ix_watch_hosts_name", "watch_hosts", ["name"])
    op.create_index("ix_watch_hosts_state", "watch_hosts", ["state"])
    op.create_index("ix_watch_hosts_first_seen_at", "watch_hosts", ["first_seen_at"])
    op.create_index("ix_watch_hosts_next_check_at", "watch_hosts", ["next_check_at"])
    op.create_index("ix_watch_hosts_scan_id", "watch_hosts", ["scan_id"])
    op.create_index(
        "ix_watch_hosts_watch_first_seen", "watch_hosts", ["watch_id", "first_seen_at"]
    )

    op.create_table(
        "watch_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("watch_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=True),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["watch_id"], ["program_watches.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_watch_events_watch_id", "watch_events", ["watch_id"])
    op.create_index("ix_watch_events_project_id", "watch_events", ["project_id"])
    op.create_index("ix_watch_events_kind", "watch_events", ["kind"])
    op.create_index("ix_watch_events_created_at", "watch_events", ["created_at"])
    op.create_index(
        "ix_watch_events_watch_created", "watch_events", ["watch_id", "created_at"]
    )

    op.create_table(
        "user_marks",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("marked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "key"),
    )


def downgrade() -> None:
    op.drop_table("user_marks")
    op.drop_index("ix_watch_events_watch_created", table_name="watch_events")
    op.drop_index("ix_watch_events_created_at", table_name="watch_events")
    op.drop_index("ix_watch_events_kind", table_name="watch_events")
    op.drop_index("ix_watch_events_project_id", table_name="watch_events")
    op.drop_index("ix_watch_events_watch_id", table_name="watch_events")
    op.drop_table("watch_events")
    for name in (
        "ix_watch_hosts_watch_first_seen",
        "ix_watch_hosts_scan_id",
        "ix_watch_hosts_next_check_at",
        "ix_watch_hosts_first_seen_at",
        "ix_watch_hosts_state",
        "ix_watch_hosts_name",
        "ix_watch_hosts_target_id",
        "ix_watch_hosts_project_id",
        "ix_watch_hosts_watch_id",
    ):
        op.drop_index(name, table_name="watch_hosts")
    op.drop_table("watch_hosts")
    op.drop_index("ix_program_watches_status", table_name="program_watches")
    op.drop_index("ix_program_watches_program_id", table_name="program_watches")
    op.drop_index("ix_program_watches_project_id", table_name="program_watches")
    op.drop_table("program_watches")
    op.drop_column("scan_schedules", "intensity")

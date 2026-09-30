"""issue trackers, routes, filed issues and their comment outbox

Revision ID: d4a17e9b3c58
Revises: c93a5f8e2d16
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4a17e9b3c58"
down_revision: str | None = "c93a5f8e2d16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.execute("ALTER TYPE activityevent ADD VALUE IF NOT EXISTS 'ISSUE_FILED'")
    op.execute("ALTER TYPE activityevent ADD VALUE IF NOT EXISTS 'ISSUE_FAILED'")

    op.create_table(
        "issue_trackers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("config_encrypted", sa.String(), nullable=False),
        sa.Column("destination", sa.String(length=200), nullable=True),
        sa.Column("issue_type", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", _TZ, nullable=False),
        sa.Column("updated_at", _TZ, nullable=False),
        sa.Column("last_test_at", _TZ, nullable=True),
        sa.Column("last_test_ok", sa.Boolean(), nullable=True),
        sa.Column("last_test_message", sa.String(length=500), nullable=True),
    )

    op.create_table(
        "issue_tracker_routes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("tracker_id", sa.Uuid(), nullable=False),
        sa.Column("destination", sa.String(length=200), nullable=False),
        sa.Column("issue_type", sa.String(length=100), nullable=True),
        sa.Column("created_at", _TZ, nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["tracker_id"], ["issue_trackers.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_issue_tracker_routes_project_id", "issue_tracker_routes", ["project_id"]
    )
    op.create_index(
        "ix_issue_tracker_routes_tracker_id", "issue_tracker_routes", ["tracker_id"]
    )
    op.create_index(
        "uq_issue_route_project",
        "issue_tracker_routes",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("target_id IS NULL"),
    )
    op.create_index(
        "uq_issue_route_target",
        "issue_tracker_routes",
        ["project_id", "target_id"],
        unique=True,
        postgresql_where=sa.text("target_id IS NOT NULL"),
    )

    op.create_table(
        "tracked_issues",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tracker_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.String(length=200), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("grouped", sa.Boolean(), nullable=False),
        sa.Column("destination", sa.String(length=200), nullable=False),
        sa.Column("issue_type", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("external_key", sa.String(length=250), nullable=True),
        sa.Column("external_id", sa.String(length=250), nullable=True),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("remote_status", sa.String(length=100), nullable=True),
        sa.Column("remote_category", sa.String(length=16), nullable=True),
        sa.Column("done_noted", sa.Boolean(), nullable=False),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", _TZ, nullable=False),
        sa.Column("updated_at", _TZ, nullable=False),
        sa.Column("filed_at", _TZ, nullable=True),
        sa.Column("status_read_at", _TZ, nullable=True),
        sa.ForeignKeyConstraint(
            ["tracker_id"], ["issue_trackers.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
    )
    for column in ("tracker_id", "project_id", "target_id", "state"):
        op.create_index(f"ix_tracked_issues_{column}", "tracked_issues", [column])

    op.create_table(
        "tracked_issue_findings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("issue_id", sa.Uuid(), nullable=False),
        sa.Column("tracker_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("matched_at", sa.String(length=2000), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("present", sa.Boolean(), nullable=False),
        sa.Column("announced", sa.Boolean(), nullable=False),
        sa.Column("added_at", _TZ, nullable=False),
        sa.ForeignKeyConstraint(
            ["issue_id"], ["tracked_issues.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["tracker_id"], ["issue_trackers.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "tracker_id", "target_id", "fingerprint", name="uq_tracked_finding"
        ),
    )
    op.create_index(
        "ix_tracked_issue_findings_issue_id", "tracked_issue_findings", ["issue_id"]
    )
    op.create_index(
        "ix_tracked_finding_target_fp",
        "tracked_issue_findings",
        ["target_id", "fingerprint"],
    )

    op.create_table(
        "tracked_issue_comments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("issue_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("created_at", _TZ, nullable=False),
        sa.Column("sent_at", _TZ, nullable=True),
        sa.ForeignKeyConstraint(
            ["issue_id"], ["tracked_issues.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_tracked_issue_comments_issue_id", "tracked_issue_comments", ["issue_id"]
    )
    op.create_index(
        "ix_tracked_issue_comments_state", "tracked_issue_comments", ["state"]
    )


def downgrade() -> None:
    op.drop_table("tracked_issue_comments")
    op.drop_table("tracked_issue_findings")
    op.drop_table("tracked_issues")
    op.drop_table("issue_tracker_routes")
    op.drop_table("issue_trackers")

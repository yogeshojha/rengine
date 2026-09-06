"""reports: templates, generated documents, themes and the AI narrative cache

Revision ID: f7c31a9d24b8
Revises: e2b5d9f1a047
Create Date: 2026-09-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f7c31a9d24b8"
down_revision: str | None = "e2b5d9f1a047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("subtitle", sa.String(length=200), nullable=False),
        sa.Column("preset", sa.String(length=40), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("sections", sa.JSON(), nullable=False),
        sa.Column("theme", sa.String(length=64), nullable=False),
        sa.Column("style", sa.JSON(), nullable=False),
        sa.Column("branding", sa.JSON(), nullable=False),
        sa.Column("narrative", sa.JSON(), nullable=False),
        sa.Column("formats", sa.JSON(), nullable=False),
        sa.Column("is_builtin", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_templates_id", "report_templates", ["id"])
    op.create_index("ix_report_templates_slug", "report_templates", ["slug"])
    op.create_index(
        "ix_report_templates_project_id", "report_templates", ["project_id"]
    )
    op.create_index("ix_report_templates_scope", "report_templates", ["scope"])
    op.create_index(
        "ix_report_templates_is_builtin", "report_templates", ["is_builtin"]
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("template_name", sa.String(length=200), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=True),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("spec", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("step", sa.String(length=120), nullable=False),
        sa.Column("error", sa.String(length=2000), nullable=True),
        sa.Column("task_id", sa.String(length=120), nullable=True),
        sa.Column("files", sa.JSON(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("stats", sa.JSON(), nullable=False),
        sa.Column("ai_used", sa.Boolean(), nullable=False),
        sa.Column("ai_provider", sa.String(length=32), nullable=True),
        sa.Column("ai_model", sa.String(length=80), nullable=True),
        sa.Column("ai_calls", sa.Integer(), nullable=False),
        sa.Column("ai_input_tokens", sa.Integer(), nullable=False),
        sa.Column("ai_output_tokens", sa.Integer(), nullable=False),
        sa.Column("ai_cached_calls", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_id", "reports", ["id"])
    op.create_index("ix_reports_project_id", "reports", ["project_id"])
    op.create_index("ix_reports_template_id", "reports", ["template_id"])
    op.create_index("ix_reports_scan_id", "reports", ["scan_id"])
    op.create_index("ix_reports_target_id", "reports", ["target_id"])
    op.create_index("ix_reports_status", "reports", ["status"])
    op.create_index("ix_reports_scope", "reports", ["scope"])
    op.create_index("ix_reports_created_at", "reports", ["created_at"])

    op.create_table(
        "report_themes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=400), nullable=False),
        sa.Column("author", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("tokens", sa.JSON(), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_report_theme_slug"),
    )
    op.create_index("ix_report_themes_id", "report_themes", ["id"])
    op.create_index("ix_report_themes_slug", "report_themes", ["slug"])
    op.create_index("ix_report_themes_origin", "report_themes", ["origin"])

    op.create_table(
        "ai_narratives",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task", sa.String(length=40), nullable=False),
        sa.Column("cache_key", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=300), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task", "cache_key", name="uq_ai_narrative_task_key"),
    )
    op.create_index("ix_ai_narratives_id", "ai_narratives", ["id"])
    op.create_index("ix_ai_narratives_task", "ai_narratives", ["task"])
    op.create_index("ix_ai_narratives_cache_key", "ai_narratives", ["cache_key"])
    op.create_index("ix_ai_narratives_created_at", "ai_narratives", ["created_at"])

    op.create_table(
        "report_fonts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("role", sa.String(length=8), nullable=False),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("note", sa.String(length=300), nullable=False),
        sa.Column("faces", sa.JSON(), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_report_font_slug"),
    )
    op.create_index("ix_report_fonts_id", "report_fonts", ["id"])
    op.create_index("ix_report_fonts_slug", "report_fonts", ["slug"])
    op.create_index("ix_report_fonts_role", "report_fonts", ["role"])
    op.create_index("ix_report_fonts_origin", "report_fonts", ["origin"])

    op.add_column(
        "instance_settings",
        sa.Column(
            "report_defaults",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )


def downgrade() -> None:
    op.drop_column("instance_settings", "report_defaults")
    op.drop_table("report_fonts")
    op.drop_table("ai_narratives")
    op.drop_table("report_themes")
    op.drop_table("reports")
    op.drop_table("report_templates")

"""initial schema

Revision ID: 3f8b2d6c1a94
Revises:
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from shared.definitions.surface import SurfaceDimension

revision: str = "3f8b2d6c1a94"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUMS: dict[str, tuple[str, ...]] = {
    "activityevent": (
        "TARGET_CREATED",
        "TARGET_UPDATED",
        "TARGET_BULK_IMPORTED",
        "TARGET_ENRICHMENT_STARTED",
        "TARGET_ENRICHMENT_WHOIS_COMPLETED",
        "TARGET_ENRICHMENT_WHOIS_FAILED",
        "TARGET_ENRICHMENT_DNS_COMPLETED",
        "TARGET_ENRICHMENT_DNS_FAILED",
        "TARGET_ENRICHMENT_BGP_COMPLETED",
        "TARGET_ENRICHMENT_BGP_FAILED",
        "PROJECT_CREATED",
        "PROJECT_UPDATED",
        "SYSTEM_USER_LOGIN",
        "SYSTEM_USER_LOGOUT",
        "SYSTEM_USER_CREATED",
        "SYSTEM_CONFIG_UPDATED",
        "SCAN_STARTED",
        "SCAN_PROGRESS",
        "SCAN_COMPLETED",
        "SCAN_FAILED",
        "SCAN_CANCELLED",
        "SCAN_STAGE_COMPLETED",
        "SCAN_STAGE_FAILED",
        "SCAN_PAUSED",
        "SCAN_RESUMED",
        "ISSUE_FILED",
        "ISSUE_FAILED",
    ),
    "activitylevel": ("INFO", "SUCCESS", "WARNING", "ERROR"),
    "apiprovider": (
        "VIEWDNS",
        "CHAOS",
        "NETLAS",
        "SECURITYTRAILS",
        "HACKERONE",
        "VULNX",
        "INTERACTSH",
        "INTIGRITI",
        "GITHUB",
        "TELEGRAM",
    ),
    "dnsrecordtype": (
        "A",
        "AAAA",
        "CNAME",
        "NS",
        "MX",
        "TXT",
        "SOA",
        "SRV",
        "PTR",
        "CAA",
        "AXFR",
        "CDN",
    ),
    "notificationseverity": ("SUCCESS", "INFO", "WARNING", "ERROR"),
    "notificationtype": (
        "SCAN",
        "SYSTEM",
        "SECURITY",
        "VULNERABILITY",
        "TARGET",
        "RESOURCE",
        "INTEGRATION",
        "WATCH",
        "NEW_CHECKS",
        "TRIPWIRE",
    ),
    "targettype": ("DOMAIN", "IP", "IP_RANGE", "ASN", "URL"),
    "taskstatus": (
        "PENDING",
        "QUERYING",
        "SUCCESS",
        "FAILED",
        "SKIPPED",
        "NOT_APPLICABLE",
    ),
    "whoislookuptype": ("DOMAIN", "IP", "ASN"),
}

RESULT_STORAGE = (
    "autovacuum_analyze_scale_factor = 0.02, autovacuum_vacuum_scale_factor = 0.05"
)
RESULT_TABLES = (
    "endpoints",
    "http_assets",
    "interest_signals",
    "ip_addresses",
    "ports",
    "software_cves",
    "subdomains",
    "vulnerabilities",
)

REVISION_TABLES = {
    "subdomains": SurfaceDimension.WEB_ASSETS.value,
    "endpoints": SurfaceDimension.ENDPOINTS.value,
    "ports": SurfaceDimension.SERVICES.value,
    "ip_addresses": SurfaceDimension.IPS.value,
    "vulnerabilities": SurfaceDimension.VULNERABILITIES.value,
    "software_cves": SurfaceDimension.SOFTWARE.value,
    "secrets": SurfaceDimension.SECRETS.value,
}

BUMP = """
CREATE FUNCTION scan_revisions_bump() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
    EXECUTE format($sql$
        WITH changed AS (
            SELECT target_id, scan_id, min(discovered_at) AS since
              FROM changed_rows
             GROUP BY target_id, scan_id
        ), floors AS (
            SELECT target_id, min(since) AS since FROM changed GROUP BY target_id
        ), later AS (
            SELECT s.id AS scan_id
              FROM scans s
              JOIN floors f ON f.target_id = s.target_id
             WHERE EXISTS (
                 SELECT 1 FROM %1$I t
                  WHERE t.scan_id = s.id AND t.discovered_at > f.since
             )
        ), affected AS (
            SELECT scan_id, 1 AS own FROM changed
            UNION ALL
            SELECT scan_id, 0 FROM later
        )
        INSERT INTO scan_revisions AS r (scan_id, dimension, rows_rev, history_rev)
        SELECT a.scan_id, %2$L, max(a.own), 1
          FROM affected a
          JOIN scans s ON s.id = a.scan_id
         GROUP BY a.scan_id
         ORDER BY a.scan_id
        ON CONFLICT (scan_id, dimension) DO UPDATE
           SET rows_rev = r.rows_rev + excluded.rows_rev,
               history_rev = r.history_rev + 1
    $sql$, TG_TABLE_NAME, TG_ARGV[0]);
    RETURN NULL;
END
$fn$
"""


def _enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(*ENUMS[name], name=name, create_type=False)


def upgrade() -> None:  # noqa: PLR0915
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
    for name, labels in ENUMS.items():
        postgresql.ENUM(*labels, name=name).create(op.get_bind())

    op.create_table(
        "ai_calls",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("task", sa.VARCHAR(length=40), nullable=False),
        sa.Column("feature", sa.VARCHAR(length=40), nullable=False),
        sa.Column("provider", sa.VARCHAR(length=32), nullable=False),
        sa.Column("model", sa.VARCHAR(length=80), nullable=False),
        sa.Column("ok", sa.BOOLEAN(), nullable=False),
        sa.Column("cached", sa.BOOLEAN(), nullable=False),
        sa.Column("rounds", sa.INTEGER(), nullable=False),
        sa.Column("input_tokens", sa.INTEGER(), nullable=False),
        sa.Column("output_tokens", sa.INTEGER(), nullable=False),
        sa.Column("cost_usd", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("latency_ms", sa.INTEGER(), nullable=False),
        sa.Column("error", sa.VARCHAR(length=300), nullable=True),
        sa.Column("source_kind", sa.VARCHAR(length=20), nullable=True),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column(
            "cache_read_tokens",
            sa.INTEGER(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "cache_write_tokens",
            sa.INTEGER(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("cost_source", sa.VARCHAR(length=16), nullable=True),
        sa.Column("input_per_mtok", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("output_per_mtok", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.PrimaryKeyConstraint("id", name="ai_calls_pkey"),
    )
    op.create_index("ix_ai_calls_at", "ai_calls", ["at"])
    op.create_index("ix_ai_calls_feature_at", "ai_calls", ["feature", "at"])
    op.create_table(
        "ai_connections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=60), nullable=False),
        sa.Column("provider", sa.VARCHAR(length=32), nullable=False),
        sa.Column("api_key_encrypted", sa.VARCHAR(), nullable=True),
        sa.Column("base_url", sa.VARCHAR(length=300), nullable=True),
        sa.Column("model", sa.VARCHAR(length=80), nullable=False),
        sa.Column("input_per_mtok", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("output_per_mtok", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("workspace_id", sa.VARCHAR(length=80), nullable=True),
        sa.Column("last_test_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_test_ok", sa.BOOLEAN(), nullable=True),
        sa.Column("last_test_message", sa.VARCHAR(length=500), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "cache_read_per_mtok", sa.DOUBLE_PRECISION(precision=53), nullable=True
        ),
        sa.Column(
            "cache_write_per_mtok", sa.DOUBLE_PRECISION(precision=53), nullable=True
        ),
        sa.Column(
            "custom_price",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="ai_connections_pkey"),
        sa.UniqueConstraint(
            "name", name="uq_ai_connection_name", postgresql_nulls_not_distinct=False
        ),
        postgresql_ignore_search_path=False,
    )
    op.create_table(
        "ai_narratives",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task", sa.VARCHAR(length=40), nullable=False),
        sa.Column("cache_key", sa.VARCHAR(length=64), nullable=False),
        sa.Column("subject", sa.VARCHAR(length=300), nullable=False),
        sa.Column("provider", sa.VARCHAR(length=32), nullable=False),
        sa.Column("model", sa.VARCHAR(length=80), nullable=False),
        sa.Column("content", sa.TEXT(), nullable=False),
        sa.Column("input_tokens", sa.INTEGER(), nullable=False),
        sa.Column("output_tokens", sa.INTEGER(), nullable=False),
        sa.Column("hits", sa.INTEGER(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_used_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="ai_narratives_pkey"),
        sa.UniqueConstraint(
            "task",
            "cache_key",
            name="uq_ai_narrative_task_key",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_ai_narratives_cache_key", "ai_narratives", ["cache_key"])
    op.create_index("ix_ai_narratives_created_at", "ai_narratives", ["created_at"])
    op.create_index("ix_ai_narratives_task", "ai_narratives", ["task"])
    op.create_table(
        "ai_prices",
        sa.Column("model_id", sa.VARCHAR(length=120), nullable=False),
        sa.Column("input_per_mtok", sa.DOUBLE_PRECISION(precision=53), nullable=False),
        sa.Column("output_per_mtok", sa.DOUBLE_PRECISION(precision=53), nullable=False),
        sa.Column(
            "cache_read_per_mtok", sa.DOUBLE_PRECISION(precision=53), nullable=True
        ),
        sa.Column(
            "cache_write_per_mtok", sa.DOUBLE_PRECISION(precision=53), nullable=True
        ),
        sa.PrimaryKeyConstraint("model_id", name="ai_prices_pkey"),
    )
    op.create_table(
        "api_keys",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("provider", _enum("apiprovider"), nullable=False),
        sa.Column("key_value", sa.VARCHAR(length=1000), nullable=False),
        sa.Column("is_enabled", sa.BOOLEAN(), nullable=False),
        sa.Column("usage_counter", sa.INTEGER(), nullable=False),
        sa.Column("last_used_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("key_meta", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("last_test_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_test_ok", sa.BOOLEAN(), nullable=True),
        sa.Column("last_test_message", sa.VARCHAR(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id", name="api_keys_pkey"),
        sa.UniqueConstraint(
            "provider", name="uq_api_key_provider", postgresql_nulls_not_distinct=False
        ),
    )
    op.create_index("ix_api_keys_provider", "api_keys", ["provider"])
    op.create_table(
        "bounty_accounts",
        sa.Column("platform", sa.VARCHAR(length=32), nullable=False),
        sa.Column("username", sa.VARCHAR(length=200), nullable=True),
        sa.Column("reputation", sa.INTEGER(), nullable=True),
        sa.Column("signal", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("impact", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("synced_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error", sa.VARCHAR(length=500), nullable=True),
        sa.PrimaryKeyConstraint("platform", name="bounty_accounts_pkey"),
    )
    op.create_table(
        "bounty_awards",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("platform", sa.VARCHAR(length=32), nullable=False),
        sa.Column("external_id", sa.VARCHAR(length=100), nullable=False),
        sa.Column("report_external_id", sa.VARCHAR(length=100), nullable=True),
        sa.Column("program_handle", sa.VARCHAR(length=200), nullable=True),
        sa.Column("program_name", sa.VARCHAR(length=300), nullable=True),
        sa.Column("amount", sa.NUMERIC(precision=14, scale=2), nullable=False),
        sa.Column(
            "bonus",
            sa.NUMERIC(precision=14, scale=2),
            server_default=sa.text("'0'::numeric"),
            nullable=False,
        ),
        sa.Column("currency", sa.VARCHAR(length=8), nullable=False),
        sa.Column("awarded_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("synced_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="bounty_awards_pkey"),
        sa.UniqueConstraint(
            "platform",
            "external_id",
            name="uq_bounty_award_external",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_bounty_awards_awarded_at", "bounty_awards", ["awarded_at"])
    op.create_index("ix_bounty_awards_platform", "bounty_awards", ["platform"])
    op.create_index(
        "ix_bounty_awards_program_handle", "bounty_awards", ["program_handle"]
    )
    op.create_index(
        "ix_bounty_awards_report_external_id", "bounty_awards", ["report_external_id"]
    )
    op.create_table(
        "bounty_programs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("platform", sa.VARCHAR(length=32), nullable=False),
        sa.Column("handle", sa.VARCHAR(length=200), nullable=False),
        sa.Column("name", sa.VARCHAR(length=300), nullable=False),
        sa.Column("url", sa.VARCHAR(length=500), nullable=True),
        sa.Column("profile_picture", sa.TEXT(), nullable=True),
        sa.Column("program_state", sa.VARCHAR(length=16), nullable=False),
        sa.Column("submission_state", sa.VARCHAR(length=16), nullable=False),
        sa.Column("offers_bounties", sa.BOOLEAN(), nullable=False),
        sa.Column("open_scope", sa.BOOLEAN(), nullable=True),
        sa.Column("gold_standard_safe_harbor", sa.BOOLEAN(), nullable=True),
        sa.Column("currency", sa.VARCHAR(length=16), nullable=True),
        sa.Column(
            "started_accepting_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("bookmarked", sa.BOOLEAN(), nullable=False),
        sa.Column("reports_for_user", sa.INTEGER(), nullable=True),
        sa.Column(
            "earnings_for_user", sa.DOUBLE_PRECISION(precision=53), nullable=True
        ),
        sa.Column(
            "scopes_synced_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("synced_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("raw_state", sa.VARCHAR(length=32), nullable=True),
        sa.Column(
            "joined", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("joined_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "source",
            sa.VARCHAR(length=16),
            server_default=sa.text("'api'::character varying"),
            nullable=False,
        ),
        sa.Column("min_payout", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("max_payout", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("payout_currency", sa.VARCHAR(length=16), nullable=True),
        sa.Column("safe_harbor", sa.VARCHAR(length=32), nullable=True),
        sa.Column("requires_2fa", sa.BOOLEAN(), nullable=True),
        sa.Column("external_id", sa.VARCHAR(length=100), nullable=True),
        sa.Column("scope_access", sa.VARCHAR(length=16), nullable=True),
        sa.Column(
            "sources",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="bounty_programs_pkey"),
        sa.UniqueConstraint(
            "platform",
            "handle",
            name="uq_bounty_program_handle",
            postgresql_nulls_not_distinct=False,
        ),
        postgresql_ignore_search_path=False,
    )
    op.create_index("ix_bounty_programs_bookmarked", "bounty_programs", ["bookmarked"])
    op.create_index(
        "ix_bounty_programs_external_id", "bounty_programs", ["external_id"]
    )
    op.create_index("ix_bounty_programs_handle", "bounty_programs", ["handle"])
    op.create_index("ix_bounty_programs_joined", "bounty_programs", ["joined"])
    op.create_index(
        "ix_bounty_programs_offers_bounties", "bounty_programs", ["offers_bounties"]
    )
    op.create_index("ix_bounty_programs_platform", "bounty_programs", ["platform"])
    op.create_index(
        "ix_bounty_programs_program_state", "bounty_programs", ["program_state"]
    )
    op.create_index("ix_bounty_programs_source", "bounty_programs", ["source"])
    op.create_index(
        "ix_bounty_programs_sources",
        "bounty_programs",
        ["sources"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_bounty_programs_started_accepting_at",
        "bounty_programs",
        ["started_accepting_at"],
    )
    op.create_index(
        "ix_bounty_programs_submission_state", "bounty_programs", ["submission_state"]
    )
    op.create_index("ix_bounty_programs_synced_at", "bounty_programs", ["synced_at"])
    op.create_table(
        "bounty_reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("platform", sa.VARCHAR(length=32), nullable=False),
        sa.Column("external_id", sa.VARCHAR(length=100), nullable=False),
        sa.Column("program_handle", sa.VARCHAR(length=200), nullable=True),
        sa.Column("title", sa.VARCHAR(length=500), nullable=False),
        sa.Column("state", sa.VARCHAR(length=32), nullable=False),
        sa.Column("severity", sa.VARCHAR(length=16), nullable=True),
        sa.Column("severity_score", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("weakness", sa.VARCHAR(length=200), nullable=True),
        sa.Column("asset_type", sa.VARCHAR(length=48), nullable=True),
        sa.Column("asset_identifier", sa.VARCHAR(length=1000), nullable=True),
        sa.Column("submitted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("triaged_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("closed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "bounty_awarded_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("disclosed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "last_program_activity_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("synced_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="bounty_reports_pkey"),
        sa.UniqueConstraint(
            "platform",
            "external_id",
            name="uq_bounty_report_external",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_bounty_reports_platform", "bounty_reports", ["platform"])
    op.create_index(
        "ix_bounty_reports_program_handle", "bounty_reports", ["program_handle"]
    )
    op.create_index("ix_bounty_reports_severity", "bounty_reports", ["severity"])
    op.create_index("ix_bounty_reports_state", "bounty_reports", ["state"])
    op.create_index(
        "ix_bounty_reports_submitted_at", "bounty_reports", ["submitted_at"]
    )
    op.create_table(
        "channel_configs",
        sa.Column("channel", sa.VARCHAR(length=16), nullable=False),
        sa.Column(
            "enabled", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "settings",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("channel", name="channel_configs_pkey"),
    )
    op.create_table(
        "cve_intel",
        sa.Column("cve", sa.VARCHAR(length=30), nullable=False),
        sa.Column("provider", sa.VARCHAR(length=32), nullable=False),
        sa.Column("severity", sa.VARCHAR(length=16), nullable=True),
        sa.Column("cvss_score", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("remediation", sa.TEXT(), nullable=True),
        sa.Column("weaknesses", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("pocs", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("poc_count", sa.INTEGER(), nullable=False),
        sa.Column("poc_first_seen", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("template_available", sa.BOOLEAN(), nullable=True),
        sa.Column("is_remote", sa.BOOLEAN(), nullable=True),
        sa.Column("needs_auth", sa.BOOLEAN(), nullable=True),
        sa.Column("patch_available", sa.BOOLEAN(), nullable=True),
        sa.Column("vendor_kev", sa.BOOLEAN(), nullable=False),
        sa.Column(
            "kev_sources", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("exposure_hosts", sa.BIGINT(), nullable=True),
        sa.Column(
            "exposure_products", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("hackerone_rank", sa.INTEGER(), nullable=True),
        sa.Column("hackerone_reports", sa.INTEGER(), nullable=True),
        sa.Column("published_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("fetched_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("cve", name="cve_intel_pkey"),
    )
    op.create_index("ix_cve_intel_fetched_at", "cve_intel", ["fetched_at"])
    op.create_table(
        "dns_lookups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("host", sa.VARCHAR(length=500), nullable=False),
        sa.Column("status_code", sa.VARCHAR(length=20), nullable=False),
        sa.Column("cdn", sa.BOOLEAN(), nullable=False),
        sa.Column("cdn_name", sa.VARCHAR(length=100), nullable=False),
        sa.Column("parsed_data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("queried_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="dns_lookups_pkey"),
        postgresql_ignore_search_path=False,
    )
    op.create_table(
        "epss_scores",
        sa.Column("cve", sa.VARCHAR(length=30), nullable=False),
        sa.Column("score", sa.DOUBLE_PRECISION(precision=53), nullable=False),
        sa.Column("percentile", sa.DOUBLE_PRECISION(precision=53), nullable=False),
        sa.PrimaryKeyConstraint("cve", name="epss_scores_pkey"),
    )
    op.create_table(
        "ip_asn_ranges",
        sa.Column("start_ip", postgresql.INET(), nullable=False),
        sa.Column("end_ip", postgresql.INET(), nullable=False),
        sa.Column("asn", sa.BIGINT(), nullable=False),
        sa.Column("as_name", sa.VARCHAR(length=255), nullable=True),
        sa.PrimaryKeyConstraint("start_ip", name="ip_asn_ranges_pkey"),
    )
    op.create_table(
        "ip_country_ranges",
        sa.Column("start_ip", postgresql.INET(), nullable=False),
        sa.Column("end_ip", postgresql.INET(), nullable=False),
        sa.Column("country", sa.VARCHAR(length=2), nullable=False),
        sa.PrimaryKeyConstraint("start_ip", name="ip_country_ranges_pkey"),
    )
    op.create_table(
        "issue_trackers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=120), nullable=False),
        sa.Column("kind", sa.VARCHAR(length=20), nullable=False),
        sa.Column("url", sa.VARCHAR(length=500), nullable=False),
        sa.Column("config_encrypted", sa.VARCHAR(), nullable=False),
        sa.Column("destination", sa.VARCHAR(length=200), nullable=True),
        sa.Column("issue_type", sa.VARCHAR(length=100), nullable=True),
        sa.Column("is_active", sa.BOOLEAN(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_test_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_test_ok", sa.BOOLEAN(), nullable=True),
        sa.Column("last_test_message", sa.VARCHAR(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id", name="issue_trackers_pkey"),
        postgresql_ignore_search_path=False,
    )
    op.create_table(
        "kev_entries",
        sa.Column("cve", sa.VARCHAR(length=30), nullable=False),
        sa.Column("vendor", sa.VARCHAR(length=200), nullable=True),
        sa.Column("product", sa.VARCHAR(length=200), nullable=True),
        sa.Column("name", sa.VARCHAR(length=500), nullable=True),
        sa.Column("short_description", sa.TEXT(), nullable=True),
        sa.Column("required_action", sa.TEXT(), nullable=True),
        sa.Column("notes", sa.TEXT(), nullable=True),
        sa.Column("cwes", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("known_ransomware", sa.BOOLEAN(), nullable=False),
        sa.Column("date_added", sa.DATE(), nullable=True),
        sa.Column("due_date", sa.DATE(), nullable=True),
        sa.PrimaryKeyConstraint("cve", name="kev_entries_pkey"),
    )
    op.create_index("ix_kev_entries_date_added", "kev_entries", ["date_added"])
    op.create_index(
        "ix_kev_entries_known_ransomware", "kev_entries", ["known_ransomware"]
    )
    op.create_table(
        "mcp_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=80), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column(
            "capabilities", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("token_hash", sa.VARCHAR(length=64), nullable=False),
        sa.Column("token_prefix", sa.VARCHAR(length=32), nullable=False),
        sa.Column("expires_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_used_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_client", sa.VARCHAR(length=120), nullable=True),
        sa.Column("calls", sa.INTEGER(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="mcp_tokens_pkey"),
    )
    op.create_index("ix_mcp_tokens_name", "mcp_tokens", ["name"])
    op.create_index("ix_mcp_tokens_project_id", "mcp_tokens", ["project_id"])
    op.create_index(
        "ix_mcp_tokens_token_hash", "mcp_tokens", ["token_hash"], unique=True
    )
    op.create_table(
        "notifications",
        sa.Column("type", _enum("notificationtype"), nullable=False),
        sa.Column("severity", _enum("notificationseverity"), nullable=False),
        sa.Column("title", sa.VARCHAR(length=200), nullable=False),
        sa.Column("message", sa.TEXT(), nullable=True),
        sa.Column(
            "id",
            sa.INTEGER(),
            server_default=sa.text("nextval('notifications_id_seq'::regclass)"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "notification_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("expires_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="notifications_pkey"),
    )
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])
    op.create_index("ix_notifications_expires_at", "notifications", ["expires_at"])
    op.create_index("ix_notifications_project_id", "notifications", ["project_id"])
    op.create_table(
        "nvd_cpe_matches",
        sa.Column(
            "id",
            sa.BIGINT(),
            server_default=sa.text("nextval('nvd_cpe_matches_id_seq'::regclass)"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("cve", sa.VARCHAR(length=30), nullable=False),
        sa.Column("vendor", sa.VARCHAR(length=200), nullable=False),
        sa.Column("product", sa.VARCHAR(length=200), nullable=False),
        sa.Column("version_kind", sa.VARCHAR(length=1), nullable=False),
        sa.Column("exact_key", sa.VARCHAR(length=160), nullable=True),
        sa.Column("start_key", sa.VARCHAR(length=160), nullable=True),
        sa.Column(
            "start_incl", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("end_key", sa.VARCHAR(length=160), nullable=True),
        sa.Column(
            "end_incl", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "conditional", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="nvd_cpe_matches_pkey"),
    )
    op.create_index("ix_nvd_cpe_matches_cve", "nvd_cpe_matches", ["cve"])
    op.create_index(
        "ix_nvd_cpe_matches_lookup",
        "nvd_cpe_matches",
        ["product", "version_kind", "vendor"],
    )
    op.create_table(
        "nvd_cves",
        sa.Column("cve", sa.VARCHAR(length=30), nullable=False),
        sa.Column("severity", sa.VARCHAR(length=16), nullable=True),
        sa.Column("cvss_score", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("cvss_vector", sa.VARCHAR(length=200), nullable=True),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("published_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "last_modified_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.PrimaryKeyConstraint("cve", name="nvd_cves_pkey"),
    )
    op.create_index("ix_nvd_cves_published_at", "nvd_cves", ["published_at"])
    op.create_index("ix_nvd_cves_severity", "nvd_cves", ["severity"])
    op.create_table(
        "report_fonts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.VARCHAR(length=64), nullable=False),
        sa.Column("name", sa.VARCHAR(length=80), nullable=False),
        sa.Column("role", sa.VARCHAR(length=8), nullable=False),
        sa.Column("origin", sa.VARCHAR(length=16), nullable=False),
        sa.Column("note", sa.VARCHAR(length=300), nullable=False),
        sa.Column("faces", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("bytes", sa.INTEGER(), nullable=False),
        sa.Column("uploaded_by", sa.UUID(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="report_fonts_pkey"),
        sa.UniqueConstraint(
            "slug", name="uq_report_font_slug", postgresql_nulls_not_distinct=False
        ),
    )
    op.create_index("ix_report_fonts_origin", "report_fonts", ["origin"])
    op.create_index("ix_report_fonts_role", "report_fonts", ["role"])
    op.create_index("ix_report_fonts_slug", "report_fonts", ["slug"])
    op.create_table(
        "report_templates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("slug", sa.VARCHAR(length=64), nullable=False),
        sa.Column("name", sa.VARCHAR(length=200), nullable=False),
        sa.Column("description", sa.VARCHAR(length=1000), nullable=False),
        sa.Column("title", sa.VARCHAR(length=200), nullable=False),
        sa.Column("subtitle", sa.VARCHAR(length=200), nullable=False),
        sa.Column("preset", sa.VARCHAR(length=40), nullable=False),
        sa.Column("tags", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("scope", sa.VARCHAR(length=16), nullable=False),
        sa.Column("sections", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("theme", sa.VARCHAR(length=64), nullable=False),
        sa.Column("style", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("branding", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("narrative", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("formats", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("is_builtin", sa.BOOLEAN(), nullable=False),
        sa.Column("is_default", sa.BOOLEAN(), nullable=False),
        sa.Column("used_count", sa.INTEGER(), nullable=False),
        sa.Column("last_used_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="report_templates_pkey"),
    )
    op.create_index(
        "ix_report_templates_is_builtin", "report_templates", ["is_builtin"]
    )
    op.create_index(
        "ix_report_templates_project_id", "report_templates", ["project_id"]
    )
    op.create_index("ix_report_templates_scope", "report_templates", ["scope"])
    op.create_index("ix_report_templates_slug", "report_templates", ["slug"])
    op.create_table(
        "report_themes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.VARCHAR(length=64), nullable=False),
        sa.Column("name", sa.VARCHAR(length=120), nullable=False),
        sa.Column("description", sa.VARCHAR(length=400), nullable=False),
        sa.Column("author", sa.VARCHAR(length=120), nullable=False),
        sa.Column("version", sa.VARCHAR(length=20), nullable=False),
        sa.Column("origin", sa.VARCHAR(length=16), nullable=False),
        sa.Column("tokens", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("source", sa.TEXT(), nullable=True),
        sa.Column("uploaded_by", sa.UUID(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="report_themes_pkey"),
        sa.UniqueConstraint(
            "slug", name="uq_report_theme_slug", postgresql_nulls_not_distinct=False
        ),
    )
    op.create_index("ix_report_themes_origin", "report_themes", ["origin"])
    op.create_index("ix_report_themes_slug", "report_themes", ["slug"])
    op.create_table(
        "ripestat_abuse_contacts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("resource", sa.VARCHAR(), nullable=False),
        sa.Column("abuse_email", sa.VARCHAR(), nullable=False),
        sa.Column("rir", sa.VARCHAR(), nullable=True),
        sa.Column("queried_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="ripestat_abuse_contacts_pkey"),
    )
    op.create_index("ix_ripestat_ac_resource", "ripestat_abuse_contacts", ["resource"])
    op.create_table(
        "ripestat_announced_prefixes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("asn", sa.BIGINT(), nullable=False),
        sa.Column("prefix", sa.VARCHAR(), nullable=False),
        sa.Column("ip_version", sa.INTEGER(), nullable=False),
        sa.Column("first_seen", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_seen", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("queried_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="ripestat_announced_prefixes_pkey"),
    )
    op.create_index("ix_ripestat_ap_asn", "ripestat_announced_prefixes", ["asn"])
    op.create_index("ix_ripestat_ap_prefix", "ripestat_announced_prefixes", ["prefix"])
    op.create_table(
        "ripestat_as_overviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("asn", sa.BIGINT(), nullable=False),
        sa.Column("holder", sa.VARCHAR(), nullable=False),
        sa.Column("rir", sa.VARCHAR(), nullable=True),
        sa.Column("announced", sa.BOOLEAN(), nullable=False),
        sa.Column("block_name", sa.VARCHAR(), nullable=True),
        sa.Column("block_resource", sa.VARCHAR(), nullable=True),
        sa.Column("queried_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="ripestat_as_overviews_pkey"),
        sa.UniqueConstraint(
            "asn",
            name="uq_ripestat_as_overview_asn",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_ripestat_as_overviews_asn", "ripestat_as_overviews", ["asn"])
    op.create_index("ix_ripestat_aso_holder", "ripestat_as_overviews", ["holder"])
    op.create_table(
        "ripestat_asn_neighbours",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("asn", sa.BIGINT(), nullable=False),
        sa.Column("neighbour_asn", sa.BIGINT(), nullable=False),
        sa.Column("relationship", sa.VARCHAR(), nullable=False),
        sa.Column("power", sa.INTEGER(), nullable=False),
        sa.Column("queried_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="ripestat_asn_neighbours_pkey"),
    )
    op.create_index("ix_ripestat_an_asn", "ripestat_asn_neighbours", ["asn"])
    op.create_index(
        "ix_ripestat_an_neighbour", "ripestat_asn_neighbours", ["neighbour_asn"]
    )
    op.create_table(
        "ripestat_network_info",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("ip", sa.VARCHAR(), nullable=False),
        sa.Column("prefix", sa.VARCHAR(), nullable=False),
        sa.Column("asn", sa.BIGINT(), nullable=False),
        sa.Column("queried_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="ripestat_network_info_pkey"),
    )
    op.create_index("ix_ripestat_ni_asn", "ripestat_network_info", ["asn"])
    op.create_index("ix_ripestat_ni_ip", "ripestat_network_info", ["ip"])
    op.create_index("ix_ripestat_ni_prefix", "ripestat_network_info", ["prefix"])
    op.create_table(
        "ripestat_prefix_overviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("prefix", sa.VARCHAR(), nullable=False),
        sa.Column("asn", sa.BIGINT(), nullable=False),
        sa.Column("holder", sa.VARCHAR(), nullable=False),
        sa.Column("is_announced", sa.BOOLEAN(), nullable=False),
        sa.Column("queried_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="ripestat_prefix_overviews_pkey"),
    )
    op.create_index("ix_ripestat_po_asn", "ripestat_prefix_overviews", ["asn"])
    op.create_index("ix_ripestat_po_prefix", "ripestat_prefix_overviews", ["prefix"])
    op.create_table(
        "ripestat_query_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("lookup_type", sa.VARCHAR(), nullable=False),
        sa.Column("query_value", sa.VARCHAR(), nullable=False),
        sa.Column("result_count", sa.INTEGER(), nullable=False),
        sa.Column("queried_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="ripestat_query_log_pkey"),
        sa.UniqueConstraint(
            "lookup_type",
            "query_value",
            name="uq_ripestat_query_log_lookup",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index(
        "ix_ripestat_query_log_lookup_type", "ripestat_query_log", ["lookup_type"]
    )
    op.create_index(
        "ix_ripestat_query_log_query_value", "ripestat_query_log", ["query_value"]
    )
    op.create_table(
        "ripestat_related_prefixes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("prefix", sa.VARCHAR(), nullable=False),
        sa.Column("related_prefix", sa.VARCHAR(), nullable=False),
        sa.Column("relationship", sa.VARCHAR(), nullable=False),
        sa.Column("origin_asn", sa.BIGINT(), nullable=True),
        sa.Column("queried_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="ripestat_related_prefixes_pkey"),
    )
    op.create_index("ix_ripestat_rp_prefix", "ripestat_related_prefixes", ["prefix"])
    op.create_index(
        "ix_ripestat_rp_related", "ripestat_related_prefixes", ["related_prefix"]
    )
    op.create_table(
        "threat_feeds",
        sa.Column("kind", sa.VARCHAR(length=32), nullable=False),
        sa.Column("status", sa.VARCHAR(length=16), nullable=False),
        sa.Column("rows", sa.INTEGER(), nullable=False),
        sa.Column("version", sa.VARCHAR(length=100), nullable=True),
        sa.Column("bytes", sa.BIGINT(), nullable=False),
        sa.Column("duration_ms", sa.INTEGER(), nullable=False),
        sa.Column("error", sa.VARCHAR(length=500), nullable=True),
        sa.Column("last_synced_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "last_attempt_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("kind", name="threat_feeds_pkey"),
    )
    op.create_table(
        "users",
        sa.Column("email", sa.VARCHAR(length=255), nullable=False),
        sa.Column("username", sa.VARCHAR(length=50), nullable=False),
        sa.Column("is_active", sa.BOOLEAN(), nullable=False),
        sa.Column("is_superuser", sa.BOOLEAN(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("hashed_password", sa.VARCHAR(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("totp_secret_encrypted", sa.VARCHAR(), nullable=True),
        sa.Column(
            "totp_enabled",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "totp_backup_codes", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.PrimaryKeyConstraint("id", name="users_pkey"),
        postgresql_ignore_search_path=False,
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table(
        "viewdns_cache",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("lookup_type", sa.VARCHAR(), nullable=False),
        sa.Column("query_value", sa.VARCHAR(), nullable=False),
        sa.Column("result_count", sa.INTEGER(), nullable=False),
        sa.Column(
            "response_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("queried_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="viewdns_cache_pkey"),
        sa.UniqueConstraint(
            "lookup_type",
            "query_value",
            name="uq_viewdns_cache_lookup",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_viewdns_cache_lookup_type", "viewdns_cache", ["lookup_type"])
    op.create_index("ix_viewdns_cache_query_value", "viewdns_cache", ["query_value"])
    op.create_table(
        "vuln_templates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "origin",
            sa.VARCHAR(length=16),
            server_default=sa.text("'official'::character varying"),
            nullable=False,
        ),
        sa.Column("template_id", sa.VARCHAR(length=200), nullable=False),
        sa.Column("path", sa.VARCHAR(length=500), nullable=False),
        sa.Column("name", sa.VARCHAR(length=500), nullable=False),
        sa.Column(
            "severity",
            sa.VARCHAR(length=16),
            server_default=sa.text("'unknown'::character varying"),
            nullable=False,
        ),
        sa.Column(
            "protocol",
            sa.VARCHAR(length=16),
            server_default=sa.text("'other'::character varying"),
            nullable=False,
        ),
        sa.Column(
            "directory",
            sa.VARCHAR(length=200),
            server_default=sa.text("''::character varying"),
            nullable=False,
        ),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("remediation", sa.TEXT(), nullable=True),
        sa.Column("tags", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("authors", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("references", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("cve_ids", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("cwe_ids", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("cvss_score", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column(
            "requests", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "digest",
            sa.VARCHAR(length=64),
            server_default=sa.text("''::character varying"),
            nullable=False,
        ),
        sa.Column("raw", sa.TEXT(), nullable=True),
        sa.Column(
            "enabled", sa.BOOLEAN(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("uploaded_by", sa.UUID(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("paths", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("simple", sa.BOOLEAN(), nullable=True),
        sa.Column("needs_oast", sa.BOOLEAN(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="vuln_templates_pkey"),
        sa.UniqueConstraint(
            "origin",
            "path",
            name="uq_vulntemplate_origin_path",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_vuln_templates_directory", "vuln_templates", ["directory"])
    op.create_index("ix_vuln_templates_enabled", "vuln_templates", ["enabled"])
    op.create_index(
        "ix_vuln_templates_name_trgm",
        "vuln_templates",
        ["name"],
        postgresql_ops={"name": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index("ix_vuln_templates_origin", "vuln_templates", ["origin"])
    op.create_index("ix_vuln_templates_protocol", "vuln_templates", ["protocol"])
    op.create_index("ix_vuln_templates_severity", "vuln_templates", ["severity"])
    op.create_index(
        "ix_vuln_templates_tags_gin",
        "vuln_templates",
        [sa.literal_column("(tags::jsonb)")],
        postgresql_using="gin",
    )
    op.create_index("ix_vuln_templates_template_id", "vuln_templates", ["template_id"])
    op.create_index(
        "ix_vuln_templates_template_trgm",
        "vuln_templates",
        ["template_id"],
        postgresql_ops={"template_id": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_table(
        "whois_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("query_value", sa.VARCHAR(length=500), nullable=False),
        sa.Column("lookup_type", _enum("whoislookuptype"), nullable=False),
        sa.Column("queried_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("handle", sa.VARCHAR(length=200), nullable=False),
        sa.Column("name", sa.VARCHAR(length=500), nullable=False),
        sa.Column("whois_server", sa.VARCHAR(length=200), nullable=False),
        sa.Column("object_class", sa.VARCHAR(length=100), nullable=False),
        sa.Column("rir", sa.VARCHAR(length=50), nullable=False),
        sa.Column("description", sa.TEXT(), nullable=False),
        sa.Column(
            "registration_date", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column(
            "last_changed_date", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column(
            "expiration_date", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("registrant_name", sa.VARCHAR(length=500), nullable=False),
        sa.Column("registrant_email", sa.VARCHAR(length=500), nullable=False),
        sa.Column("registrar_name", sa.VARCHAR(length=500), nullable=False),
        sa.Column("abuse_email", sa.VARCHAR(length=500), nullable=False),
        sa.Column(
            "nameservers", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "domain_status", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("dnssec", sa.BOOLEAN(), nullable=True),
        sa.Column("country", sa.VARCHAR(length=10), nullable=False),
        sa.Column("ip_version", sa.INTEGER(), nullable=True),
        sa.Column("assignment_type", sa.VARCHAR(length=100), nullable=False),
        sa.Column("network_cidr", sa.VARCHAR(length=100), nullable=False),
        sa.Column("asn_range_start", sa.BIGINT(), nullable=True),
        sa.Column("asn_range_end", sa.BIGINT(), nullable=True),
        sa.Column(
            "parsed_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="whois_records_pkey"),
        postgresql_ignore_search_path=False,
    )
    op.create_index("ix_whois_records_country", "whois_records", ["country"])
    op.create_index("ix_whois_records_name", "whois_records", ["name"])
    op.create_index("ix_whois_records_network_cidr", "whois_records", ["network_cidr"])
    op.create_index(
        "ix_whois_records_query_value", "whois_records", ["query_value"], unique=True
    )
    op.create_index(
        "ix_whois_records_registrant_email", "whois_records", ["registrant_email"]
    )
    op.create_index(
        "ix_whois_records_registrant_name", "whois_records", ["registrant_name"]
    )
    op.create_index(
        "ix_whois_records_registrar_name", "whois_records", ["registrar_name"]
    )
    op.create_table(
        "wordlists",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.VARCHAR(length=64), nullable=False),
        sa.Column("name", sa.VARCHAR(length=200), nullable=False),
        sa.Column("description", sa.VARCHAR(length=1000), nullable=False),
        sa.Column("origin", sa.VARCHAR(length=16), nullable=False),
        sa.Column("kind", sa.VARCHAR(length=16), nullable=False),
        sa.Column("filename", sa.VARCHAR(length=200), nullable=False),
        sa.Column("words", sa.INTEGER(), nullable=False),
        sa.Column("bytes", sa.INTEGER(), nullable=False),
        sa.Column("uploaded_by", sa.UUID(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="wordlists_pkey"),
    )
    op.create_index("ix_wordlists_kind", "wordlists", ["kind"])
    op.create_index("ix_wordlists_origin", "wordlists", ["origin"])
    op.create_index("ix_wordlists_slug", "wordlists", ["slug"], unique=True)
    op.create_table(
        "bounty_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("platform", sa.VARCHAR(length=32), nullable=False),
        sa.Column("program_id", sa.UUID(), nullable=False),
        sa.Column("handle", sa.VARCHAR(length=200), nullable=False),
        sa.Column("program_name", sa.VARCHAR(length=300), nullable=False),
        sa.Column("kind", sa.VARCHAR(length=32), nullable=False),
        sa.Column("asset_type", sa.VARCHAR(length=48), nullable=True),
        sa.Column("asset_identifier", sa.VARCHAR(length=1000), nullable=True),
        sa.Column("detail", sa.VARCHAR(length=500), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["bounty_programs.id"],
            name="bounty_events_program_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="bounty_events_pkey"),
    )
    op.create_index("ix_bounty_events_created_at", "bounty_events", ["created_at"])
    op.create_index("ix_bounty_events_handle", "bounty_events", ["handle"])
    op.create_index("ix_bounty_events_kind", "bounty_events", ["kind"])
    op.create_index("ix_bounty_events_platform", "bounty_events", ["platform"])
    op.create_index("ix_bounty_events_program_id", "bounty_events", ["program_id"])
    op.create_table(
        "bounty_scopes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("program_id", sa.UUID(), nullable=False),
        sa.Column("asset_type", sa.VARCHAR(length=48), nullable=False),
        sa.Column("asset_identifier", sa.VARCHAR(length=1000), nullable=False),
        sa.Column("scope_state", sa.VARCHAR(length=16), nullable=False),
        sa.Column("eligible_for_bounty", sa.BOOLEAN(), nullable=True),
        sa.Column("max_severity", sa.VARCHAR(length=16), nullable=True),
        sa.Column("instruction", sa.TEXT(), nullable=True),
        sa.Column("reference", sa.VARCHAR(length=500), nullable=True),
        sa.Column("target_value", sa.VARCHAR(length=500), nullable=True),
        sa.Column("target_type", _enum("targettype"), nullable=True),
        sa.Column("raw", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("synced_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("tier", sa.VARCHAR(length=32), nullable=True),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["bounty_programs.id"],
            name="bounty_scopes_program_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="bounty_scopes_pkey"),
        sa.UniqueConstraint(
            "program_id",
            "asset_type",
            "asset_identifier",
            name="uq_bounty_scope_asset",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_bounty_scopes_asset_type", "bounty_scopes", ["asset_type"])
    op.create_index("ix_bounty_scopes_program_id", "bounty_scopes", ["program_id"])
    op.create_index("ix_bounty_scopes_scope_state", "bounty_scopes", ["scope_state"])
    op.create_index("ix_bounty_scopes_target_value", "bounty_scopes", ["target_value"])
    op.create_table(
        "instance_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("singleton_key", sa.VARCHAR(length=20), nullable=False),
        sa.Column("instance_name", sa.VARCHAR(length=120), nullable=False),
        sa.Column("timezone", sa.VARCHAR(length=64), nullable=False),
        sa.Column("mode", sa.VARCHAR(), nullable=False),
        sa.Column("onboarding_completed", sa.BOOLEAN(), nullable=False),
        sa.Column(
            "onboarding_completed_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("onboarding_completed_by", sa.UUID(), nullable=True),
        sa.Column("onboarding_step", sa.INTEGER(), nullable=False),
        sa.Column(
            "onboarding_state", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("scan_history_retention_days", sa.INTEGER(), nullable=False),
        sa.Column("screenshot_retention_days", sa.INTEGER(), nullable=False),
        sa.Column("ai_enabled", sa.BOOLEAN(), nullable=False),
        sa.Column(
            "ai_features", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "report_defaults",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column(
            "mcp_enabled", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "mcp_settings",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column(
            "threat_intel_auto_sync",
            sa.BOOLEAN(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "bounty_sync_interval",
            sa.VARCHAR(length=16),
            server_default=sa.text("'daily'::character varying"),
            nullable=False,
        ),
        sa.Column(
            "bounty_synced_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column(
            "bounty_events_seen_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column(
            "bounty_settings",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column(
            "bounty_feed_interval",
            sa.VARCHAR(length=16),
            server_default=sa.text("'six_hours'::character varying"),
            nullable=False,
        ),
        sa.Column(
            "bounty_feed_synced_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column(
            "cert_recheck_enabled",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "new_checks_swept_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column(
            "oast_mode",
            sa.VARCHAR(length=16),
            server_default=sa.text("'off'::character varying"),
            nullable=False,
        ),
        sa.Column("oast_server", sa.VARCHAR(length=200), nullable=True),
        sa.Column(
            "oast_public_acknowledged",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "oast_wait_seconds",
            sa.INTEGER(),
            server_default=sa.text("60"),
            nullable=False,
        ),
        sa.Column(
            "concurrent_scans",
            sa.INTEGER(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("ai_connection_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ai_connection_id"],
            ["ai_connections.id"],
            name="fk_instance_settings_ai_connection",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="instance_settings_pkey"),
        sa.UniqueConstraint(
            "singleton_key",
            name="uq_instance_settings_singleton",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_table(
        "notification_channels",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=120), nullable=False),
        sa.Column("provider", sa.VARCHAR(length=20), nullable=False),
        sa.Column("is_active", sa.BOOLEAN(), nullable=False),
        sa.Column("config_encrypted", sa.VARCHAR(), nullable=False),
        sa.Column("events", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_test_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_test_ok", sa.BOOLEAN(), nullable=True),
        sa.Column("last_test_message", sa.VARCHAR(), nullable=True),
        sa.Column("last_sent_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_sent_ok", sa.BOOLEAN(), nullable=True),
        sa.Column("last_sent_message", sa.VARCHAR(length=500), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="notification_channels_created_by_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="notification_channels_pkey"),
    )
    op.create_table(
        "notification_receipts",
        sa.Column("notification_id", sa.INTEGER(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("read_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("dismissed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.id"],
            name="notification_receipts_notification_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="notification_receipts_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "notification_id", "user_id", name="notification_receipts_pkey"
        ),
    )
    op.create_index(
        "ix_notification_receipts_user_id", "notification_receipts", ["user_id"]
    )
    op.create_table(
        "projects",
        sa.Column("name", sa.VARCHAR(length=50), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.VARCHAR(length=100), nullable=False),
        sa.Column("is_active", sa.BOOLEAN(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("description", sa.VARCHAR(length=1000), nullable=True),
        sa.Column("label", sa.VARCHAR(length=50), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="projects_created_by_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="projects_pkey"),
        postgresql_ignore_search_path=False,
    )
    op.create_index("ix_projects_slug", "projects", ["slug"], unique=True)
    op.create_table(
        "proxies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=120), nullable=False),
        sa.Column("description", sa.VARCHAR(length=500), nullable=True),
        sa.Column("is_active", sa.BOOLEAN(), nullable=False),
        sa.Column("is_default", sa.BOOLEAN(), nullable=False),
        sa.Column("endpoints_encrypted", sa.VARCHAR(), nullable=False),
        sa.Column("endpoint_count", sa.INTEGER(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_test_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_test_ok", sa.BOOLEAN(), nullable=True),
        sa.Column("last_test_message", sa.VARCHAR(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="proxies_created_by_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="proxies_pkey"),
    )
    op.create_table(
        "user_marks",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("key", sa.VARCHAR(length=120), nullable=False),
        sa.Column("marked_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="user_marks_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "key", name="user_marks_pkey"),
    )
    op.create_table(
        "whois_nameservers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("whois_record_id", sa.UUID(), nullable=False),
        sa.Column("nameserver", sa.VARCHAR(length=500), nullable=False),
        sa.ForeignKeyConstraint(
            ["whois_record_id"],
            ["whois_records.id"],
            name="whois_nameservers_whois_record_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="whois_nameservers_pkey"),
    )
    op.create_index(
        "ix_whois_nameservers_nameserver", "whois_nameservers", ["nameserver"]
    )
    op.create_index(
        "ix_whois_nameservers_whois_record_id", "whois_nameservers", ["whois_record_id"]
    )
    op.create_table(
        "channel_chats",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("channel", sa.VARCHAR(length=16), nullable=False),
        sa.Column("external_id", sa.VARCHAR(length=64), nullable=False),
        sa.Column(
            "display",
            sa.VARCHAR(length=120),
            server_default=sa.text("''::character varying"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column(
            "capabilities",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column(
            "state",
            sa.VARCHAR(length=16),
            server_default=sa.text("'active'::character varying"),
            nullable=False,
        ),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_seen_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_command", sa.VARCHAR(length=80), nullable=True),
        sa.Column("calls", sa.INTEGER(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="channel_chats_project_id_fkey",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="channel_chats_user_id_fkey",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="channel_chats_pkey"),
        sa.UniqueConstraint(
            "channel",
            "external_id",
            name="uq_channel_chats_external",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_channel_chats_channel", "channel_chats", ["channel"])
    op.create_index("ix_channel_chats_project_id", "channel_chats", ["project_id"])
    op.create_index("ix_channel_chats_state", "channel_chats", ["state"])
    op.create_index("ix_channel_chats_user_id", "channel_chats", ["user_id"])
    op.create_table(
        "connectors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column(
            "kind",
            sa.VARCHAR(length=16),
            server_default=sa.text("'burp'::character varying"),
            nullable=False,
        ),
        sa.Column("name", sa.VARCHAR(length=80), nullable=False),
        sa.Column("token_hash", sa.VARCHAR(length=64), nullable=False),
        sa.Column("token_prefix", sa.VARCHAR(length=32), nullable=False),
        sa.Column(
            "ingest_tools",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column(
            "capture_bodies",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "include_static",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "scan_safe_methods_only",
            sa.BOOLEAN(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("context_id", sa.UUID(), nullable=True),
        sa.Column(
            "paused", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "requests_seen", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "dropped_out_of_scope",
            sa.INTEGER(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "candidates", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "scans_launched", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("last_seen_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_client", sa.VARCHAR(length=120), nullable=True),
        sa.Column("last_scan_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "record_hosts", sa.BOOLEAN(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "only_known_hosts",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "restore_credentials",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="connectors_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="connectors_pkey"),
        sa.UniqueConstraint(
            "token_hash",
            name="connectors_token_hash_key",
            postgresql_nulls_not_distinct=False,
        ),
        postgresql_ignore_search_path=False,
    )
    op.create_index("ix_connectors_kind", "connectors", ["kind"])
    op.create_index("ix_connectors_last_seen_at", "connectors", ["last_seen_at"])
    op.create_index("ix_connectors_project_id", "connectors", ["project_id"])
    op.create_index("ix_connectors_token_hash", "connectors", ["token_hash"])
    op.create_index(
        "uq_connector_project_kind", "connectors", ["project_id", "kind"], unique=True
    )
    op.create_table(
        "estate_candidate",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("domain", sa.VARCHAR(length=253), nullable=False),
        sa.Column("resolves", sa.BOOLEAN(), nullable=True),
        sa.Column("a", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("aaaa", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("cname", sa.VARCHAR(length=253), nullable=True),
        sa.Column("ports", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("registered_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("registrar", sa.VARCHAR(length=200), nullable=True),
        sa.Column("takeover_provider", sa.VARCHAR(length=64), nullable=True),
        sa.Column("checked_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="estate_candidate_project_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="estate_candidate_pkey"),
        sa.UniqueConstraint(
            "project_id",
            "domain",
            name="uq_estate_candidate_project_domain",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index(
        "ix_estate_candidate_checked_at", "estate_candidate", ["checked_at"]
    )
    op.create_index(
        "ix_estate_candidate_project_id", "estate_candidate", ["project_id"]
    )
    op.create_table(
        "estate_triage",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("domain", sa.VARCHAR(length=253), nullable=False),
        sa.Column("state", sa.VARCHAR(length=16), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="estate_triage_project_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="estate_triage_pkey"),
        sa.UniqueConstraint(
            "project_id",
            "domain",
            name="uq_estate_triage_project_domain",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_estate_triage_project_id", "estate_triage", ["project_id"])
    op.create_table(
        "interest_rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.VARCHAR(length=80), nullable=False),
        sa.Column("description", sa.VARCHAR(length=300), nullable=True),
        sa.Column("mode", sa.VARCHAR(length=16), nullable=False),
        sa.Column("query", sa.VARCHAR(length=2000), nullable=False),
        sa.Column("keywords", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "keyword_fields", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("live_only", sa.BOOLEAN(), nullable=False),
        sa.Column("kind", sa.VARCHAR(length=40), nullable=False),
        sa.Column("weight", sa.INTEGER(), nullable=True),
        sa.Column("enabled", sa.BOOLEAN(), nullable=False),
        sa.Column("builtin", sa.BOOLEAN(), nullable=False),
        sa.Column("notify", sa.BOOLEAN(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="interest_rules_created_by_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="interest_rules_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="interest_rules_pkey"),
    )
    op.create_index("ix_interest_rules_builtin", "interest_rules", ["builtin"])
    op.create_index("ix_interest_rules_enabled", "interest_rules", ["enabled"])
    op.create_index(
        "ix_interest_rules_project_enabled", "interest_rules", ["project_id", "enabled"]
    )
    op.create_index("ix_interest_rules_project_id", "interest_rules", ["project_id"])
    op.create_table(
        "organizations",
        sa.Column("name", sa.VARCHAR(length=100), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.VARCHAR(length=150), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("description", sa.VARCHAR(length=500), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="organizations_created_by_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="organizations_project_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="organizations_pkey"),
        sa.UniqueConstraint(
            "name",
            "project_id",
            name="uq_organization_name_project",
            postgresql_nulls_not_distinct=False,
        ),
        sa.UniqueConstraint(
            "slug",
            "project_id",
            name="uq_organization_slug_project",
            postgresql_nulls_not_distinct=False,
        ),
        postgresql_ignore_search_path=False,
    )
    op.create_index("ix_organizations_project_id", "organizations", ["project_id"])
    op.create_index("ix_organizations_slug", "organizations", ["slug"])
    op.create_table(
        "program_watches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("program_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=True),
        sa.Column("context_id", sa.UUID(), nullable=True),
        sa.Column("schedule_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.VARCHAR(length=16), nullable=False),
        sa.Column("engine_id", sa.UUID(), nullable=True),
        sa.Column("cadence", sa.VARCHAR(length=16), nullable=False),
        sa.Column("intensity", sa.VARCHAR(length=16), nullable=True),
        sa.Column("rate_limit", sa.INTEGER(), nullable=True),
        sa.Column("probe_on_resolve", sa.BOOLEAN(), nullable=False),
        sa.Column("probe_engine_id", sa.UUID(), nullable=True),
        sa.Column("follow_scope", sa.BOOLEAN(), nullable=False),
        sa.Column("alert_unresolved", sa.BOOLEAN(), nullable=False),
        sa.Column("alert_query", sa.VARCHAR(length=2000), nullable=False),
        sa.Column(
            "channel_ids", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("notify_in_app", sa.BOOLEAN(), nullable=False),
        sa.Column(
            "watch_items", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "unenforceable", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("hosts_seen", sa.INTEGER(), nullable=False),
        sa.Column("hosts_alerted", sa.INTEGER(), nullable=False),
        sa.Column(
            "last_certificate_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("last_alert_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_error", sa.VARCHAR(length=500), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="program_watches_created_by_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["bounty_programs.id"],
            name="program_watches_program_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="program_watches_project_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="program_watches_pkey"),
        sa.UniqueConstraint(
            "project_id",
            "program_id",
            name="uq_program_watch",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_program_watches_program_id", "program_watches", ["program_id"])
    op.create_index("ix_program_watches_project_id", "program_watches", ["project_id"])
    op.create_index("ix_program_watches_status", "program_watches", ["status"])
    op.create_table(
        "reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("template_id", sa.UUID(), nullable=True),
        sa.Column("template_name", sa.VARCHAR(length=200), nullable=False),
        sa.Column("scope", sa.VARCHAR(length=16), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=True),
        sa.Column("target_id", sa.UUID(), nullable=True),
        sa.Column("subject", sa.VARCHAR(length=500), nullable=False),
        sa.Column("title", sa.VARCHAR(length=200), nullable=False),
        sa.Column("spec", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.VARCHAR(length=16), nullable=False),
        sa.Column("progress", sa.INTEGER(), nullable=False),
        sa.Column("step", sa.VARCHAR(length=120), nullable=False),
        sa.Column("error", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("task_id", sa.VARCHAR(length=120), nullable=True),
        sa.Column("files", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("page_count", sa.INTEGER(), nullable=True),
        sa.Column("stats", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("ai_used", sa.BOOLEAN(), nullable=False),
        sa.Column("ai_provider", sa.VARCHAR(length=32), nullable=True),
        sa.Column("ai_model", sa.VARCHAR(length=80), nullable=True),
        sa.Column("ai_calls", sa.INTEGER(), nullable=False),
        sa.Column("ai_input_tokens", sa.INTEGER(), nullable=False),
        sa.Column("ai_output_tokens", sa.INTEGER(), nullable=False),
        sa.Column("ai_cached_calls", sa.INTEGER(), nullable=False),
        sa.Column("duration_seconds", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expires_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="reports_project_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="reports_pkey"),
    )
    op.create_index("ix_reports_created_at", "reports", ["created_at"])
    op.create_index("ix_reports_project_id", "reports", ["project_id"])
    op.create_index("ix_reports_scan_id", "reports", ["scan_id"])
    op.create_index("ix_reports_scope", "reports", ["scope"])
    op.create_index("ix_reports_status", "reports", ["status"])
    op.create_index("ix_reports_target_id", "reports", ["target_id"])
    op.create_index("ix_reports_template_id", "reports", ["template_id"])
    op.create_table(
        "scan_contexts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=200), nullable=False),
        sa.Column("description", sa.VARCHAR(length=1000), nullable=True),
        sa.Column("auth_type", sa.VARCHAR(), nullable=False),
        sa.Column("auth", sa.TEXT(), nullable=False),
        sa.Column("extra_headers", sa.TEXT(), nullable=False),
        sa.Column("global_rate_limit_override", sa.INTEGER(), nullable=True),
        sa.Column(
            "per_tool_rate_overrides",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "thread_multiplier", sa.DOUBLE_PRECISION(precision=53), nullable=False
        ),
        sa.Column(
            "timeout_multiplier", sa.DOUBLE_PRECISION(precision=53), nullable=False
        ),
        sa.Column(
            "excluded_subdomains",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "excluded_paths", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "excluded_ips", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "included_subdomains",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("follow_redirects_override", sa.BOOLEAN(), nullable=True),
        sa.Column("http_protocol", sa.VARCHAR(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_used_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_used_scan_id", sa.UUID(), nullable=True),
        sa.Column("proxy_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="scan_contexts_created_by_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="scan_contexts_project_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="scan_contexts_pkey"),
    )
    op.create_index("ix_scan_contexts_project_id", "scan_contexts", ["project_id"])
    op.create_index("ix_scan_contexts_proxy_id", "scan_contexts", ["proxy_id"])
    op.create_table(
        "scan_engines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=200), nullable=False),
        sa.Column("description", sa.VARCHAR(length=1000), nullable=True),
        sa.Column("intensity", sa.VARCHAR(), nullable=False),
        sa.Column("global_headers", sa.TEXT(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_used_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "tool_options",
            sa.TEXT(),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column(
            "stages",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column("yaml_source", sa.TEXT(), nullable=True),
        sa.Column(
            "builtin", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "transport_overrides",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="scan_engines_created_by_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="scan_engines_project_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="scan_engines_pkey"),
    )
    op.create_index("ix_scan_engines_project_id", "scan_engines", ["project_id"])
    op.create_index(
        "ux_scan_engines_builtin_project",
        "scan_engines",
        ["project_id"],
        unique=True,
        postgresql_where="builtin",
    )
    op.create_table(
        "scan_schedules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=200), nullable=False),
        sa.Column("target_ids", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("engine_id", sa.UUID(), nullable=False),
        sa.Column("engine_name", sa.VARCHAR(length=200), nullable=False),
        sa.Column("context_id", sa.UUID(), nullable=True),
        sa.Column("context_name", sa.VARCHAR(length=200), nullable=True),
        sa.Column("schedule_type", sa.VARCHAR(), nullable=False),
        sa.Column("run_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("interval_every", sa.INTEGER(), nullable=True),
        sa.Column("interval_unit", sa.VARCHAR(length=10), nullable=True),
        sa.Column("daily_at_time", sa.VARCHAR(length=5), nullable=True),
        sa.Column("cron_expression", sa.VARCHAR(length=120), nullable=True),
        sa.Column("timezone", sa.VARCHAR(length=64), nullable=False),
        sa.Column("status", sa.VARCHAR(), nullable=False),
        sa.Column("next_run_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_run_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_error", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("total_run_count", sa.INTEGER(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("intensity", sa.VARCHAR(length=16), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="scan_schedules_created_by_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="scan_schedules_project_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="scan_schedules_pkey"),
        postgresql_ignore_search_path=False,
    )
    op.create_index("ix_scan_schedules_engine_id", "scan_schedules", ["engine_id"])
    op.create_index("ix_scan_schedules_project_id", "scan_schedules", ["project_id"])
    op.create_index(
        "ix_scan_schedules_schedule_type", "scan_schedules", ["schedule_type"]
    )
    op.create_index("ix_scan_schedules_status", "scan_schedules", ["status"])
    op.create_index(
        "ix_scan_schedules_status_next_run", "scan_schedules", ["status", "next_run_at"]
    )
    op.create_table(
        "tags",
        sa.Column("name", sa.VARCHAR(length=50), nullable=False),
        sa.Column("color", sa.VARCHAR(length=7), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.VARCHAR(length=100), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="tags_created_by_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="tags_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="tags_pkey"),
        sa.UniqueConstraint(
            "name",
            "project_id",
            name="uq_tag_name_project",
            postgresql_nulls_not_distinct=False,
        ),
        sa.UniqueConstraint(
            "slug",
            "project_id",
            name="uq_tag_slug_project",
            postgresql_nulls_not_distinct=False,
        ),
        postgresql_ignore_search_path=False,
    )
    op.create_index("ix_tags_project_id", "tags", ["project_id"])
    op.create_index("ix_tags_slug", "tags", ["slug"])
    op.create_table(
        "targets",
        sa.Column("target_value", sa.VARCHAR(length=500), nullable=False),
        sa.Column("display_name", sa.VARCHAR(length=200), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("target_type", _enum("targettype"), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("whois_status", _enum("taskstatus"), nullable=False),
        sa.Column("whois_error", sa.VARCHAR(length=1000), nullable=True),
        sa.Column("whois_record_id", sa.UUID(), nullable=True),
        sa.Column("bgp_status", _enum("taskstatus"), nullable=False),
        sa.Column("dns_status", _enum("taskstatus"), nullable=False),
        sa.Column("dns_error", sa.VARCHAR(length=1000), nullable=True),
        sa.Column("dns_lookup_id", sa.UUID(), nullable=True),
        sa.Column(
            "seed_scans", sa.BOOLEAN(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "new_checks", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "new_checks_swept_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="targets_created_by_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["dns_lookup_id"],
            ["dns_lookups.id"],
            name="targets_dns_lookup_id_fkey",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="targets_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["whois_record_id"],
            ["whois_records.id"],
            name="targets_whois_record_id_fkey",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="targets_pkey"),
        sa.UniqueConstraint(
            "target_value",
            "project_id",
            name="uq_target_value_project",
            postgresql_nulls_not_distinct=False,
        ),
        postgresql_ignore_search_path=False,
    )
    op.create_index("ix_targets_bgp_status", "targets", ["bgp_status"])
    op.create_index("ix_targets_dns_lookup_id", "targets", ["dns_lookup_id"])
    op.create_index("ix_targets_dns_status", "targets", ["dns_status"])
    op.create_index("ix_targets_project_id", "targets", ["project_id"])
    op.create_index("ix_targets_whois_record_id", "targets", ["whois_record_id"])
    op.create_index("ix_targets_whois_status", "targets", ["whois_status"])
    op.create_table(
        "tripwires",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=80), nullable=False),
        sa.Column("dimension", sa.VARCHAR(length=32), nullable=False),
        sa.Column("query", sa.VARCHAR(length=2000), nullable=False),
        sa.Column("trigger", sa.VARCHAR(length=16), nullable=False),
        sa.Column("fire_on", sa.VARCHAR(length=16), nullable=False),
        sa.Column("scope_kind", sa.VARCHAR(length=16), nullable=False),
        sa.Column("scope_ids", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("actions", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("enabled", sa.BOOLEAN(), nullable=False),
        sa.Column("fired_count", sa.INTEGER(), nullable=False),
        sa.Column("last_fired_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "last_checked_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="tripwires_created_by_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="tripwires_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="tripwires_pkey"),
    )
    op.create_index(
        "ix_tripwires_project_enabled", "tripwires", ["project_id", "enabled"]
    )
    op.create_index("ix_tripwires_project_id", "tripwires", ["project_id"])
    op.create_table(
        "activity_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("timestamp", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("level", _enum("activitylevel"), nullable=False),
        sa.Column("event_type", _enum("activityevent"), nullable=False),
        sa.Column("title", sa.VARCHAR(length=200), nullable=False),
        sa.Column("description", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("target_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("scan_id", sa.UUID(), nullable=True),
        sa.Column("target_value", sa.VARCHAR(length=500), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="activity_logs_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="activity_logs_target_id_fkey",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="activity_logs_user_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="activity_logs_pkey"),
    )
    op.create_index("ix_activity_logs_event_type", "activity_logs", ["event_type"])
    op.create_index("ix_activity_logs_project_id", "activity_logs", ["project_id"])
    op.create_index("ix_activity_logs_scan_id", "activity_logs", ["scan_id"])
    op.create_index("ix_activity_logs_target_id", "activity_logs", ["target_id"])
    op.create_index("ix_activity_logs_timestamp", "activity_logs", ["timestamp"])
    op.create_index("ix_activity_logs_user_id", "activity_logs", ["user_id"])
    op.create_table(
        "ask_threads",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("dimension", sa.VARCHAR(length=32), nullable=False),
        sa.Column("asset_key", sa.VARCHAR(length=500), nullable=False),
        sa.Column("title", sa.VARCHAR(length=80), nullable=True),
        sa.Column("message_count", sa.INTEGER(), nullable=False),
        sa.Column("input_tokens", sa.INTEGER(), nullable=False),
        sa.Column("output_tokens", sa.INTEGER(), nullable=False),
        sa.Column("cost_usd", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="ask_threads_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="ask_threads_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="ask_threads_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="ask_threads_pkey"),
    )
    op.create_index(
        "ix_ask_threads_asset",
        "ask_threads",
        ["target_id", "dimension", "asset_key", "user_id"],
    )
    op.create_index("ix_ask_threads_project_id", "ask_threads", ["project_id"])
    op.create_index("ix_ask_threads_target_id", "ask_threads", ["target_id"])
    op.create_index("ix_ask_threads_user_id", "ask_threads", ["user_id"])
    op.create_table(
        "connector_actions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("connector_id", sa.UUID(), nullable=False),
        sa.Column(
            "kind",
            sa.VARCHAR(length=16),
            server_default=sa.text("'repeater'::character varying"),
            nullable=False,
        ),
        sa.Column("url", sa.VARCHAR(length=2000), nullable=False),
        sa.Column(
            "method",
            sa.VARCHAR(length=16),
            server_default=sa.text("'GET'::character varying"),
            nullable=False,
        ),
        sa.Column("label", sa.VARCHAR(length=120), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("delivered_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("request", sa.TEXT(), nullable=True),
        sa.Column("response", sa.TEXT(), nullable=True),
        sa.Column("notes", sa.TEXT(), nullable=True),
        sa.Column("color", sa.VARCHAR(length=16), nullable=True),
        sa.Column("scan_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["connector_id"],
            ["connectors.id"],
            name="connector_actions_connector_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="connector_actions_pkey"),
    )
    op.create_index(
        "ix_connector_actions_connector_id", "connector_actions", ["connector_id"]
    )
    op.create_index(
        "ix_connector_actions_created_at", "connector_actions", ["created_at"]
    )
    op.create_index(
        "ix_connector_actions_delivered_at", "connector_actions", ["delivered_at"]
    )
    op.create_table(
        "connector_candidates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("connector_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=True),
        sa.Column("signature", sa.VARCHAR(length=64), nullable=False),
        sa.Column("url", sa.VARCHAR(length=2000), nullable=False),
        sa.Column("scheme", sa.VARCHAR(length=8), nullable=False),
        sa.Column("host", sa.VARCHAR(length=500), nullable=False),
        sa.Column("port", sa.INTEGER(), server_default=sa.text("443"), nullable=False),
        sa.Column("path", sa.VARCHAR(length=1500), nullable=False),
        sa.Column("dir_path", sa.VARCHAR(length=1500), nullable=False),
        sa.Column("filename", sa.VARCHAR(length=300), nullable=True),
        sa.Column("extension", sa.VARCHAR(length=16), nullable=True),
        sa.Column("depth", sa.INTEGER(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "methods",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column(
            "params",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column(
            "param_count", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("endpoint_class", sa.VARCHAR(length=24), nullable=True),
        sa.Column(
            "interests",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column(
            "notices",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column("status_code", sa.INTEGER(), nullable=True),
        sa.Column("content_type", sa.VARCHAR(length=120), nullable=True),
        sa.Column("content_length", sa.INTEGER(), nullable=True),
        sa.Column("title", sa.VARCHAR(length=500), nullable=True),
        sa.Column(
            "authenticated",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "source_tool",
            sa.VARCHAR(length=16),
            server_default=sa.text("'proxy'::character varying"),
            nullable=False,
        ),
        sa.Column("request_sample", sa.TEXT(), nullable=True),
        sa.Column(
            "known", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "state",
            sa.VARCHAR(length=16),
            server_default=sa.text("'new'::character varying"),
            nullable=False,
        ),
        sa.Column("hits", sa.INTEGER(), server_default=sa.text("1"), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=True),
        sa.Column("first_seen_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_seen_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("notified_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["connector_id"],
            ["connectors.id"],
            name="connector_candidates_connector_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="connector_candidates_pkey"),
        sa.UniqueConstraint(
            "connector_id",
            "signature",
            name="uq_connector_candidate_signature",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index(
        "ix_connector_candidates_authenticated",
        "connector_candidates",
        ["authenticated"],
    )
    op.create_index(
        "ix_connector_candidates_connector_id", "connector_candidates", ["connector_id"]
    )
    op.create_index(
        "ix_connector_candidates_endpoint_class",
        "connector_candidates",
        ["endpoint_class"],
    )
    op.create_index(
        "ix_connector_candidates_first_seen_at",
        "connector_candidates",
        ["first_seen_at"],
    )
    op.create_index("ix_connector_candidates_host", "connector_candidates", ["host"])
    op.create_index("ix_connector_candidates_known", "connector_candidates", ["known"])
    op.create_index(
        "ix_connector_candidates_last_seen_at", "connector_candidates", ["last_seen_at"]
    )
    op.create_index(
        "ix_connector_candidates_notified_at", "connector_candidates", ["notified_at"]
    )
    op.create_index(
        "ix_connector_candidates_param_count", "connector_candidates", ["param_count"]
    )
    op.create_index(
        "ix_connector_candidates_project_id", "connector_candidates", ["project_id"]
    )
    op.create_index(
        "ix_connector_candidates_signature", "connector_candidates", ["signature"]
    )
    op.create_index("ix_connector_candidates_state", "connector_candidates", ["state"])
    op.create_index(
        "ix_connector_candidates_status_code", "connector_candidates", ["status_code"]
    )
    op.create_index(
        "ix_connector_candidates_target_id", "connector_candidates", ["target_id"]
    )
    op.create_table(
        "connector_hosts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("connector_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("host", sa.VARCHAR(length=500), nullable=False),
        sa.Column(
            "registrable",
            sa.VARCHAR(length=500),
            server_default=sa.text("''::character varying"),
            nullable=False,
        ),
        sa.Column("target_id", sa.UUID(), nullable=True),
        sa.Column(
            "requests", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "dismissed", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("first_seen_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_seen_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["connector_id"],
            ["connectors.id"],
            name="connector_hosts_connector_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="connector_hosts_pkey"),
        sa.UniqueConstraint(
            "connector_id",
            "host",
            name="uq_connector_host",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index(
        "ix_connector_hosts_connector_id", "connector_hosts", ["connector_id"]
    )
    op.create_index("ix_connector_hosts_dismissed", "connector_hosts", ["dismissed"])
    op.create_index("ix_connector_hosts_host", "connector_hosts", ["host"])
    op.create_index(
        "ix_connector_hosts_last_seen_at", "connector_hosts", ["last_seen_at"]
    )
    op.create_index("ix_connector_hosts_project_id", "connector_hosts", ["project_id"])
    op.create_index(
        "ix_connector_hosts_registrable", "connector_hosts", ["registrable"]
    )
    op.create_index("ix_connector_hosts_target_id", "connector_hosts", ["target_id"])
    op.create_table(
        "dns_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("dns_lookup_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("record_type", _enum("dnsrecordtype"), nullable=False),
        sa.Column("value", sa.VARCHAR(length=2000), nullable=False),
        sa.Column("priority", sa.INTEGER(), nullable=True),
        sa.Column("weight", sa.INTEGER(), nullable=True),
        sa.Column("port", sa.INTEGER(), nullable=True),
        sa.Column("soa_email", sa.VARCHAR(length=500), nullable=True),
        sa.Column("soa_serial", sa.BIGINT(), nullable=True),
        sa.Column("soa_refresh", sa.INTEGER(), nullable=True),
        sa.Column("soa_retry", sa.INTEGER(), nullable=True),
        sa.Column("soa_expire", sa.INTEGER(), nullable=True),
        sa.Column("soa_minttl", sa.INTEGER(), nullable=True),
        sa.Column("caa_tag", sa.VARCHAR(length=100), nullable=True),
        sa.Column("caa_flag", sa.INTEGER(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["dns_lookup_id"],
            ["dns_lookups.id"],
            name="dns_records_dns_lookup_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="dns_records_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="dns_records_pkey"),
    )
    op.create_index("ix_dns_records_dns_lookup_id", "dns_records", ["dns_lookup_id"])
    op.create_index("ix_dns_records_record_type", "dns_records", ["record_type"])
    op.create_index("ix_dns_records_target_id", "dns_records", ["target_id"])
    op.create_index("ix_dns_records_value", "dns_records", ["value"])
    op.create_table(
        "interest_dismissals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("host", sa.VARCHAR(length=500), nullable=False),
        sa.Column("kind", sa.VARCHAR(length=40), nullable=False),
        sa.Column("note", sa.VARCHAR(length=300), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="interest_dismissals_created_by_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="interest_dismissals_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="interest_dismissals_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="interest_dismissals_pkey"),
        sa.UniqueConstraint(
            "target_id",
            "host",
            "kind",
            name="uq_interest_dismissal",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_interest_dismissals_host", "interest_dismissals", ["host"])
    op.create_index(
        "ix_interest_dismissals_project_id", "interest_dismissals", ["project_id"]
    )
    op.create_index(
        "ix_interest_dismissals_target_id", "interest_dismissals", ["target_id"]
    )
    op.create_table(
        "issue_tracker_routes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=True),
        sa.Column("tracker_id", sa.UUID(), nullable=False),
        sa.Column("destination", sa.VARCHAR(length=200), nullable=False),
        sa.Column("issue_type", sa.VARCHAR(length=100), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="issue_tracker_routes_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="issue_tracker_routes_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tracker_id"],
            ["issue_trackers.id"],
            name="issue_tracker_routes_tracker_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="issue_tracker_routes_pkey"),
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
        postgresql_where="(target_id IS NULL)",
    )
    op.create_index(
        "uq_issue_route_target",
        "issue_tracker_routes",
        ["project_id", "target_id"],
        unique=True,
        postgresql_where="(target_id IS NOT NULL)",
    )
    op.create_table(
        "lookalike_triage",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("domain", sa.VARCHAR(length=253), nullable=False),
        sa.Column("state", sa.VARCHAR(length=16), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="lookalike_triage_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="lookalike_triage_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="lookalike_triage_pkey"),
        sa.UniqueConstraint(
            "target_id",
            "domain",
            name="uq_lookalike_triage_target_domain",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index(
        "ix_lookalike_triage_project_id", "lookalike_triage", ["project_id"]
    )
    op.create_index("ix_lookalike_triage_target_id", "lookalike_triage", ["target_id"])
    op.create_table(
        "scans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("engine_id", sa.UUID(), nullable=True),
        sa.Column("engine_name", sa.VARCHAR(length=200), nullable=False),
        sa.Column("context_id", sa.UUID(), nullable=True),
        sa.Column("context_name", sa.VARCHAR(length=200), nullable=True),
        sa.Column(
            "execution_config", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("status", sa.VARCHAR(), nullable=False),
        sa.Column("subdomains_found", sa.INTEGER(), nullable=False),
        sa.Column("ips_found", sa.INTEGER(), nullable=False),
        sa.Column("open_ports_found", sa.INTEGER(), nullable=False),
        sa.Column("vulnerabilities_found", sa.INTEGER(), nullable=False),
        sa.Column("endpoints_found", sa.INTEGER(), nullable=False),
        sa.Column("error", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "celery_task_ids",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column("schedule_id", sa.UUID(), nullable=True),
        sa.Column("schedule_type", sa.VARCHAR(length=20), nullable=True),
        sa.Column(
            "http_assets_found",
            sa.INTEGER(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "scope",
            sa.VARCHAR(length=16),
            server_default=sa.text("'full'::character varying"),
            nullable=False,
        ),
        sa.Column("parent_scan_id", sa.UUID(), nullable=True),
        sa.Column("interest_signature", sa.VARCHAR(length=64), nullable=True),
        sa.Column(
            "interest_judged_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("interest_model", sa.VARCHAR(length=80), nullable=True),
        sa.Column("run_group_id", sa.UUID(), nullable=True),
        sa.Column(
            "run_epoch", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("paused_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "paused_seconds",
            sa.DOUBLE_PRECISION(precision=53),
            server_default=sa.text("'0'::double precision"),
            nullable=False,
        ),
        sa.Column(
            "secrets_found", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="scans_created_by_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["parent_scan_id"],
            ["scans.id"],
            name="fk_scans_parent_scan_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="scans_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["schedule_id"],
            ["scan_schedules.id"],
            name="fk_scans_schedule_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="scans_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="scans_pkey"),
        postgresql_ignore_search_path=False,
    )
    op.create_index("ix_scans_engine_id", "scans", ["engine_id"])
    op.create_index("ix_scans_parent_scan_id", "scans", ["parent_scan_id"])
    op.create_index("ix_scans_project_id", "scans", ["project_id"])
    op.create_index(
        "ix_scans_project_started",
        "scans",
        [
            "project_id",
            sa.literal_column("COALESCE(started_at, created_at) DESC"),
            sa.literal_column("created_at DESC"),
        ],
    )
    op.create_index("ix_scans_run_group_id", "scans", ["run_group_id"])
    op.create_index("ix_scans_schedule_id", "scans", ["schedule_id"])
    op.create_index("ix_scans_scope", "scans", ["scope"])
    op.create_index("ix_scans_status", "scans", ["status"])
    op.create_index("ix_scans_target_id", "scans", ["target_id"])
    op.create_index(
        "ix_scans_target_started",
        "scans",
        [
            "target_id",
            sa.literal_column("COALESCE(started_at, created_at) DESC"),
            sa.literal_column("created_at DESC"),
        ],
    )
    op.create_table(
        "target_bgp_summaries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("prefix_count", sa.INTEGER(), nullable=True),
        sa.Column("peer_count", sa.INTEGER(), nullable=True),
        sa.Column("announced", sa.BOOLEAN(), nullable=True),
        sa.Column("asn", sa.BIGINT(), nullable=True),
        sa.Column("prefix", sa.VARCHAR(), nullable=True),
        sa.Column("holder", sa.VARCHAR(), nullable=True),
        sa.Column("queried_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="target_bgp_summaries_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="target_bgp_summaries_pkey"),
    )
    op.create_index(
        "ix_target_bgp_summaries_target_id",
        "target_bgp_summaries",
        ["target_id"],
        unique=True,
    )
    op.create_table(
        "target_organizations",
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="target_organizations_organization_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="target_organizations_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "target_id", "organization_id", name="target_organizations_pkey"
        ),
    )
    op.create_table(
        "target_seeds",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.VARCHAR(length=16), nullable=False),
        sa.Column("value", sa.VARCHAR(length=2000), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="target_seeds_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="target_seeds_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="target_seeds_pkey"),
        sa.UniqueConstraint(
            "target_id",
            "value",
            name="uq_target_seed_value",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_target_seeds_project_id", "target_seeds", ["project_id"])
    op.create_index("ix_target_seeds_target_id", "target_seeds", ["target_id"])
    op.create_table(
        "target_tags",
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["tags.id"], name="target_tags_tag_id_fkey", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="target_tags_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("target_id", "tag_id", name="target_tags_pkey"),
    )
    op.create_table(
        "tracked_issues",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tracker_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("template_id", sa.VARCHAR(length=200), nullable=False),
        sa.Column("severity", sa.VARCHAR(length=16), nullable=False),
        sa.Column("grouped", sa.BOOLEAN(), nullable=False),
        sa.Column("destination", sa.VARCHAR(length=200), nullable=False),
        sa.Column("issue_type", sa.VARCHAR(length=100), nullable=True),
        sa.Column("title", sa.VARCHAR(length=255), nullable=False),
        sa.Column("state", sa.VARCHAR(length=16), nullable=False),
        sa.Column("external_key", sa.VARCHAR(length=250), nullable=True),
        sa.Column("external_id", sa.VARCHAR(length=250), nullable=True),
        sa.Column("url", sa.VARCHAR(length=1000), nullable=True),
        sa.Column("remote_status", sa.VARCHAR(length=100), nullable=True),
        sa.Column("remote_category", sa.VARCHAR(length=16), nullable=True),
        sa.Column("done_noted", sa.BOOLEAN(), nullable=False),
        sa.Column("error", sa.VARCHAR(length=500), nullable=True),
        sa.Column("attempts", sa.INTEGER(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("filed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status_read_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="tracked_issues_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="tracked_issues_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tracker_id"],
            ["issue_trackers.id"],
            name="tracked_issues_tracker_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="tracked_issues_pkey"),
    )
    op.create_index("ix_tracked_issues_project_id", "tracked_issues", ["project_id"])
    op.create_index("ix_tracked_issues_state", "tracked_issues", ["state"])
    op.create_index("ix_tracked_issues_target_id", "tracked_issues", ["target_id"])
    op.create_index("ix_tracked_issues_tracker_id", "tracked_issues", ["tracker_id"])
    op.create_table(
        "vulnerability_triage",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("fingerprint", sa.VARCHAR(length=64), nullable=False),
        sa.Column("template_id", sa.VARCHAR(length=200), nullable=False),
        sa.Column("matched_at", sa.VARCHAR(length=2000), nullable=False),
        sa.Column(
            "state",
            sa.VARCHAR(length=20),
            server_default=sa.text("'open'::character varying"),
            nullable=False,
        ),
        sa.Column("decided_by", sa.UUID(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="vulnerability_triage_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="vulnerability_triage_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="vulnerability_triage_pkey"),
        sa.UniqueConstraint(
            "target_id",
            "fingerprint",
            name="uq_vulntriage_target_fp",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index(
        "ix_vulnerability_triage_fingerprint", "vulnerability_triage", ["fingerprint"]
    )
    op.create_index(
        "ix_vulnerability_triage_project_id", "vulnerability_triage", ["project_id"]
    )
    op.create_index("ix_vulnerability_triage_state", "vulnerability_triage", ["state"])
    op.create_index(
        "ix_vulnerability_triage_target_id", "vulnerability_triage", ["target_id"]
    )
    op.create_table(
        "watch_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("watch_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.VARCHAR(length=32), nullable=False),
        sa.Column("name", sa.VARCHAR(length=500), nullable=True),
        sa.Column("detail", sa.VARCHAR(length=500), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="watch_events_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["watch_id"],
            ["program_watches.id"],
            name="watch_events_watch_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="watch_events_pkey"),
    )
    op.create_index("ix_watch_events_created_at", "watch_events", ["created_at"])
    op.create_index("ix_watch_events_kind", "watch_events", ["kind"])
    op.create_index("ix_watch_events_project_id", "watch_events", ["project_id"])
    op.create_index(
        "ix_watch_events_watch_created", "watch_events", ["watch_id", "created_at"]
    )
    op.create_index("ix_watch_events_watch_id", "watch_events", ["watch_id"])
    op.create_table(
        "watch_hosts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("watch_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=500), nullable=False),
        sa.Column("state", sa.VARCHAR(length=16), nullable=False),
        sa.Column("reason", sa.VARCHAR(length=200), nullable=True),
        sa.Column("matched_item", sa.VARCHAR(length=500), nullable=True),
        sa.Column("cert_sha256", sa.VARCHAR(length=64), nullable=True),
        sa.Column("issuer", sa.VARCHAR(length=500), nullable=True),
        sa.Column("not_before", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("sightings", sa.INTEGER(), nullable=False),
        sa.Column("first_seen_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_seen_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "resolved_ips", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("cname", sa.VARCHAR(length=500), nullable=True),
        sa.Column("is_wildcard", sa.BOOLEAN(), nullable=False),
        sa.Column("resolved_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("next_check_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("scan_id", sa.UUID(), nullable=True),
        sa.Column("probed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status_code", sa.INTEGER(), nullable=True),
        sa.Column("title", sa.VARCHAR(length=1000), nullable=True),
        sa.Column("tech", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("screenshot_path", sa.VARCHAR(length=500), nullable=True),
        sa.Column("fingerprint", sa.VARCHAR(length=64), nullable=True),
        sa.Column("alerted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("alerts", sa.INTEGER(), nullable=False),
        sa.Column("muted_from", sa.VARCHAR(length=16), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="watch_hosts_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="watch_hosts_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["watch_id"],
            ["program_watches.id"],
            name="watch_hosts_watch_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="watch_hosts_pkey"),
        sa.UniqueConstraint(
            "watch_id",
            "name",
            name="uq_watch_host",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_watch_hosts_first_seen_at", "watch_hosts", ["first_seen_at"])
    op.create_index("ix_watch_hosts_name", "watch_hosts", ["name"])
    op.create_index("ix_watch_hosts_next_check_at", "watch_hosts", ["next_check_at"])
    op.create_index("ix_watch_hosts_project_id", "watch_hosts", ["project_id"])
    op.create_index("ix_watch_hosts_scan_id", "watch_hosts", ["scan_id"])
    op.create_index("ix_watch_hosts_state", "watch_hosts", ["state"])
    op.create_index("ix_watch_hosts_target_id", "watch_hosts", ["target_id"])
    op.create_index(
        "ix_watch_hosts_watch_first_seen", "watch_hosts", ["watch_id", "first_seen_at"]
    )
    op.create_index("ix_watch_hosts_watch_id", "watch_hosts", ["watch_id"])
    op.create_table(
        "ask_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.VARCHAR(length=16), nullable=False),
        sa.Column("text", sa.TEXT(), nullable=False),
        sa.Column("citations", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("trace", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("flags", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("suggestion", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("model", sa.VARCHAR(length=80), nullable=True),
        sa.Column("input_tokens", sa.INTEGER(), nullable=False),
        sa.Column("output_tokens", sa.INTEGER(), nullable=False),
        sa.Column("cost_usd", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["ask_threads.id"],
            name="ask_messages_thread_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="ask_messages_pkey"),
    )
    op.create_index(
        "ix_ask_messages_thread_created", "ask_messages", ["thread_id", "created_at"]
    )
    op.create_index("ix_ask_messages_thread_id", "ask_messages", ["thread_id"])
    op.create_table(
        "asset_rechecks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("parent_scan_id", sa.UUID(), nullable=False),
        sa.Column("dimension", sa.VARCHAR(length=32), nullable=False),
        sa.Column("asset_kind", sa.VARCHAR(length=16), nullable=False),
        sa.Column("asset_key", sa.VARCHAR(length=500), nullable=False),
        sa.Column(
            "changed", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("changes", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_scan_id"],
            ["scans.id"],
            name="asset_rechecks_parent_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="asset_rechecks_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="asset_rechecks_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="asset_rechecks_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="asset_rechecks_pkey"),
    )
    op.create_index("ix_asset_rechecks_asset_key", "asset_rechecks", ["asset_key"])
    op.create_index(
        "ix_asset_rechecks_parent_lookup",
        "asset_rechecks",
        ["parent_scan_id", "asset_key"],
    )
    op.create_index("ix_asset_rechecks_project_id", "asset_rechecks", ["project_id"])
    op.create_index("ix_asset_rechecks_scan_id", "asset_rechecks", ["scan_id"])
    op.create_index("ix_asset_rechecks_target_id", "asset_rechecks", ["target_id"])
    op.create_table(
        "domain_posture",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("zone", sa.VARCHAR(length=253), nullable=False),
        sa.Column("hosts", sa.INTEGER(), server_default=sa.text("0"), nullable=False),
        sa.Column("spf", sa.TEXT(), nullable=True),
        sa.Column("spf_all", sa.VARCHAR(length=16), nullable=True),
        sa.Column("spf_lookups", sa.INTEGER(), nullable=True),
        sa.Column("dmarc", sa.TEXT(), nullable=True),
        sa.Column("dmarc_policy", sa.VARCHAR(length=16), nullable=True),
        sa.Column("dmarc_subdomain_policy", sa.VARCHAR(length=16), nullable=True),
        sa.Column("dmarc_pct", sa.INTEGER(), nullable=True),
        sa.Column("dmarc_rua", sa.BOOLEAN(), nullable=True),
        sa.Column(
            "dkim_selectors", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("dkim_key_bits", sa.INTEGER(), nullable=True),
        sa.Column("mx", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "null_mx", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("mta_sts", sa.VARCHAR(length=500), nullable=True),
        sa.Column("mta_sts_mode", sa.VARCHAR(length=16), nullable=True),
        sa.Column("tls_rpt", sa.VARCHAR(length=500), nullable=True),
        sa.Column(
            "dnssec",
            sa.VARCHAR(length=16),
            server_default=sa.text("'unknown'::character varying"),
            nullable=False,
        ),
        sa.Column("caa", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "posture_issues", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "posture_checked", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("evidence", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("discovered_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("parent", sa.VARCHAR(length=253), nullable=True),
        sa.Column(
            "dmarc_inherited",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="domain_posture_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="domain_posture_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="domain_posture_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="domain_posture_pkey"),
        sa.UniqueConstraint(
            "scan_id",
            "zone",
            name="uq_domain_posture_scan_zone",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_domain_posture_project_id", "domain_posture", ["project_id"])
    op.create_index(
        "ix_domain_posture_scan_discovered",
        "domain_posture",
        ["scan_id", "discovered_at"],
    )
    op.create_index("ix_domain_posture_scan_id", "domain_posture", ["scan_id"])
    op.create_index(
        "ix_domain_posture_target_discovered",
        "domain_posture",
        ["target_id", "discovered_at"],
    )
    op.create_index("ix_domain_posture_target_id", "domain_posture", ["target_id"])
    op.create_index("ix_domain_posture_zone", "domain_posture", ["zone"])
    op.create_table(
        "endpoint_coverage",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("source", sa.VARCHAR(length=24), nullable=False),
        sa.Column("tool", sa.VARCHAR(length=40), nullable=True),
        sa.Column("status", sa.VARCHAR(length=16), nullable=False),
        sa.Column(
            "hosts_total", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("hosts_scanned", sa.INTEGER(), nullable=True),
        sa.Column(
            "hosts_dropped", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("urls_found", sa.INTEGER(), nullable=True),
        sa.Column("urls_stored", sa.INTEGER(), nullable=True),
        sa.Column("urls_probed", sa.INTEGER(), nullable=True),
        sa.Column("pages_fetched", sa.INTEGER(), nullable=True),
        sa.Column("depth_reached", sa.INTEGER(), nullable=True),
        sa.Column("errors", sa.INTEGER(), nullable=True),
        sa.Column(
            "capped", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("cap_reason", sa.VARCHAR(length=200), nullable=True),
        sa.Column("command", sa.TEXT(), nullable=True),
        sa.Column("error", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ended_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column(
            "urls_dropped",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="endpoint_coverage_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="endpoint_coverage_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="endpoint_coverage_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="endpoint_coverage_pkey"),
    )
    op.create_index(
        "ix_endpoint_coverage_project_id", "endpoint_coverage", ["project_id"]
    )
    op.create_index("ix_endpoint_coverage_scan_id", "endpoint_coverage", ["scan_id"])
    op.create_index("ix_endpoint_coverage_source", "endpoint_coverage", ["source"])
    op.create_index(
        "ix_endpoint_coverage_target_id", "endpoint_coverage", ["target_id"]
    )
    op.create_table(
        "endpoints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("signature", sa.VARCHAR(length=64), nullable=False),
        sa.Column("url", sa.VARCHAR(length=2000), nullable=False),
        sa.Column("host", sa.VARCHAR(length=500), nullable=False),
        sa.Column("port", sa.INTEGER(), server_default=sa.text("443"), nullable=False),
        sa.Column(
            "scheme",
            sa.VARCHAR(length=8),
            server_default=sa.text("'https'::character varying"),
            nullable=False,
        ),
        sa.Column("path", sa.VARCHAR(length=1500), nullable=False),
        sa.Column("dir_path", sa.VARCHAR(length=1500), nullable=False),
        sa.Column("filename", sa.VARCHAR(length=300), nullable=True),
        sa.Column("extension", sa.VARCHAR(length=10), nullable=True),
        sa.Column("depth", sa.INTEGER(), server_default=sa.text("0"), nullable=False),
        sa.Column("params", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "param_count", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "param_samples", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "variants", sa.INTEGER(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column(
            "more_variants",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("methods", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("sources", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("primary_source", sa.VARCHAR(length=24), nullable=False),
        sa.Column("discovery", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("found_on", sa.VARCHAR(length=2000), nullable=True),
        sa.Column(
            "is_probed", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("status_code", sa.INTEGER(), nullable=True),
        sa.Column("content_type", sa.VARCHAR(length=255), nullable=True),
        sa.Column("content_length", sa.INTEGER(), nullable=True),
        sa.Column("title", sa.VARCHAR(length=1000), nullable=True),
        sa.Column("words", sa.INTEGER(), nullable=True),
        sa.Column("lines", sa.INTEGER(), nullable=True),
        sa.Column("response_time", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("redirect_location", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("content_hash", sa.VARCHAR(length=80), nullable=True),
        sa.Column("tech", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("endpoint_class", sa.VARCHAR(length=16), nullable=False),
        sa.Column("interest", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("http_asset_id", sa.UUID(), nullable=True),
        sa.Column("subdomain_id", sa.UUID(), nullable=True),
        sa.Column(
            "archive_last_seen", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("discovered_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "shape",
            sa.VARCHAR(length=1500),
            server_default=sa.text("''::character varying"),
            nullable=False,
        ),
        sa.Column(
            "family",
            sa.VARCHAR(length=64),
            server_default=sa.text("''::character varying"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="endpoints_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"], ["scans.id"], name="endpoints_scan_id_fkey", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="endpoints_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="endpoints_pkey"),
        sa.UniqueConstraint(
            "scan_id",
            "signature",
            name="uq_endpoint_scan_signature",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_endpoints_content_hash", "endpoints", ["content_hash"])
    op.create_index("ix_endpoints_dir_path", "endpoints", ["dir_path"])
    op.create_index("ix_endpoints_discovered_at", "endpoints", ["discovered_at"])
    op.create_index("ix_endpoints_extension", "endpoints", ["extension"])
    op.create_index("ix_endpoints_host", "endpoints", ["host"])
    op.create_index(
        "ix_endpoints_host_trgm",
        "endpoints",
        ["host"],
        postgresql_ops={"host": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index("ix_endpoints_http_asset_id", "endpoints", ["http_asset_id"])
    op.create_index("ix_endpoints_is_probed", "endpoints", ["is_probed"])
    op.create_index("ix_endpoints_param_count", "endpoints", ["param_count"])
    op.create_index(
        "ix_endpoints_path_trgm",
        "endpoints",
        ["path"],
        postgresql_ops={"path": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index(
        "ix_endpoints_project_host_shape", "endpoints", ["project_id", "host", "shape"]
    )
    op.create_index("ix_endpoints_project_id", "endpoints", ["project_id"])
    op.create_index(
        "ix_endpoints_scan_dir", "endpoints", ["scan_id", "dir_path", "path"]
    )
    op.create_index(
        "ix_endpoints_scan_discovered", "endpoints", ["scan_id", "discovered_at"]
    )
    op.create_index("ix_endpoints_scan_family", "endpoints", ["scan_id", "family"])
    op.create_index("ix_endpoints_scan_id", "endpoints", ["scan_id"])
    op.create_index("ix_endpoints_signature", "endpoints", ["signature"])
    op.create_index("ix_endpoints_status_code", "endpoints", ["status_code"])
    op.create_index("ix_endpoints_subdomain_id", "endpoints", ["subdomain_id"])
    op.create_index(
        "ix_endpoints_target_discovered", "endpoints", ["target_id", "discovered_at"]
    )
    op.create_index("ix_endpoints_target_id", "endpoints", ["target_id"])
    op.create_index(
        "ix_endpoints_target_signature", "endpoints", ["target_id", "signature"]
    )
    op.create_index(
        "ix_endpoints_title_trgm",
        "endpoints",
        ["title"],
        postgresql_ops={"title": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index(
        "ix_endpoints_url_trgm",
        "endpoints",
        ["url"],
        postgresql_ops={"url": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_table(
        "exports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("dimension", sa.VARCHAR(length=32), nullable=False),
        sa.Column("scope", sa.VARCHAR(length=16), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=True),
        sa.Column("target_id", sa.UUID(), nullable=True),
        sa.Column("subject", sa.VARCHAR(length=200), nullable=False),
        sa.Column("query", sa.VARCHAR(length=2000), nullable=False),
        sa.Column("filters", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("export_format", sa.VARCHAR(length=16), nullable=False),
        sa.Column("include_evidence", sa.BOOLEAN(), nullable=False),
        sa.Column("status", sa.VARCHAR(length=16), nullable=False),
        sa.Column("progress", sa.INTEGER(), nullable=False),
        sa.Column("step", sa.VARCHAR(length=100), nullable=False),
        sa.Column("error", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("task_id", sa.VARCHAR(length=100), nullable=True),
        sa.Column("filename", sa.VARCHAR(length=255), nullable=True),
        sa.Column("bytes_written", sa.BIGINT(), nullable=False),
        sa.Column("row_count", sa.INTEGER(), nullable=False),
        sa.Column("total_rows", sa.INTEGER(), nullable=False),
        sa.Column("capped", sa.BOOLEAN(), nullable=False),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("expires_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="exports_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"], ["scans.id"], name="exports_scan_id_fkey", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="exports_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="exports_pkey"),
    )
    op.create_index("ix_exports_created_at", "exports", ["created_at"])
    op.create_index("ix_exports_dimension", "exports", ["dimension"])
    op.create_index("ix_exports_expires_at", "exports", ["expires_at"])
    op.create_index("ix_exports_project_id", "exports", ["project_id"])
    op.create_index("ix_exports_scan_id", "exports", ["scan_id"])
    op.create_index("ix_exports_status", "exports", ["status"])
    op.create_index("ix_exports_target_id", "exports", ["target_id"])
    op.create_table(
        "http_assets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("url", sa.VARCHAR(length=2000), nullable=False),
        sa.Column("host", sa.VARCHAR(length=500), nullable=False),
        sa.Column("port", sa.INTEGER(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "scheme",
            sa.VARCHAR(length=8),
            server_default=sa.text("'https'::character varying"),
            nullable=False,
        ),
        sa.Column("status_code", sa.INTEGER(), nullable=True),
        sa.Column("title", sa.VARCHAR(length=1000), nullable=True),
        sa.Column("webserver", sa.VARCHAR(length=255), nullable=True),
        sa.Column("content_length", sa.INTEGER(), nullable=True),
        sa.Column("content_type", sa.VARCHAR(length=255), nullable=True),
        sa.Column("location", sa.VARCHAR(length=2000), nullable=True),
        sa.Column(
            "tech",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column("ip", sa.VARCHAR(length=45), nullable=True),
        sa.Column("cname", sa.VARCHAR(length=500), nullable=True),
        sa.Column("asn", sa.BIGINT(), nullable=True),
        sa.Column("asn_org", sa.VARCHAR(length=255), nullable=True),
        sa.Column(
            "is_cdn", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("cdn_name", sa.VARCHAR(length=100), nullable=True),
        sa.Column("waf", sa.VARCHAR(length=100), nullable=True),
        sa.Column("jarm", sa.VARCHAR(length=64), nullable=True),
        sa.Column("favicon_hash", sa.VARCHAR(length=64), nullable=True),
        sa.Column("content_hash", sa.VARCHAR(length=80), nullable=True),
        sa.Column("tls_issuer", sa.VARCHAR(length=500), nullable=True),
        sa.Column("tls_subject_cn", sa.VARCHAR(length=500), nullable=True),
        sa.Column(
            "tls_sans",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column("tls_not_after", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("tls_self_signed", sa.BOOLEAN(), nullable=True),
        sa.Column("tls_expired", sa.BOOLEAN(), nullable=True),
        sa.Column("tls_version", sa.VARCHAR(length=20), nullable=True),
        sa.Column("screenshot_path", sa.VARCHAR(length=500), nullable=True),
        sa.Column("discovered_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("final_url", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("method", sa.VARCHAR(length=10), nullable=True),
        sa.Column("path", sa.VARCHAR(length=2000), nullable=True),
        sa.Column(
            "chain_status_codes",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column("response_time", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("words", sa.INTEGER(), nullable=True),
        sa.Column("lines", sa.INTEGER(), nullable=True),
        sa.Column(
            "cpe",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column("favicon_path", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("header_hash", sa.VARCHAR(length=80), nullable=True),
        sa.Column(
            "supports_http2",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "supports_pipeline",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "a_records",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column(
            "aaaa_records",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column("cdn_type", sa.VARCHAR(length=20), nullable=True),
        sa.Column("tls_cipher", sa.VARCHAR(length=100), nullable=True),
        sa.Column("tls_subject_dn", sa.VARCHAR(length=1000), nullable=True),
        sa.Column("tls_issuer_cn", sa.VARCHAR(length=500), nullable=True),
        sa.Column("tls_issuer_org", sa.VARCHAR(length=500), nullable=True),
        sa.Column("tls_serial", sa.VARCHAR(length=200), nullable=True),
        sa.Column("tls_fingerprint", sa.VARCHAR(length=80), nullable=True),
        sa.Column("tls_not_before", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("raw_request", sa.TEXT(), nullable=True),
        sa.Column("raw_response_header", sa.TEXT(), nullable=True),
        sa.Column("response_body", sa.TEXT(), nullable=True),
        sa.Column(
            "response_headers",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column("body_preview", sa.VARCHAR(length=512), nullable=True),
        sa.Column(
            "search_tsv",
            postgresql.TSVECTOR(),
            sa.Computed(
                "(setweight(to_tsvector('simple'::regconfig, \"left\"(COALESCE(raw_response_header, ''::text), 20000)), 'A'::\"char\") || setweight(to_tsvector('simple'::regconfig, \"left\"(COALESCE(response_body, ''::text), 100000)), 'B'::\"char\"))",
                persisted=True,
            ),
            nullable=True,
        ),
        sa.Column("software", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "hygiene_issues", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "hygiene_checked", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("not_found", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("screenshot_phash", sa.BIGINT(), nullable=True),
        sa.Column(
            "tracking_ids", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "ai_checked", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("ai_service", sa.VARCHAR(length=64), nullable=True),
        sa.Column("ai_category", sa.VARCHAR(length=32), nullable=True),
        sa.Column("ai_endpoint", sa.VARCHAR(length=500), nullable=True),
        sa.Column("ai_models", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="http_assets_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="http_assets_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="http_assets_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="http_assets_pkey"),
        sa.UniqueConstraint(
            "scan_id",
            "url",
            name="uq_httpasset_scan_url",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index(
        "ix_http_assets_ai_models_gin",
        "http_assets",
        [sa.literal_column("(ai_models::jsonb)")],
        postgresql_using="gin",
        postgresql_where="(ai_models IS NOT NULL)",
    )
    op.create_index(
        "ix_http_assets_ai_service",
        "http_assets",
        ["scan_id", "ai_service"],
        postgresql_where="(ai_service IS NOT NULL)",
    )
    op.create_index(
        "ix_http_assets_cert_cn_trgm",
        "http_assets",
        ["tls_subject_cn"],
        postgresql_ops={"tls_subject_cn": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index(
        "ix_http_assets_cert_issuer_trgm",
        "http_assets",
        ["tls_issuer"],
        postgresql_ops={"tls_issuer": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index("ix_http_assets_host", "http_assets", ["host"])
    op.create_index("ix_http_assets_ip", "http_assets", ["ip"])
    op.create_index("ix_http_assets_is_cdn", "http_assets", ["is_cdn"])
    op.create_index(
        "ix_http_assets_issuer_cn_trgm",
        "http_assets",
        ["tls_issuer_cn"],
        postgresql_ops={"tls_issuer_cn": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index(
        "ix_http_assets_issuer_org_trgm",
        "http_assets",
        ["tls_issuer_org"],
        postgresql_ops={"tls_issuer_org": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index(
        "ix_http_assets_location_trgm",
        "http_assets",
        ["location"],
        postgresql_ops={"location": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index("ix_http_assets_project_id", "http_assets", ["project_id"])
    op.create_index(
        "ix_http_assets_sans_text_trgm",
        "http_assets",
        [sa.literal_column("(tls_sans::text)")],
        postgresql_ops={"(tls_sans::text)": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index(
        "ix_http_assets_scan_fp", "http_assets", ["scan_id", "tls_fingerprint"]
    )
    op.create_index("ix_http_assets_scan_host", "http_assets", ["scan_id", "host"])
    op.create_index("ix_http_assets_scan_id", "http_assets", ["scan_id"])
    op.create_index(
        "ix_http_assets_screenshot",
        "http_assets",
        ["scan_id"],
        postgresql_where="(screenshot_path IS NOT NULL)",
    )
    op.create_index(
        "ix_http_assets_screenshot_phash",
        "http_assets",
        ["scan_id", "screenshot_phash"],
        postgresql_where="(screenshot_phash IS NOT NULL)",
    )
    op.create_index(
        "ix_http_assets_search_tsv",
        "http_assets",
        ["search_tsv"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_http_assets_software_pending",
        "http_assets",
        ["scan_id"],
        postgresql_where="(software IS NULL)",
    )
    op.create_index("ix_http_assets_status_code", "http_assets", ["status_code"])
    op.create_index("ix_http_assets_target_id", "http_assets", ["target_id"])
    op.create_index(
        "ix_http_assets_title_trgm",
        "http_assets",
        ["title"],
        postgresql_ops={"title": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index(
        "ix_http_assets_tracking_gin",
        "http_assets",
        [sa.literal_column("(tracking_ids::jsonb)")],
        postgresql_using="gin",
    )
    op.create_table(
        "intel_signals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("vulnerability_id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.VARCHAR(length=32), nullable=False),
        sa.Column("weight", sa.INTEGER(), nullable=False),
        sa.Column("reason", sa.VARCHAR(length=500), nullable=False),
        sa.Column("evidence", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="intel_signals_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="intel_signals_pkey"),
        sa.UniqueConstraint(
            "vulnerability_id",
            "kind",
            name="uq_intel_signal_vuln_kind",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_intel_signals_kind", "intel_signals", ["kind"])
    op.create_index("ix_intel_signals_scan_id", "intel_signals", ["scan_id"])
    op.create_index(
        "ix_intel_signals_vulnerability_id", "intel_signals", ["vulnerability_id"]
    )
    op.create_table(
        "ip_addresses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("ip", sa.VARCHAR(length=45), nullable=False),
        sa.Column("version", sa.INTEGER(), server_default=sa.text("4"), nullable=False),
        sa.Column("source", sa.VARCHAR(length=30), nullable=False),
        sa.Column(
            "ptr_hostnames",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column("asn", sa.BIGINT(), nullable=True),
        sa.Column("asn_org", sa.VARCHAR(length=255), nullable=True),
        sa.Column("prefix", sa.VARCHAR(length=64), nullable=True),
        sa.Column("country", sa.VARCHAR(length=10), nullable=True),
        sa.Column(
            "is_cdn", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("cdn_name", sa.VARCHAR(length=100), nullable=True),
        sa.Column("is_alive", sa.BOOLEAN(), nullable=True),
        sa.Column("discovered_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("cdn_type", sa.VARCHAR(length=20), nullable=True),
        sa.Column("scan_policy", sa.VARCHAR(length=16), nullable=True),
        sa.Column("scan_policy_reason", sa.VARCHAR(length=32), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="ip_addresses_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="ip_addresses_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="ip_addresses_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="ip_addresses_pkey"),
        sa.UniqueConstraint(
            "scan_id",
            "ip",
            name="uq_ipaddress_scan_ip",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_ip_addresses_asn", "ip_addresses", ["asn"])
    op.create_index("ix_ip_addresses_ip", "ip_addresses", ["ip"])
    op.create_index("ix_ip_addresses_is_cdn", "ip_addresses", ["is_cdn"])
    op.create_index("ix_ip_addresses_project_id", "ip_addresses", ["project_id"])
    op.create_index(
        "ix_ip_addresses_scan_discovered", "ip_addresses", ["scan_id", "discovered_at"]
    )
    op.create_index("ix_ip_addresses_scan_id", "ip_addresses", ["scan_id"])
    op.create_index("ix_ip_addresses_scan_policy", "ip_addresses", ["scan_policy"])
    op.create_index(
        "ix_ip_addresses_target_discovered",
        "ip_addresses",
        ["target_id", "discovered_at"],
    )
    op.create_index("ix_ip_addresses_target_id", "ip_addresses", ["target_id"])
    op.create_index(
        "ix_ip_addresses_target_key_discovered",
        "ip_addresses",
        ["target_id", "ip", "discovered_at"],
    )
    op.create_table(
        "lookalike_domains",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("apex", sa.VARCHAR(length=253), nullable=False),
        sa.Column("domain", sa.VARCHAR(length=253), nullable=False),
        sa.Column("display", sa.VARCHAR(length=253), nullable=False),
        sa.Column("technique", sa.VARCHAR(length=32), nullable=False),
        sa.Column("verdict", sa.VARCHAR(length=16), nullable=False),
        sa.Column("link_reason", sa.VARCHAR(length=16), nullable=True),
        sa.Column("a", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("aaaa", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("mx", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("ns", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "parked", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("http_status", sa.INTEGER(), nullable=True),
        sa.Column("final_url", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("title", sa.VARCHAR(length=300), nullable=True),
        sa.Column("similarity", sa.INTEGER(), nullable=True),
        sa.Column("registered_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("registrar", sa.VARCHAR(length=200), nullable=True),
        sa.Column("first_seen", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("discovered_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="lookalike_domains_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="lookalike_domains_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="lookalike_domains_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="lookalike_domains_pkey"),
        sa.UniqueConstraint(
            "scan_id",
            "domain",
            name="uq_lookalike_domains_scan_domain",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_lookalike_domains_domain", "lookalike_domains", ["domain"])
    op.create_index(
        "ix_lookalike_domains_project_id", "lookalike_domains", ["project_id"]
    )
    op.create_index(
        "ix_lookalike_domains_scan_discovered",
        "lookalike_domains",
        ["scan_id", "discovered_at"],
    )
    op.create_index("ix_lookalike_domains_scan_id", "lookalike_domains", ["scan_id"])
    op.create_index(
        "ix_lookalike_domains_target_discovered",
        "lookalike_domains",
        ["target_id", "discovered_at"],
    )
    op.create_index(
        "ix_lookalike_domains_target_id", "lookalike_domains", ["target_id"]
    )
    op.create_index("ix_lookalike_domains_verdict", "lookalike_domains", ["verdict"])
    op.create_table(
        "notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=True),
        sa.Column("dimension", sa.VARCHAR(length=32), nullable=True),
        sa.Column("asset_key", sa.VARCHAR(length=500), nullable=True),
        sa.Column("asset_label", sa.VARCHAR(length=500), nullable=True),
        sa.Column("title", sa.VARCHAR(length=200), nullable=True),
        sa.Column("body", sa.VARCHAR(length=20000), nullable=False),
        sa.Column(
            "status",
            sa.VARCHAR(length=16),
            server_default=sa.text("'open'::character varying"),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("triage_state", sa.VARCHAR(length=20), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="notes_created_by_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="notes_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"], ["scans.id"], name="notes_scan_id_fkey", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="notes_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="notes_pkey"),
    )
    op.create_index("ix_notes_anchor", "notes", ["dimension", "asset_key"])
    op.create_index(
        "ix_notes_body_trgm",
        "notes",
        ["body"],
        postgresql_ops={"body": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index("ix_notes_created_at", "notes", ["created_at"])
    op.create_index("ix_notes_project_id", "notes", ["project_id"])
    op.create_index("ix_notes_scan_id", "notes", ["scan_id"])
    op.create_index("ix_notes_status", "notes", ["status"])
    op.create_index("ix_notes_tags", "notes", ["tags"], postgresql_using="gin")
    op.create_index("ix_notes_target_id", "notes", ["target_id"])
    op.create_index(
        "ix_notes_title_trgm",
        "notes",
        ["title"],
        postgresql_ops={"title": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index(
        "ix_notes_triage",
        "notes",
        [
            "target_id",
            "asset_key",
            "triage_state",
            sa.literal_column("created_at DESC"),
        ],
        postgresql_where="(triage_state IS NOT NULL)",
    )
    op.create_table(
        "ports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("ip", sa.VARCHAR(length=45), nullable=False),
        sa.Column("number", sa.INTEGER(), nullable=False),
        sa.Column(
            "protocol",
            sa.VARCHAR(length=8),
            server_default=sa.text("'tcp'::character varying"),
            nullable=False,
        ),
        sa.Column(
            "state",
            sa.VARCHAR(length=16),
            server_default=sa.text("'open'::character varying"),
            nullable=False,
        ),
        sa.Column("service_name", sa.VARCHAR(length=64), nullable=True),
        sa.Column("source", sa.VARCHAR(length=30), nullable=False),
        sa.Column("discovered_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "service_class",
            sa.VARCHAR(length=16),
            server_default=sa.text("'other'::character varying"),
            nullable=False,
        ),
        sa.Column(
            "is_http", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("tls", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False),
        sa.Column("product", sa.VARCHAR(length=200), nullable=True),
        sa.Column("version", sa.VARCHAR(length=100), nullable=True),
        sa.Column("banner", sa.VARCHAR(length=1000), nullable=True),
        sa.Column(
            "cpe",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="ports_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"], ["scans.id"], name="ports_scan_id_fkey", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="ports_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="ports_pkey"),
        sa.UniqueConstraint(
            "scan_id",
            "ip",
            "number",
            "protocol",
            name="uq_port_scan_ip_num_proto",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_ports_ip", "ports", ["ip"])
    op.create_index("ix_ports_is_http", "ports", ["is_http"])
    op.create_index("ix_ports_number", "ports", ["number"])
    op.create_index("ix_ports_project_id", "ports", ["project_id"])
    op.create_index("ix_ports_scan_discovered", "ports", ["scan_id", "discovered_at"])
    op.create_index("ix_ports_scan_id", "ports", ["scan_id"])
    op.create_index("ix_ports_scan_ip", "ports", ["scan_id", "ip"])
    op.create_index("ix_ports_service_class", "ports", ["service_class"])
    op.create_index("ix_ports_service_name", "ports", ["service_name"])
    op.create_index(
        "ix_ports_target_discovered", "ports", ["target_id", "discovered_at"]
    )
    op.create_index("ix_ports_target_id", "ports", ["target_id"])
    op.create_index(
        "ix_ports_target_key_discovered",
        "ports",
        ["target_id", "ip", "number", "discovered_at"],
    )
    op.create_table(
        "scan_activities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=100), nullable=False),
        sa.Column("title", sa.VARCHAR(length=200), nullable=False),
        sa.Column("status", sa.VARCHAR(), nullable=False),
        sa.Column("celery_task_id", sa.VARCHAR(length=100), nullable=True),
        sa.Column("error", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("traceback", sa.TEXT(), nullable=True),
        sa.Column("result", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="scan_activities_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="scan_activities_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="scan_activities_pkey"),
    )
    op.create_index("ix_scan_activities_name", "scan_activities", ["name"])
    op.create_index("ix_scan_activities_project_id", "scan_activities", ["project_id"])
    op.create_index("ix_scan_activities_scan_id", "scan_activities", ["scan_id"])
    op.create_index("ix_scan_activities_status", "scan_activities", ["status"])
    op.create_table(
        "scan_deltas",
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("dimension", sa.VARCHAR(length=32), nullable=False),
        sa.Column("history_rev", sa.BIGINT(), nullable=False),
        sa.Column("first_seen", sa.INTEGER(), nullable=False),
        sa.Column("rows", sa.INTEGER(), nullable=False),
        sa.Column("first_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="scan_deltas_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("scan_id", "dimension", name="scan_deltas_pkey"),
    )
    op.create_table(
        "scan_retired",
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("prev_scan_id", sa.UUID(), nullable=False),
        sa.Column("dimension", sa.VARCHAR(length=32), nullable=False),
        sa.Column("rows_rev", sa.BIGINT(), nullable=False),
        sa.Column("prev_rows_rev", sa.BIGINT(), nullable=False),
        sa.Column("retired", sa.INTEGER(), nullable=False),
        sa.ForeignKeyConstraint(
            ["prev_scan_id"],
            ["scans.id"],
            name="scan_retired_prev_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="scan_retired_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "scan_id", "prev_scan_id", "dimension", name="scan_retired_pkey"
        ),
    )
    op.create_index("ix_scan_retired_prev_scan_id", "scan_retired", ["prev_scan_id"])
    op.create_table(
        "scan_revisions",
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("dimension", sa.VARCHAR(length=32), nullable=False),
        sa.Column(
            "rows_rev",
            sa.BIGINT(),
            server_default=sa.text("'0'::bigint"),
            nullable=False,
        ),
        sa.Column(
            "history_rev",
            sa.BIGINT(),
            server_default=sa.text("'0'::bigint"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="scan_revisions_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("scan_id", "dimension", name="scan_revisions_pkey"),
    )
    op.create_table(
        "scan_surface_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("class", sa.VARCHAR(length=16), nullable=False),
        sa.Column("value", sa.VARCHAR(length=2000), nullable=False),
        sa.Column("host", sa.VARCHAR(length=500), nullable=True),
        sa.Column("port", sa.INTEGER(), nullable=True),
        sa.Column("scheme", sa.VARCHAR(length=8), nullable=True),
        sa.Column("http_asset_id", sa.UUID(), nullable=True),
        sa.Column("endpoint_id", sa.UUID(), nullable=True),
        sa.Column("port_id", sa.UUID(), nullable=True),
        sa.Column("subdomain_id", sa.UUID(), nullable=True),
        sa.Column("cluster_id", sa.UUID(), nullable=True),
        sa.Column("representative_id", sa.UUID(), nullable=True),
        sa.Column(
            "cluster_signals", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("members", sa.INTEGER(), server_default=sa.text("1"), nullable=False),
        sa.Column("drop_reason", sa.VARCHAR(length=32), nullable=True),
        sa.Column(
            "rank",
            sa.DOUBLE_PRECISION(precision=53),
            server_default=sa.text("'0'::double precision"),
            nullable=False,
        ),
        sa.Column("batch", sa.INTEGER(), nullable=True),
        sa.Column(
            "guarded", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("tags", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "unmapped_tech", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "tiers_planned", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("tiers_done", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("state", sa.VARCHAR(length=16), nullable=False),
        sa.Column("note", sa.VARCHAR(length=500), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="scan_surface_items_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="scan_surface_items_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="scan_surface_items_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="scan_surface_items_pkey"),
    )
    op.create_index(
        "ix_scan_surface_items_cluster_id", "scan_surface_items", ["cluster_id"]
    )
    op.create_index(
        "ix_scan_surface_items_project_id", "scan_surface_items", ["project_id"]
    )
    op.create_index(
        "ix_scan_surface_items_representative_id",
        "scan_surface_items",
        ["representative_id"],
    )
    op.create_index("ix_scan_surface_items_scan_id", "scan_surface_items", ["scan_id"])
    op.create_index(
        "ix_scan_surface_items_target_id", "scan_surface_items", ["target_id"]
    )
    op.create_index(
        "ix_scan_surface_scan_asset", "scan_surface_items", ["scan_id", "http_asset_id"]
    )
    op.create_index(
        "ix_scan_surface_scan_class", "scan_surface_items", ["scan_id", "class"]
    )
    op.create_index(
        "ix_scan_surface_target_value", "scan_surface_items", ["target_id", "value"]
    )
    op.create_table(
        "secret_coverage",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("source", sa.VARCHAR(length=24), nullable=False),
        sa.Column("status", sa.VARCHAR(length=16), nullable=False),
        sa.Column(
            "documents_total", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "documents_read", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "bytes_read",
            sa.BIGINT(),
            server_default=sa.text("'0'::bigint"),
            nullable=False,
        ),
        sa.Column(
            "truncated", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("skipped", sa.INTEGER(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "detectors", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("matches", sa.INTEGER(), server_default=sa.text("0"), nullable=False),
        sa.Column("secrets", sa.INTEGER(), server_default=sa.text("0"), nullable=False),
        sa.Column("dropped", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("error", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ended_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="secret_coverage_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="secret_coverage_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="secret_coverage_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="secret_coverage_pkey"),
        sa.UniqueConstraint(
            "scan_id",
            "source",
            name="uq_secret_coverage_scan_source",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_secret_coverage_project_id", "secret_coverage", ["project_id"])
    op.create_index("ix_secret_coverage_scan_id", "secret_coverage", ["scan_id"])
    op.create_index("ix_secret_coverage_target_id", "secret_coverage", ["target_id"])
    op.create_table(
        "secrets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("fingerprint", sa.VARCHAR(length=64), nullable=False),
        sa.Column("kind", sa.VARCHAR(length=40), nullable=False),
        sa.Column("group", sa.VARCHAR(length=24), nullable=False),
        sa.Column(
            "vendor",
            sa.VARCHAR(length=60),
            server_default=sa.text("''::character varying"),
            nullable=False,
        ),
        sa.Column("state", sa.VARCHAR(length=16), nullable=False),
        sa.Column(
            "is_secret", sa.BOOLEAN(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("value", sa.TEXT(), nullable=False),
        sa.Column("subject", sa.VARCHAR(length=500), nullable=True),
        sa.Column("meta", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("host", sa.VARCHAR(length=500), nullable=False),
        sa.Column("url", sa.VARCHAR(length=2000), nullable=False),
        sa.Column("http_asset_id", sa.UUID(), nullable=True),
        sa.Column("source", sa.VARCHAR(length=16), nullable=False),
        sa.Column("context", sa.TEXT(), nullable=True),
        sa.Column(
            "sightings", sa.INTEGER(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column("hosts", sa.INTEGER(), server_default=sa.text("1"), nullable=False),
        sa.Column("discovered_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="secrets_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"], ["scans.id"], name="secrets_scan_id_fkey", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="secrets_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="secrets_pkey"),
        sa.UniqueConstraint(
            "scan_id",
            "fingerprint",
            name="uq_secret_scan_fingerprint",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_secrets_discovered_at", "secrets", ["discovered_at"])
    op.create_index("ix_secrets_fingerprint", "secrets", ["fingerprint"])
    op.create_index("ix_secrets_group", "secrets", ["group"])
    op.create_index("ix_secrets_host", "secrets", ["host"])
    op.create_index("ix_secrets_http_asset_id", "secrets", ["http_asset_id"])
    op.create_index("ix_secrets_kind", "secrets", ["kind"])
    op.create_index("ix_secrets_project_id", "secrets", ["project_id"])
    op.create_index(
        "ix_secrets_scan_discovered", "secrets", ["scan_id", "discovered_at"]
    )
    op.create_index("ix_secrets_scan_id", "secrets", ["scan_id"])
    op.create_index("ix_secrets_scan_kind", "secrets", ["scan_id", "kind"])
    op.create_index("ix_secrets_scan_state", "secrets", ["scan_id", "state"])
    op.create_index("ix_secrets_state", "secrets", ["state"])
    op.create_index("ix_secrets_subject", "secrets", ["subject"])
    op.create_index(
        "ix_secrets_target_discovered", "secrets", ["target_id", "discovered_at"]
    )
    op.create_index("ix_secrets_target_id", "secrets", ["target_id"])
    op.create_table(
        "software_cves",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("fingerprint", sa.VARCHAR(length=64), nullable=False),
        sa.Column("cve", sa.VARCHAR(length=30), nullable=False),
        sa.Column("name", sa.VARCHAR(length=120), nullable=False),
        sa.Column("version", sa.VARCHAR(length=64), nullable=False),
        sa.Column("vendor", sa.VARCHAR(length=200), nullable=False),
        sa.Column("product", sa.VARCHAR(length=200), nullable=False),
        sa.Column("cpe", sa.VARCHAR(length=300), nullable=False),
        sa.Column("version_source", sa.VARCHAR(length=16), nullable=False),
        sa.Column("severity", sa.VARCHAR(length=16), nullable=False),
        sa.Column("cvss_score", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("epss_score", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("epss_percentile", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column(
            "is_kev", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "kev_ransomware",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("kev_due_date", sa.DATE(), nullable=True),
        sa.Column(
            "exploit_score", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "intel_kinds",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column("confidence", sa.VARCHAR(length=16), nullable=False),
        sa.Column(
            "caveats",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column("host", sa.VARCHAR(length=500), nullable=True),
        sa.Column("ip", sa.VARCHAR(length=45), nullable=True),
        sa.Column("port", sa.INTEGER(), nullable=True),
        sa.Column("url", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("http_asset_id", sa.UUID(), nullable=True),
        sa.Column("port_id", sa.UUID(), nullable=True),
        sa.Column("discovered_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "evidence",
            sa.VARCHAR(length=16),
            server_default=sa.text("'inferred'::character varying"),
            nullable=False,
        ),
        sa.Column("fixed_in", sa.VARCHAR(length=64), nullable=True),
        sa.Column("fixed_in_assets", sa.INTEGER(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="software_cves_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="software_cves_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="software_cves_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="software_cves_pkey"),
        sa.UniqueConstraint(
            "scan_id",
            "fingerprint",
            name="uq_software_scan_fingerprint",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_software_cves_cve", "software_cves", ["cve"])
    op.create_index(
        "ix_software_cves_discovered_at", "software_cves", ["discovered_at"]
    )
    op.create_index(
        "ix_software_cves_exploit_score", "software_cves", ["exploit_score"]
    )
    op.create_index("ix_software_cves_fingerprint", "software_cves", ["fingerprint"])
    op.create_index("ix_software_cves_host", "software_cves", ["host"])
    op.create_index(
        "ix_software_cves_http_asset_id", "software_cves", ["http_asset_id"]
    )
    op.create_index("ix_software_cves_ip", "software_cves", ["ip"])
    op.create_index("ix_software_cves_is_kev", "software_cves", ["is_kev"])
    op.create_index("ix_software_cves_port_id", "software_cves", ["port_id"])
    op.create_index("ix_software_cves_project_id", "software_cves", ["project_id"])
    op.create_index(
        "ix_software_cves_scan_discovered",
        "software_cves",
        ["scan_id", "discovered_at"],
    )
    op.create_index("ix_software_cves_scan_id", "software_cves", ["scan_id"])
    op.create_index(
        "ix_software_cves_target_discovered",
        "software_cves",
        ["target_id", "discovered_at"],
    )
    op.create_index("ix_software_cves_target_id", "software_cves", ["target_id"])
    op.create_index(
        "ix_software_cves_target_key_discovered",
        "software_cves",
        ["target_id", "fingerprint", "discovered_at"],
    )
    op.create_table(
        "subdomains",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=500), nullable=False),
        sa.Column("sources", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "resolved_ips", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("cname", sa.VARCHAR(length=500), nullable=True),
        sa.Column("is_active", sa.BOOLEAN(), nullable=False),
        sa.Column("is_wildcard", sa.BOOLEAN(), nullable=False),
        sa.Column("discovered_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "is_excluded", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "is_important",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("http_url", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("http_status", sa.INTEGER(), nullable=True),
        sa.Column("page_title", sa.VARCHAR(length=1000), nullable=True),
        sa.Column("content_type", sa.VARCHAR(length=255), nullable=True),
        sa.Column("content_length", sa.INTEGER(), nullable=True),
        sa.Column("response_time", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("webserver", sa.VARCHAR(length=255), nullable=True),
        sa.Column(
            "tech",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column(
            "is_cdn", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("cdn_name", sa.VARCHAR(length=100), nullable=True),
        sa.Column("screenshot_path", sa.VARCHAR(length=500), nullable=True),
        sa.Column("final_url", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("waf", sa.VARCHAR(length=100), nullable=True),
        sa.Column("asn", sa.BIGINT(), nullable=True),
        sa.Column("asn_org", sa.VARCHAR(length=255), nullable=True),
        sa.Column("favicon_hash", sa.VARCHAR(length=64), nullable=True),
        sa.Column("tls_not_after", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("tls_expired", sa.BOOLEAN(), nullable=True),
        sa.Column("tls_self_signed", sa.BOOLEAN(), nullable=True),
        sa.Column(
            "interest_score", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("interest_band", sa.VARCHAR(length=16), nullable=True),
        sa.Column(
            "interest_kinds",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column("tls_checked_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "hygiene_issues", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "hygiene_checked", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("screenshot_phash", sa.BIGINT(), nullable=True),
        sa.Column(
            "posture_issues", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "posture_checked", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("ai_services", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint(
            "name::text = lower(name::text)", name="ck_subdomains_name_lower"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="subdomains_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="subdomains_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="subdomains_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="subdomains_pkey"),
        sa.UniqueConstraint(
            "scan_id",
            "name",
            name="uq_subdomain_scan_name",
            postgresql_nulls_not_distinct=False,
        ),
        postgresql_ignore_search_path=False,
    )
    op.create_index(
        "ix_subdomains_ai_services_gin",
        "subdomains",
        [sa.literal_column("(ai_services::jsonb)")],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_subdomains_cdn_trgm",
        "subdomains",
        ["cdn_name"],
        postgresql_ops={"cdn_name": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index(
        "ix_subdomains_cname_trgm",
        "subdomains",
        ["cname"],
        postgresql_ops={"cname": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index(
        "ix_subdomains_final_url_trgm",
        "subdomains",
        ["final_url"],
        postgresql_ops={"final_url": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index("ix_subdomains_http_status", "subdomains", ["http_status"])
    op.create_index(
        "ix_subdomains_hygiene_gin",
        "subdomains",
        [sa.literal_column("(hygiene_issues::jsonb)")],
        postgresql_using="gin",
    )
    op.create_index("ix_subdomains_interest_band", "subdomains", ["interest_band"])
    op.create_index("ix_subdomains_interest_score", "subdomains", ["interest_score"])
    op.create_index(
        "ix_subdomains_ips_gin",
        "subdomains",
        [sa.literal_column("(resolved_ips::jsonb)")],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_subdomains_ips_text_trgm",
        "subdomains",
        [sa.literal_column("(resolved_ips::text)")],
        postgresql_ops={"(resolved_ips::text)": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index("ix_subdomains_is_active", "subdomains", ["is_active"])
    op.create_index("ix_subdomains_is_excluded", "subdomains", ["is_excluded"])
    op.create_index("ix_subdomains_name", "subdomains", ["name"])
    op.create_index(
        "ix_subdomains_name_trgm",
        "subdomains",
        ["name"],
        postgresql_ops={"name": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index(
        "ix_subdomains_org_trgm",
        "subdomains",
        ["asn_org"],
        postgresql_ops={"asn_org": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index(
        "ix_subdomains_posture_gin",
        "subdomains",
        [sa.literal_column("(posture_issues::jsonb)")],
        postgresql_using="gin",
    )
    op.create_index("ix_subdomains_project_id", "subdomains", ["project_id"])
    op.create_index("ix_subdomains_scan_asn", "subdomains", ["scan_id", "asn"])
    op.create_index("ix_subdomains_scan_cname", "subdomains", ["scan_id", "cname"])
    op.create_index(
        "ix_subdomains_scan_discovered", "subdomains", ["scan_id", "discovered_at"]
    )
    op.create_index(
        "ix_subdomains_scan_favicon", "subdomains", ["scan_id", "favicon_hash"]
    )
    op.create_index("ix_subdomains_scan_id", "subdomains", ["scan_id"])
    op.create_index(
        "ix_subdomains_scan_status_name",
        "subdomains",
        ["scan_id", "http_status", "name"],
    )
    op.create_index(
        "ix_subdomains_scan_tls_after", "subdomains", ["scan_id", "tls_not_after"]
    )
    op.create_index(
        "ix_subdomains_screenshot",
        "subdomains",
        ["scan_id"],
        postgresql_where="(screenshot_path IS NOT NULL)",
    )
    op.create_index(
        "ix_subdomains_screenshot_phash",
        "subdomains",
        ["scan_id", "screenshot_phash"],
        postgresql_where="(screenshot_phash IS NOT NULL)",
    )
    op.create_index(
        "ix_subdomains_sources_gin",
        "subdomains",
        [sa.literal_column("(sources::jsonb)")],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_subdomains_sources_text_trgm",
        "subdomains",
        [sa.literal_column("(sources::text)")],
        postgresql_ops={"(sources::text)": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index(
        "ix_subdomains_target_discovered", "subdomains", ["target_id", "discovered_at"]
    )
    op.create_index("ix_subdomains_target_id", "subdomains", ["target_id"])
    op.create_index(
        "ix_subdomains_target_name_discovered",
        "subdomains",
        ["target_id", "name", "discovered_at"],
    )
    op.create_index(
        "ix_subdomains_tech_gin",
        "subdomains",
        [sa.literal_column("(tech::jsonb)")],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_subdomains_tech_text_trgm",
        "subdomains",
        [sa.literal_column("(tech::text)")],
        postgresql_ops={"(tech::text)": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index(
        "ix_subdomains_title_trgm",
        "subdomains",
        ["page_title"],
        postgresql_ops={"page_title": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index(
        "ix_subdomains_tls_recheck",
        "subdomains",
        ["tls_not_after", "tls_checked_at"],
        postgresql_where="(tls_not_after IS NOT NULL)",
    )
    op.create_index(
        "ix_subdomains_waf_trgm",
        "subdomains",
        ["waf"],
        postgresql_ops={"waf": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index(
        "ix_subdomains_webserver_trgm",
        "subdomains",
        ["webserver"],
        postgresql_ops={"webserver": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_table(
        "tracked_issue_comments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("issue_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.VARCHAR(length=24), nullable=False),
        sa.Column("body", sa.TEXT(), nullable=False),
        sa.Column("state", sa.VARCHAR(length=16), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=True),
        sa.Column("attempts", sa.INTEGER(), nullable=False),
        sa.Column("error", sa.VARCHAR(length=500), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("sent_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["tracked_issues.id"],
            name="tracked_issue_comments_issue_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="tracked_issue_comments_pkey"),
    )
    op.create_index(
        "ix_tracked_issue_comments_issue_id", "tracked_issue_comments", ["issue_id"]
    )
    op.create_index(
        "ix_tracked_issue_comments_state", "tracked_issue_comments", ["state"]
    )
    op.create_table(
        "tracked_issue_findings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("issue_id", sa.UUID(), nullable=False),
        sa.Column("tracker_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("fingerprint", sa.VARCHAR(length=64), nullable=False),
        sa.Column("matched_at", sa.VARCHAR(length=2000), nullable=False),
        sa.Column("severity", sa.VARCHAR(length=16), nullable=False),
        sa.Column("present", sa.BOOLEAN(), nullable=False),
        sa.Column("announced", sa.BOOLEAN(), nullable=False),
        sa.Column("added_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["tracked_issues.id"],
            name="tracked_issue_findings_issue_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="tracked_issue_findings_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tracker_id"],
            ["issue_trackers.id"],
            name="tracked_issue_findings_tracker_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="tracked_issue_findings_pkey"),
        sa.UniqueConstraint(
            "tracker_id",
            "target_id",
            "fingerprint",
            name="uq_tracked_finding",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index(
        "ix_tracked_finding_target_fp",
        "tracked_issue_findings",
        ["target_id", "fingerprint"],
    )
    op.create_index(
        "ix_tracked_issue_findings_issue_id", "tracked_issue_findings", ["issue_id"]
    )
    op.create_table(
        "tripwire_marks",
        sa.Column("tripwire_id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("key", sa.VARCHAR(length=600), nullable=False),
        sa.Column("marked_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="tripwire_marks_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tripwire_id"],
            ["tripwires.id"],
            name="tripwire_marks_tripwire_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "tripwire_id", "scan_id", "key", name="tripwire_marks_pkey"
        ),
    )
    op.create_index("ix_tripwire_marks_scan_id", "tripwire_marks", ["scan_id"])
    op.create_table(
        "tripwire_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tripwire_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.VARCHAR(length=16), nullable=False),
        sa.Column("matched", sa.INTEGER(), nullable=False),
        sa.Column("fired", sa.INTEGER(), nullable=False),
        sa.Column("rows", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("outcomes", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("detail", sa.VARCHAR(length=500), nullable=True),
        sa.Column("checked_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("fired_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="tripwire_runs_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="tripwire_runs_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="tripwire_runs_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tripwire_id"],
            ["tripwires.id"],
            name="tripwire_runs_tripwire_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="tripwire_runs_pkey"),
        sa.UniqueConstraint(
            "tripwire_id",
            "scan_id",
            name="uq_tripwire_run",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index(
        "ix_tripwire_runs_project_fired", "tripwire_runs", ["project_id", "fired_at"]
    )
    op.create_index("ix_tripwire_runs_project_id", "tripwire_runs", ["project_id"])
    op.create_index("ix_tripwire_runs_scan_id", "tripwire_runs", ["scan_id"])
    op.create_index("ix_tripwire_runs_status", "tripwire_runs", ["status"])
    op.create_index("ix_tripwire_runs_target_id", "tripwire_runs", ["target_id"])
    op.create_index(
        "ix_tripwire_runs_tripwire_checked",
        "tripwire_runs",
        ["tripwire_id", "checked_at"],
    )
    op.create_index("ix_tripwire_runs_tripwire_id", "tripwire_runs", ["tripwire_id"])
    op.create_table(
        "vulnerabilities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("fingerprint", sa.VARCHAR(length=64), nullable=False),
        sa.Column(
            "scanner",
            sa.VARCHAR(length=32),
            server_default=sa.text("'nuclei'::character varying"),
            nullable=False,
        ),
        sa.Column("template_id", sa.VARCHAR(length=200), nullable=False),
        sa.Column("template_name", sa.VARCHAR(length=500), nullable=False),
        sa.Column("template_path", sa.VARCHAR(length=500), nullable=True),
        sa.Column("template_url", sa.VARCHAR(length=1000), nullable=True),
        sa.Column(
            "severity",
            sa.VARCHAR(length=16),
            server_default=sa.text("'unknown'::character varying"),
            nullable=False,
        ),
        sa.Column(
            "protocol",
            sa.VARCHAR(length=16),
            server_default=sa.text("'other'::character varying"),
            nullable=False,
        ),
        sa.Column("matcher_name", sa.VARCHAR(length=200), nullable=True),
        sa.Column("extractor_name", sa.VARCHAR(length=200), nullable=True),
        sa.Column(
            "extracted_results", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("impact", sa.TEXT(), nullable=True),
        sa.Column("remediation", sa.TEXT(), nullable=True),
        sa.Column("references", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("tags", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("authors", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("cve_ids", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("cwe_ids", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("cvss_metrics", sa.VARCHAR(length=200), nullable=True),
        sa.Column("cvss_score", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("epss_score", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("epss_percentile", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("cpe", sa.VARCHAR(length=300), nullable=True),
        sa.Column(
            "is_kev", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("extra", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("matched_at", sa.VARCHAR(length=2000), nullable=False),
        sa.Column("host", sa.VARCHAR(length=500), nullable=True),
        sa.Column("ip", sa.VARCHAR(length=45), nullable=True),
        sa.Column("port", sa.INTEGER(), nullable=True),
        sa.Column("scheme", sa.VARCHAR(length=16), nullable=True),
        sa.Column("url", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("path", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("subdomain_id", sa.UUID(), nullable=True),
        sa.Column("http_asset_id", sa.UUID(), nullable=True),
        sa.Column("port_id", sa.UUID(), nullable=True),
        sa.Column("request", sa.TEXT(), nullable=True),
        sa.Column("response", sa.TEXT(), nullable=True),
        sa.Column("curl_command", sa.TEXT(), nullable=True),
        sa.Column(
            "interaction", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("observed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("discovered_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "exploit_score", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "intel_kinds",
            postgresql.JSON(astext_type=sa.Text()),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column(
            "kev_ransomware",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("kev_due_date", sa.DATE(), nullable=True),
        sa.Column("poc_count", sa.INTEGER(), nullable=True),
        sa.Column("template_available", sa.BOOLEAN(), nullable=True),
        sa.Column("intel_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("hackerone_reports", sa.INTEGER(), nullable=True),
        sa.Column(
            "evidence",
            sa.VARCHAR(length=16),
            server_default=sa.text("'observed'::character varying"),
            nullable=False,
        ),
        sa.Column("replayed_from_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="vulnerabilities_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="vulnerabilities_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="vulnerabilities_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="vulnerabilities_pkey"),
        sa.UniqueConstraint(
            "scan_id",
            "fingerprint",
            name="uq_vuln_scan_fingerprint",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index(
        "ix_vulnerabilities_cve_gin",
        "vulnerabilities",
        [sa.literal_column("(cve_ids::jsonb)")],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_vulnerabilities_discovered_at", "vulnerabilities", ["discovered_at"]
    )
    op.create_index("ix_vulnerabilities_evidence", "vulnerabilities", ["evidence"])
    op.create_index(
        "ix_vulnerabilities_exploit_score", "vulnerabilities", ["exploit_score"]
    )
    op.create_index(
        "ix_vulnerabilities_fingerprint", "vulnerabilities", ["fingerprint"]
    )
    op.create_index("ix_vulnerabilities_host", "vulnerabilities", ["host"])
    op.create_index(
        "ix_vulnerabilities_host_trgm",
        "vulnerabilities",
        ["host"],
        postgresql_ops={"host": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index(
        "ix_vulnerabilities_http_asset_id", "vulnerabilities", ["http_asset_id"]
    )
    op.create_index("ix_vulnerabilities_ip", "vulnerabilities", ["ip"])
    op.create_index("ix_vulnerabilities_is_kev", "vulnerabilities", ["is_kev"])
    op.create_index(
        "ix_vulnerabilities_kev_ransomware", "vulnerabilities", ["kev_ransomware"]
    )
    op.create_index(
        "ix_vulnerabilities_matched_trgm",
        "vulnerabilities",
        ["matched_at"],
        postgresql_ops={"matched_at": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index(
        "ix_vulnerabilities_name_trgm",
        "vulnerabilities",
        ["template_name"],
        postgresql_ops={"template_name": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_index("ix_vulnerabilities_port", "vulnerabilities", ["port"])
    op.create_index("ix_vulnerabilities_port_id", "vulnerabilities", ["port_id"])
    op.create_index("ix_vulnerabilities_project_id", "vulnerabilities", ["project_id"])
    op.create_index("ix_vulnerabilities_protocol", "vulnerabilities", ["protocol"])
    op.create_index(
        "ix_vulnerabilities_replayed_from_id",
        "vulnerabilities",
        ["replayed_from_id"],
        postgresql_where="(replayed_from_id IS NOT NULL)",
    )
    op.create_index(
        "ix_vulnerabilities_scan_discovered",
        "vulnerabilities",
        ["scan_id", "discovered_at"],
    )
    op.create_index("ix_vulnerabilities_scan_id", "vulnerabilities", ["scan_id"])
    op.create_index(
        "ix_vulnerabilities_scan_matched", "vulnerabilities", ["scan_id", "matched_at"]
    )
    op.create_index(
        "ix_vulnerabilities_scan_severity",
        "vulnerabilities",
        ["scan_id", "severity", "template_id"],
    )
    op.create_index("ix_vulnerabilities_scanner", "vulnerabilities", ["scanner"])
    op.create_index("ix_vulnerabilities_severity", "vulnerabilities", ["severity"])
    op.create_index(
        "ix_vulnerabilities_subdomain_id", "vulnerabilities", ["subdomain_id"]
    )
    op.create_index(
        "ix_vulnerabilities_tags_gin",
        "vulnerabilities",
        [sa.literal_column("(tags::jsonb)")],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_vulnerabilities_target_discovered",
        "vulnerabilities",
        ["target_id", "discovered_at"],
    )
    op.create_index("ix_vulnerabilities_target_id", "vulnerabilities", ["target_id"])
    op.create_index(
        "ix_vulnerabilities_target_key_discovered",
        "vulnerabilities",
        ["target_id", "fingerprint", "discovered_at"],
    )
    op.create_index(
        "ix_vulnerabilities_template_id", "vulnerabilities", ["template_id"]
    )
    op.create_index(
        "ix_vulnerabilities_template_trgm",
        "vulnerabilities",
        ["template_id"],
        postgresql_ops={"template_id": "gin_trgm_ops"},
        postgresql_using="gin",
    )
    op.create_table(
        "vulnerability_coverage",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column(
            "scanner",
            sa.VARCHAR(length=32),
            server_default=sa.text("'nuclei'::character varying"),
            nullable=False,
        ),
        sa.Column("group", sa.VARCHAR(length=120), nullable=False),
        sa.Column(
            "status",
            sa.VARCHAR(length=16),
            server_default=sa.text("'completed'::character varying"),
            nullable=False,
        ),
        sa.Column("severities", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "template_sets", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("templates_selected", sa.INTEGER(), nullable=True),
        sa.Column("templates_loaded", sa.INTEGER(), nullable=True),
        sa.Column(
            "custom_templates",
            sa.INTEGER(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "hosts_total", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("hosts_scanned", sa.INTEGER(), nullable=True),
        sa.Column(
            "hosts_dropped", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("requests_sent", sa.INTEGER(), nullable=True),
        sa.Column("requests_planned", sa.INTEGER(), nullable=True),
        sa.Column("matched", sa.INTEGER(), nullable=True),
        sa.Column("errors", sa.INTEGER(), nullable=True),
        sa.Column("rate_limit", sa.INTEGER(), nullable=True),
        sa.Column("concurrency", sa.INTEGER(), nullable=True),
        sa.Column("command", sa.TEXT(), nullable=True),
        sa.Column("error", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ended_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("tier", sa.VARCHAR(length=16), nullable=True),
        sa.Column("batch", sa.INTEGER(), nullable=True),
        sa.Column(
            "hosts_covered", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "echo_filtered", sa.INTEGER(), server_default=sa.text("0"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="vulnerability_coverage_project_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="vulnerability_coverage_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="vulnerability_coverage_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="vulnerability_coverage_pkey"),
    )
    op.create_index(
        "ix_vulnerability_coverage_project_id", "vulnerability_coverage", ["project_id"]
    )
    op.create_index(
        "ix_vulnerability_coverage_scan_id", "vulnerability_coverage", ["scan_id"]
    )
    op.create_index(
        "ix_vulnerability_coverage_target_id", "vulnerability_coverage", ["target_id"]
    )
    op.create_table(
        "endpoint_responses",
        sa.Column("endpoint_id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("raw_response_header", sa.TEXT(), nullable=True),
        sa.Column("response_body", sa.TEXT(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["endpoint_id"],
            ["endpoints.id"],
            name="endpoint_responses_endpoint_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="endpoint_responses_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("endpoint_id", name="endpoint_responses_pkey"),
    )
    op.create_index("ix_endpoint_responses_scan_id", "endpoint_responses", ["scan_id"])
    op.create_table(
        "interest_signals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("subdomain_id", sa.UUID(), nullable=False),
        sa.Column("host", sa.VARCHAR(length=500), nullable=False),
        sa.Column("source", sa.VARCHAR(length=16), nullable=False),
        sa.Column("key", sa.VARCHAR(length=120), nullable=False),
        sa.Column("kind", sa.VARCHAR(length=40), nullable=False),
        sa.Column("weight", sa.INTEGER(), nullable=False),
        sa.Column("label", sa.VARCHAR(length=80), nullable=False),
        sa.Column("reason", sa.VARCHAR(length=400), nullable=False),
        sa.Column("evidence", sa.VARCHAR(length=300), nullable=True),
        sa.Column("rule_id", sa.UUID(), nullable=True),
        sa.Column("model", sa.VARCHAR(length=80), nullable=True),
        sa.Column("prompt_version", sa.VARCHAR(length=16), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="interest_signals_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="interest_signals_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["subdomain_id"],
            ["subdomains.id"],
            name="interest_signals_subdomain_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="interest_signals_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="interest_signals_pkey"),
        sa.UniqueConstraint(
            "scan_id",
            "subdomain_id",
            "source",
            "key",
            name="uq_interest_signal",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index("ix_interest_signals_host", "interest_signals", ["host"])
    op.create_index("ix_interest_signals_kind", "interest_signals", ["kind"])
    op.create_index(
        "ix_interest_signals_project_id", "interest_signals", ["project_id"]
    )
    op.create_index("ix_interest_signals_rule_id", "interest_signals", ["rule_id"])
    op.create_index("ix_interest_signals_scan_id", "interest_signals", ["scan_id"])
    op.create_index(
        "ix_interest_signals_scan_score", "interest_signals", ["scan_id", "weight"]
    )
    op.create_index("ix_interest_signals_source", "interest_signals", ["source"])
    op.create_index(
        "ix_interest_signals_subdomain_id", "interest_signals", ["subdomain_id"]
    )
    op.create_index("ix_interest_signals_target_id", "interest_signals", ["target_id"])
    op.create_table(
        "scan_commands",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("activity_id", sa.UUID(), nullable=True),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("tool", sa.VARCHAR(length=100), nullable=False),
        sa.Column("command", sa.TEXT(), nullable=False),
        sa.Column("status", sa.VARCHAR(), nullable=False),
        sa.Column("return_code", sa.INTEGER(), nullable=True),
        sa.Column("output", sa.TEXT(), nullable=True),
        sa.Column("error", sa.VARCHAR(length=2000), nullable=True),
        sa.Column("duration_seconds", sa.DOUBLE_PRECISION(precision=53), nullable=True),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["scan_activities.id"],
            name="scan_commands_activity_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="scan_commands_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="scan_commands_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="scan_commands_pkey"),
    )
    op.create_index("ix_scan_commands_activity_id", "scan_commands", ["activity_id"])
    op.create_index("ix_scan_commands_project_id", "scan_commands", ["project_id"])
    op.create_index("ix_scan_commands_scan_id", "scan_commands", ["scan_id"])
    op.create_index("ix_scan_commands_status", "scan_commands", ["status"])
    op.create_index("ix_scan_commands_tool", "scan_commands", ["tool"])
    op.create_table(
        "secret_sightings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("secret_id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("host", sa.VARCHAR(length=500), nullable=False),
        sa.Column("url", sa.VARCHAR(length=2000), nullable=False),
        sa.Column("http_asset_id", sa.UUID(), nullable=True),
        sa.Column("source", sa.VARCHAR(length=16), nullable=False),
        sa.Column("offset", sa.INTEGER(), server_default=sa.text("0"), nullable=False),
        sa.Column("context", sa.TEXT(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="secret_sightings_project_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="secret_sightings_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["secret_id"],
            ["secrets.id"],
            name="secret_sightings_secret_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="secret_sightings_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="secret_sightings_pkey"),
        sa.UniqueConstraint(
            "secret_id",
            "url",
            "source",
            name="uq_sighting_secret_url",
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index(
        "ix_secret_sightings_http_asset_id", "secret_sightings", ["http_asset_id"]
    )
    op.create_index(
        "ix_secret_sightings_project_id", "secret_sightings", ["project_id"]
    )
    op.create_index(
        "ix_secret_sightings_scan_host", "secret_sightings", ["scan_id", "host"]
    )
    op.create_index("ix_secret_sightings_scan_id", "secret_sightings", ["scan_id"])
    op.create_index("ix_secret_sightings_secret_id", "secret_sightings", ["secret_id"])
    op.create_index("ix_secret_sightings_target_id", "secret_sightings", ["target_id"])

    for table in RESULT_TABLES:
        op.execute(f"ALTER TABLE {table} SET ({RESULT_STORAGE})")

    op.execute(BUMP)
    for table, dimension in REVISION_TABLES.items():
        for event, alias in (("INSERT", "NEW"), ("DELETE", "OLD")):
            op.execute(
                f"CREATE TRIGGER {table}_revisions_{event.lower()} "
                f"AFTER {event} ON {table} "
                f"REFERENCING {alias} TABLE AS changed_rows "
                f"FOR EACH STATEMENT EXECUTE FUNCTION scan_revisions_bump('{dimension}')"
            )


def downgrade() -> None:  # noqa: PLR0915
    op.drop_table("secret_sightings")
    op.drop_table("scan_commands")
    op.drop_table("interest_signals")
    op.drop_table("endpoint_responses")
    op.drop_table("vulnerability_coverage")
    op.drop_table("vulnerabilities")
    op.drop_table("tripwire_runs")
    op.drop_table("tripwire_marks")
    op.drop_table("tracked_issue_findings")
    op.drop_table("tracked_issue_comments")
    op.drop_table("subdomains")
    op.drop_table("software_cves")
    op.drop_table("secrets")
    op.drop_table("secret_coverage")
    op.drop_table("scan_surface_items")
    op.drop_table("scan_revisions")
    op.drop_table("scan_retired")
    op.drop_table("scan_deltas")
    op.drop_table("scan_activities")
    op.drop_table("ports")
    op.drop_table("notes")
    op.drop_table("lookalike_domains")
    op.drop_table("ip_addresses")
    op.drop_table("intel_signals")
    op.drop_table("http_assets")
    op.drop_table("exports")
    op.drop_table("endpoints")
    op.drop_table("endpoint_coverage")
    op.drop_table("domain_posture")
    op.drop_table("asset_rechecks")
    op.drop_table("ask_messages")
    op.drop_table("watch_hosts")
    op.drop_table("watch_events")
    op.drop_table("vulnerability_triage")
    op.drop_table("tracked_issues")
    op.drop_table("target_tags")
    op.drop_table("target_seeds")
    op.drop_table("target_organizations")
    op.drop_table("target_bgp_summaries")
    op.drop_table("scans")
    op.drop_table("lookalike_triage")
    op.drop_table("issue_tracker_routes")
    op.drop_table("interest_dismissals")
    op.drop_table("dns_records")
    op.drop_table("connector_hosts")
    op.drop_table("connector_candidates")
    op.drop_table("connector_actions")
    op.drop_table("ask_threads")
    op.drop_table("activity_logs")
    op.drop_table("tripwires")
    op.drop_table("targets")
    op.drop_table("tags")
    op.drop_table("scan_schedules")
    op.drop_table("scan_engines")
    op.drop_table("scan_contexts")
    op.drop_table("reports")
    op.drop_table("program_watches")
    op.drop_table("organizations")
    op.drop_table("interest_rules")
    op.drop_table("estate_triage")
    op.drop_table("estate_candidate")
    op.drop_table("connectors")
    op.drop_table("channel_chats")
    op.drop_table("whois_nameservers")
    op.drop_table("user_marks")
    op.drop_table("proxies")
    op.drop_table("projects")
    op.drop_table("notification_receipts")
    op.drop_table("notification_channels")
    op.drop_table("instance_settings")
    op.drop_table("bounty_scopes")
    op.drop_table("bounty_events")
    op.drop_table("wordlists")
    op.drop_table("whois_records")
    op.drop_table("vuln_templates")
    op.drop_table("viewdns_cache")
    op.drop_table("users")
    op.drop_table("threat_feeds")
    op.drop_table("ripestat_related_prefixes")
    op.drop_table("ripestat_query_log")
    op.drop_table("ripestat_prefix_overviews")
    op.drop_table("ripestat_network_info")
    op.drop_table("ripestat_asn_neighbours")
    op.drop_table("ripestat_as_overviews")
    op.drop_table("ripestat_announced_prefixes")
    op.drop_table("ripestat_abuse_contacts")
    op.drop_table("report_themes")
    op.drop_table("report_templates")
    op.drop_table("report_fonts")
    op.drop_table("nvd_cves")
    op.drop_table("nvd_cpe_matches")
    op.drop_table("notifications")
    op.drop_table("mcp_tokens")
    op.drop_table("kev_entries")
    op.drop_table("issue_trackers")
    op.drop_table("ip_country_ranges")
    op.drop_table("ip_asn_ranges")
    op.drop_table("epss_scores")
    op.drop_table("dns_lookups")
    op.drop_table("cve_intel")
    op.drop_table("channel_configs")
    op.drop_table("bounty_reports")
    op.drop_table("bounty_programs")
    op.drop_table("bounty_awards")
    op.drop_table("bounty_accounts")
    op.drop_table("api_keys")
    op.drop_table("ai_prices")
    op.drop_table("ai_narratives")
    op.drop_table("ai_connections")
    op.drop_table("ai_calls")
    op.execute("DROP FUNCTION scan_revisions_bump()")
    for name in ENUMS:
        op.execute(f"DROP TYPE {name}")

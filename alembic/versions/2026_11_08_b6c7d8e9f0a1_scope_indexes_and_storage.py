"""scope-leading indexes, unread index drops, fillfactor and autovacuum

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-11-08

Drops, each read by no predicate it could serve:
ix_subdomains_is_active: boolean, every reader also filters scan_id
ix_subdomains_is_excluded: boolean, every reader also filters scan_id
ix_subdomains_target_id: prefix of ix_subdomains_target_discovered
ix_endpoints_subdomain_id: no reader, not a foreign key
ix_endpoints_target_id: prefix of ix_endpoints_target_discovered
ix_vulnerabilities_subdomain_id: no reader, not a foreign key
ix_vulnerabilities_port_id: no reader, not a foreign key
ix_vulnerabilities_target_id: prefix of ix_vulnerabilities_target_discovered
ix_software_cves_port_id: read only as IS NOT NULL inside a scan scope
ix_software_cves_http_asset_id: read only as IS NOT NULL inside a scan scope
ix_software_cves_host: every reader also filters scan_id, served by ix_software_cves_scan_host
ix_software_cves_target_id: prefix of ix_software_cves_target_discovered
ix_secrets_http_asset_id: no reader, not a foreign key
ix_secrets_target_id: prefix of ix_secrets_target_discovered
ix_ports_is_http: boolean, every reader also filters scan_id
ix_ports_target_id: prefix of ix_ports_target_discovered
ix_ip_addresses_target_id: prefix of ix_ip_addresses_target_discovered
ix_scan_activities_scan_id: prefix of ix_scan_activities_scan_name
ix_scan_activities_name: every reader also filters scan_id
ix_scan_activities_status: every reader also filters scan_id or id
ix_nvd_cves_published_at: written, and read off the row alone
ix_nvd_cves_severity: read only after a join on cve
"""

from collections.abc import Sequence

from alembic import op

revision: str = "b6c7d8e9f0a1"
down_revision: str | None = "a5b6c7d8e9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REGISTRANT_KEY = (
    "(CASE WHEN (coalesce(btrim(regexp_replace(lower(registrant_name), '\\s+', ' ', 'g')), '') "
    "IN ('', '-', '--', 'n/a', 'na', 'nil', 'no', 'none', 'not applicable', 'not available', "
    "'not disclosed', 'null', 'tbd', 'unknown') "
    "OR (btrim(regexp_replace(lower(registrant_name), '\\s+', ' ', 'g')) ~ "
    "'anonymised|anonymize|anonymized|by proxy|data protected|data protection|domain protection|"
    "domains by proxy|gdpr|identity protection|masking enabled|non-public data|obscured whois|"
    "privacy|privacydotlink|private registration|proxy protection|redact|redacted|"
    "registrant private|registration private|statutory masking|whoisguard|withheld for')) "
    "THEN '' ELSE regexp_replace(regexp_replace(lower(registrant_name), "
    "'((^|[^a-z0-9]+)(incorporated|corporation|limited|holdings|company|group|gmbh|corp|llc|"
    "ltd|inc|plc|sas|sarl|bv|nv|ab|as|oy|pty|pte|srl|spa|kk|co|sa))+[^a-z0-9]*$', '', 'g'), "
    "'[^a-z0-9]', '', 'g') END)"
)

CREATED = (
    ("ix_endpoints_scan_tree", "endpoints (scan_id, host, dir_path, path)"),
    ("ix_endpoints_sources_gin", "endpoints USING gin ((sources::jsonb))"),
    (
        "ix_subdomains_scan_title",
        "subdomains (scan_id, page_title) INCLUDE (target_id, is_excluded, http_status) "
        "WHERE page_title IS NOT NULL",
    ),
    (
        "ix_scan_activities_scan_name",
        "scan_activities (scan_id, name) INCLUDE (status)",
    ),
    (
        "ix_http_assets_hygiene_pending",
        "http_assets (scan_id) WHERE hygiene_checked IS NULL",
    ),
    (
        "ix_http_assets_host_reverse",
        "http_assets (reverse(host) text_pattern_ops)",
    ),
    (
        "ix_http_assets_screenshot_unhashed",
        "http_assets (scan_id) WHERE screenshot_path IS NOT NULL "
        "AND screenshot_phash IS NULL",
    ),
    (
        "ix_ip_addresses_enrich_pending",
        "ip_addresses (discovered_at DESC, id DESC) "
        "WHERE asn IS NULL OR country IS NULL",
    ),
    (
        "ix_scan_surface_root_covered",
        "scan_surface_items (target_id, value) WHERE class = 'root' "
        "AND (tiers_done::jsonb ->> 'universal') LIKE 'completed@%'",
    ),
    ("ix_software_cves_scan_host", "software_cves (scan_id, host)"),
    ("ix_software_cves_name_trgm", "software_cves USING gin (name gin_trgm_ops)"),
    ("ix_software_cves_host_trgm", "software_cves USING gin (host gin_trgm_ops)"),
    ("ix_software_cves_cve_trgm", "software_cves USING gin (cve gin_trgm_ops)"),
    ("ix_secrets_subject_trgm", "secrets USING gin (subject gin_trgm_ops)"),
    ("ix_secrets_host_trgm", "secrets USING gin (host gin_trgm_ops)"),
    ("ix_secrets_url_trgm", "secrets USING gin (url gin_trgm_ops)"),
    ("ix_whois_records_registrant_key", f"whois_records ({REGISTRANT_KEY})"),
    ("ix_target_tags_tag_id", "target_tags (tag_id)"),
    (
        "ix_target_organizations_organization_id",
        "target_organizations (organization_id)",
    ),
)

DROPPED = (
    ("ix_subdomains_is_active", "subdomains (is_active)"),
    ("ix_subdomains_is_excluded", "subdomains (is_excluded)"),
    ("ix_subdomains_target_id", "subdomains (target_id)"),
    ("ix_endpoints_subdomain_id", "endpoints (subdomain_id)"),
    ("ix_endpoints_target_id", "endpoints (target_id)"),
    ("ix_vulnerabilities_subdomain_id", "vulnerabilities (subdomain_id)"),
    ("ix_vulnerabilities_port_id", "vulnerabilities (port_id)"),
    ("ix_vulnerabilities_target_id", "vulnerabilities (target_id)"),
    ("ix_software_cves_port_id", "software_cves (port_id)"),
    ("ix_software_cves_http_asset_id", "software_cves (http_asset_id)"),
    ("ix_software_cves_host", "software_cves (host)"),
    ("ix_software_cves_target_id", "software_cves (target_id)"),
    ("ix_secrets_http_asset_id", "secrets (http_asset_id)"),
    ("ix_secrets_target_id", "secrets (target_id)"),
    ("ix_ports_is_http", "ports (is_http)"),
    ("ix_ports_target_id", "ports (target_id)"),
    ("ix_ip_addresses_target_id", "ip_addresses (target_id)"),
    ("ix_scan_activities_scan_id", "scan_activities (scan_id)"),
    ("ix_scan_activities_name", "scan_activities (name)"),
    ("ix_scan_activities_status", "scan_activities (status)"),
    ("ix_nvd_cves_published_at", "nvd_cves (published_at)"),
    ("ix_nvd_cves_severity", "nvd_cves (severity)"),
)

HOT_TABLES = ("subdomains", "http_assets", "endpoints", "vulnerabilities")

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
RESULT_STORAGE = (
    "autovacuum_analyze_scale_factor = 0.02, autovacuum_vacuum_scale_factor = 0.05"
)
INSERT_STORAGE = (
    "autovacuum_vacuum_insert_scale_factor = 0.05, "
    "autovacuum_vacuum_insert_threshold = 10000"
)
INSERT_KEYS = (
    "autovacuum_vacuum_insert_scale_factor, autovacuum_vacuum_insert_threshold"
)
STORAGE_KEYS = (
    "autovacuum_analyze_scale_factor, autovacuum_vacuum_scale_factor, " + INSERT_KEYS
)
NEW_STORAGE_TABLES = (
    "nvd_cpe_matches",
    "scan_surface_items",
    "scan_activities",
    "secrets",
)


def upgrade() -> None:
    for name, _definition in DROPPED:
        op.execute(f"DROP INDEX {name}")
    for name, definition in CREATED:
        op.execute(f"CREATE INDEX {name} ON {definition}")
    for table in HOT_TABLES:
        op.execute(f"ALTER TABLE {table} SET (fillfactor = 85)")
    for table in RESULT_TABLES:
        op.execute(f"ALTER TABLE {table} SET ({INSERT_STORAGE})")
    for table in NEW_STORAGE_TABLES:
        op.execute(f"ALTER TABLE {table} SET ({RESULT_STORAGE}, {INSERT_STORAGE})")


def downgrade() -> None:
    for table in NEW_STORAGE_TABLES:
        op.execute(f"ALTER TABLE {table} RESET ({STORAGE_KEYS})")
    for table in RESULT_TABLES:
        op.execute(f"ALTER TABLE {table} RESET ({INSERT_KEYS})")
    for table in HOT_TABLES:
        op.execute(f"ALTER TABLE {table} RESET (fillfactor)")
    for name, _definition in reversed(CREATED):
        op.execute(f"DROP INDEX {name}")
    for name, definition in reversed(DROPPED):
        op.execute(f"CREATE INDEX {name} ON {definition}")

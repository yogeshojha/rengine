"""Drop the transport and constant fields from stored engines.

Revision ID: b7d3e1f04a26
Revises: a4c2e7d91f53
Create Date: 2026-09-14
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision: str = "b7d3e1f04a26"
down_revision: str | None = "a4c2e7d91f53"
branch_labels = None
depends_on = None

_REMOVED: dict[str, set[str]] = {
    "content_discovery": {"threads", "rate", "timeout"},
    "dast_scan": {
        "max_dirs_per_origin",
        "dir_depth",
        "fuzz_param_frequency",
        "rate",
        "threads",
        "bulk_size",
        "timeout",
        "retries",
        "max_host_error",
        "waf_rate_divisor",
        "honeypot_threshold",
        "interactsh_server",
        "oast_wait_minutes",
        "store_evidence",
        "max_evidence_recovery",
        "max_findings",
    },
    "endpoint_probe": {"threads", "timeout", "rate", "follow_redirects"},
    "host_discovery": {"rate", "threads", "timeout"},
    "http_probe": {
        "threads",
        "timeout",
        "rate",
        "follow_redirects",
        "probe_open_ports",
        "max_ports_per_host",
    },
    "netblock_sweep": {
        "min_addresses",
        "max_asn_addresses",
        "min_share",
        "dns_threads",
        "dns_timeout",
    },
    "origin_probe": {"threads", "timeout", "rate", "max_ports_per_address"},
    "passive_ports": {"max_addresses"},
    "port_scan": {"rate", "threads", "timeout", "retries", "port_threshold"},
    "reverse_dns": {"dns_threads", "dns_timeout"},
    "screenshot": {"threads", "rate", "timeout"},
    "seed_resolution": {"cidr_skip_rfc1918"},
    "service_fingerprint": {"threads", "timeout", "include_unknown"},
    "session_check": {"timeout"},
    "subdomain_discovery": {
        "permutation_seeds",
        "permutation_limit",
        "dns_threads",
        "dns_batch_size",
        "dns_batch_concurrency",
        "dns_idle_timeout",
        "dns_retry_silent",
    },
    "target_enrichment": {"dns_threads", "dns_timeout"},
    "url_discovery": {
        "threads",
        "timeout",
        "rate",
        "crawl_javascript",
        "max_urls",
        "max_known_file_hosts",
        "max_source_maps",
        "max_archive_domains",
    },
    "vhost": {"threads", "rate"},
    "vulnerability_scan": {
        "rate",
        "threads",
        "bulk_size",
        "timeout",
        "retries",
        "max_host_error",
        "waf_rate_divisor",
        "honeypot_threshold",
        "oast_wait_minutes",
        "max_evidence_recovery",
        "max_findings",
    },
}


def _prune(stages: dict) -> tuple[dict, bool]:
    changed = False
    out: dict = {}
    for name, config in (stages or {}).items():
        if not isinstance(config, dict):
            out[name] = config
            continue
        gone = _REMOVED.get(name, set())
        kept = {k: v for k, v in config.items() if k not in gone}
        if len(kept) != len(config):
            changed = True
        if kept:
            out[name] = kept
        elif config:
            changed = True
    return out, changed


def _yaml_mentions_removed(source: str | None) -> bool:
    if not source:
        return False
    try:
        import yaml  # noqa: PLC0415

        doc = yaml.safe_load(source) or {}
    except Exception:  # noqa: BLE001
        return False
    stages = doc.get("stages") if isinstance(doc, dict) else None
    if not isinstance(stages, dict):
        return False
    return any(
        isinstance(cfg, dict) and set(cfg) & _REMOVED.get(name, set())
        for name, cfg in stages.items()
    )


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, stages, yaml_source FROM scan_engines")
    ).all()
    for id_, stages, yaml_source in rows:
        raw = stages if isinstance(stages, dict) else json.loads(stages or "{}")
        pruned, changed = _prune(raw)
        drop_yaml = _yaml_mentions_removed(yaml_source)
        if not changed and not drop_yaml:
            continue
        bind.execute(
            sa.text(
                "UPDATE scan_engines SET stages = :stages, "
                "yaml_source = CASE WHEN :drop THEN NULL ELSE yaml_source END "
                "WHERE id = :id"
            ),
            {"stages": json.dumps(pruned), "drop": drop_yaml, "id": id_},
        )


def downgrade() -> None:
    """Irreversible: the pruned keys and cleared YAML sources are not kept; an
    engine without them runs on the stage defaults.
    """

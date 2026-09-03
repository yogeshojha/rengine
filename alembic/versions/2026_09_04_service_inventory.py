"""service-level port inventory + per-address port-scan policy

Revision ID: a4c7e91b2d63
Revises: d17b3c9e5f24
Create Date: 2026-09-04 00:20:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from shared.definitions.ports import WEB_PORTS, WELL_KNOWN, ServiceClass

revision: str = "a4c7e91b2d63"
down_revision: str | None = "d17b3c9e5f24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ports",
        sa.Column(
            "service_class",
            sa.String(length=16),
            nullable=False,
            server_default="other",
        ),
    )
    op.add_column(
        "ports",
        sa.Column("is_http", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "ports",
        sa.Column("tls", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("ports", sa.Column("product", sa.String(length=200), nullable=True))
    op.add_column("ports", sa.Column("version", sa.String(length=100), nullable=True))
    op.add_column("ports", sa.Column("banner", sa.String(length=1000), nullable=True))
    op.add_column(
        "ports",
        sa.Column(
            "cpe",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.create_index("ix_ports_service_class", "ports", ["service_class"])
    op.create_index("ix_ports_is_http", "ports", ["is_http"])
    op.create_index("ix_ports_service_name", "ports", ["service_name"])
    op.create_index("ix_ports_scan_ip", "ports", ["scan_id", "ip"])

    op.add_column(
        "ip_addresses", sa.Column("cdn_type", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "ip_addresses", sa.Column("scan_policy", sa.String(length=16), nullable=True)
    )
    op.add_column(
        "ip_addresses",
        sa.Column("scan_policy_reason", sa.String(length=32), nullable=True),
    )
    op.create_index("ix_ip_addresses_scan_policy", "ip_addresses", ["scan_policy"])

    _classify_existing_ports()

    # cdn_check moved from IP-only to every target type; an inert false recorded no opinion
    op.execute(
        """
        UPDATE scan_engines
        SET stages = cast(cast(stages AS jsonb) - 'cdn_check' AS json)
        WHERE cast(stages AS jsonb) -> 'cdn_check' ->> 'enabled' = 'false'
        """
    )
    # port_scan.ports used to hold the whole spec; it is a profile plus a custom list now
    op.execute(
        """
        UPDATE scan_engines SET stages = cast(jsonb_set(
            cast(stages AS jsonb), '{port_scan,profile}',
            to_jsonb(CASE lower(cast(stages AS jsonb) -> 'port_scan' ->> 'ports')
                WHEN 'top-100' THEN 'top-100'
                WHEN 'top100' THEN 'top-100'
                WHEN 'top-1000' THEN 'top-1000'
                WHEN 'top1000' THEN 'top-1000'
                WHEN 'full' THEN 'full'
                WHEN 'all' THEN 'full'
                WHEN '-' THEN 'full'
                ELSE 'custom' END)
        ) AS json)
        WHERE nullif(cast(stages AS jsonb) -> 'port_scan' ->> 'ports', '') IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE scan_engines SET stages = cast(jsonb_set(
            cast(stages AS jsonb), '{port_scan,ports}', '""'
        ) AS json)
        WHERE cast(stages AS jsonb) -> 'port_scan' ->> 'profile' IS DISTINCT FROM 'custom'
          AND cast(stages AS jsonb) -> 'port_scan' ? 'ports'
        """
    )
    op.execute(
        """
        UPDATE scan_engines SET stages = cast(jsonb_set(
            cast(stages AS jsonb), '{port_scan}',
            (cast(stages AS jsonb) -> 'port_scan') - 'exclude_cdn'
        ) AS json)
        WHERE cast(stages AS jsonb) -> 'port_scan' ? 'exclude_cdn'
        """
    )
    # the authored document still carries the old port_scan keys; regenerate it from stages
    op.execute(
        "UPDATE scan_engines SET yaml_source = NULL "
        "WHERE yaml_source IS NOT NULL AND yaml_source LIKE '%port_scan%'"
    )


def _classify_existing_ports() -> None:
    """Rows written before this migration all carry the 'other' default."""
    by_class: dict[str, set[int]] = {}
    for number, spec in WELL_KNOWN.items():
        by_class.setdefault(spec.klass, set()).add(number)
    by_class.setdefault(ServiceClass.WEB.value, set()).update(WEB_PORTS)
    for klass, numbers in by_class.items():
        if klass == ServiceClass.OTHER.value or not numbers:
            continue
        listed = ",".join(str(n) for n in sorted(numbers))
        op.execute(
            f"UPDATE ports SET service_class = '{klass}' WHERE number IN ({listed})"  # noqa: S608
        )
    op.execute(
        """
        UPDATE ports p SET is_http = true, service_class = 'web',
            tls = (h.scheme = 'https'),
            service_name = coalesce(p.service_name, h.scheme)
        FROM (
            SELECT DISTINCT ON (scan_id, ip, port) scan_id, ip, port, scheme
            FROM http_assets WHERE ip IS NOT NULL
            ORDER BY scan_id, ip, port, (scheme = 'https') DESC
        ) h
        WHERE p.scan_id = h.scan_id AND p.ip = h.ip AND p.number = h.port
        """
    )
    # the rollup is a set, not a sum of stage results, so restate it from the table
    op.execute(
        "UPDATE scans s SET open_ports_found = "
        "(SELECT count(*) FROM ports p WHERE p.scan_id = s.id)"
    )


def downgrade() -> None:
    op.drop_index("ix_ip_addresses_scan_policy", table_name="ip_addresses")
    op.drop_column("ip_addresses", "scan_policy_reason")
    op.drop_column("ip_addresses", "scan_policy")
    op.drop_column("ip_addresses", "cdn_type")
    op.drop_index("ix_ports_scan_ip", table_name="ports")
    op.drop_index("ix_ports_service_name", table_name="ports")
    op.drop_index("ix_ports_is_http", table_name="ports")
    op.drop_index("ix_ports_service_class", table_name="ports")
    for col in (
        "cpe",
        "banner",
        "version",
        "product",
        "tls",
        "is_http",
        "service_class",
    ):
        op.drop_column("ports", col)

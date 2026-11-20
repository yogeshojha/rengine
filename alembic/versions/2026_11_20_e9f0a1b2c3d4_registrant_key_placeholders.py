"""registrant key reads registry placeholders as redacted

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-11-20
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e9f0a1b2c3d4"
down_revision: str | None = "d8e9f0a1b2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX = "ix_whois_records_registrant_key"

PREVIOUS = (
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

REGISTRANT_KEY = (
    "(CASE WHEN (coalesce(btrim(regexp_replace(lower(registrant_name), '\\s+', ' ', 'g')), '') "
    "IN ('', '-', '--', 'n/a', 'na', 'nil', 'no', 'none', 'not applicable', 'not available', "
    "'null', 'tbd', 'unknown') "
    "OR (btrim(regexp_replace(lower(registrant_name), '\\s+', ' ', 'g')) ~ "
    "'anonymised|anonymize|anonymized|by proxy|data protected|data protection|domain protection|"
    "domains by proxy|gdpr|hidden upon|identity protection|masking enabled|non-public data|"
    "not disclosed|not shown|obscured whois|"
    "privacy|privacydotlink|private registration|proxy protection|redact|redacted|"
    "registrant private|registration private|statutory masking|whoisguard|withheld for')) "
    "THEN '' ELSE regexp_replace(regexp_replace(lower(registrant_name), "
    "'((^|[^a-z0-9]+)(incorporated|corporation|limited|holdings|company|group|gmbh|corp|llc|"
    "ltd|inc|plc|sas|sarl|bv|nv|ab|as|oy|pty|pte|srl|spa|kk|co|sa))+[^a-z0-9]*$', '', 'g'), "
    "'[^a-z0-9]', '', 'g') END)"
)


def upgrade() -> None:
    op.execute(f"DROP INDEX {INDEX}")
    op.execute(f"CREATE INDEX {INDEX} ON whois_records ({REGISTRANT_KEY})")


def downgrade() -> None:
    op.execute(f"DROP INDEX {INDEX}")
    op.execute(f"CREATE INDEX {INDEX} ON whois_records ({PREVIOUS})")

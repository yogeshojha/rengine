"""keyed subdomain and internet scan sources

Revision ID: b4f348070912
Revises: b7d2e4a91c35
Create Date: 2026-11-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "b4f348070912"
down_revision: str | None = "b7d2e4a91c35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PROVIDERS = (
    "VIRUSTOTAL",
    "CENSYS",
    "SHODAN",
    "ALIENVAULT",
    "URLSCAN",
    "CERTSPOTTER",
    "FULLHUNT",
    "LEAKIX",
    "BEVIGIL",
    "INTELX",
    "WHOISXMLAPI",
    "FOFA",
    "ZOOMEYE",
)


def upgrade() -> None:
    for provider in PROVIDERS:
        op.execute(f"ALTER TYPE apiprovider ADD VALUE IF NOT EXISTS '{provider}'")


def downgrade() -> None:
    labels = ", ".join(f"'{p}'" for p in PROVIDERS)
    op.execute(f"DELETE FROM api_keys WHERE provider::text IN ({labels})")  # noqa: S608

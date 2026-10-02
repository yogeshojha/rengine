"""migrate fks

Revision ID: 32af52b2b23b
Revises: d55cda538e83
Create Date: 2026-02-21 15:55:30.366973+00:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "32af52b2b23b"
down_revision: str | None = "d55cda538e83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("dns_records_dns_lookup_id_fkey"), "dns_records", type_="foreignkey"
    )
    op.drop_constraint(
        op.f("dns_records_target_id_fkey"), "dns_records", type_="foreignkey"
    )
    op.create_foreign_key(
        None,
        "dns_records",
        "dns_lookups",
        ["dns_lookup_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None, "dns_records", "targets", ["target_id"], ["id"], ondelete="CASCADE"
    )
    op.drop_constraint(op.f("tags_project_id_fkey"), "tags", type_="foreignkey")
    op.create_foreign_key(
        None, "tags", "projects", ["project_id"], ["id"], ondelete="CASCADE"
    )
    op.drop_constraint(
        op.f("target_bgp_summaries_target_id_fkey"),
        "target_bgp_summaries",
        type_="foreignkey",
    )
    op.create_foreign_key(
        None,
        "target_bgp_summaries",
        "targets",
        ["target_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        op.f("target_organizations_organization_id_fkey"),
        "target_organizations",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("target_organizations_target_id_fkey"),
        "target_organizations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        None,
        "target_organizations",
        "targets",
        ["target_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "target_organizations",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        op.f("target_tags_tag_id_fkey"), "target_tags", type_="foreignkey"
    )
    op.drop_constraint(
        op.f("target_tags_target_id_fkey"), "target_tags", type_="foreignkey"
    )
    op.create_foreign_key(
        None, "target_tags", "tags", ["tag_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        None, "target_tags", "targets", ["target_id"], ["id"], ondelete="CASCADE"
    )
    op.drop_constraint(
        op.f("targets_whois_record_id_fkey"), "targets", type_="foreignkey"
    )
    op.drop_constraint(
        op.f("targets_dns_lookup_id_fkey"), "targets", type_="foreignkey"
    )
    op.create_foreign_key(
        None,
        "targets",
        "whois_records",
        ["whois_record_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        None, "targets", "dns_lookups", ["dns_lookup_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint("targets_whois_record_id_fkey", "targets", type_="foreignkey")
    op.drop_constraint("targets_dns_lookup_id_fkey", "targets", type_="foreignkey")
    op.create_foreign_key(
        op.f("targets_dns_lookup_id_fkey"),
        "targets",
        "dns_lookups",
        ["dns_lookup_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("targets_whois_record_id_fkey"),
        "targets",
        "whois_records",
        ["whois_record_id"],
        ["id"],
    )
    op.drop_constraint("target_tags_tag_id_fkey", "target_tags", type_="foreignkey")
    op.drop_constraint("target_tags_target_id_fkey", "target_tags", type_="foreignkey")
    op.create_foreign_key(
        op.f("target_tags_target_id_fkey"),
        "target_tags",
        "targets",
        ["target_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("target_tags_tag_id_fkey"), "target_tags", "tags", ["tag_id"], ["id"]
    )
    op.drop_constraint(
        "target_organizations_target_id_fkey",
        "target_organizations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "target_organizations_organization_id_fkey",
        "target_organizations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("target_organizations_target_id_fkey"),
        "target_organizations",
        "targets",
        ["target_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("target_organizations_organization_id_fkey"),
        "target_organizations",
        "organizations",
        ["organization_id"],
        ["id"],
    )
    op.drop_constraint(
        "target_bgp_summaries_target_id_fkey",
        "target_bgp_summaries",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("target_bgp_summaries_target_id_fkey"),
        "target_bgp_summaries",
        "targets",
        ["target_id"],
        ["id"],
    )
    op.drop_constraint("tags_project_id_fkey", "tags", type_="foreignkey")
    op.create_foreign_key(
        op.f("tags_project_id_fkey"), "tags", "projects", ["project_id"], ["id"]
    )
    op.drop_constraint(
        "dns_records_dns_lookup_id_fkey", "dns_records", type_="foreignkey"
    )
    op.drop_constraint("dns_records_target_id_fkey", "dns_records", type_="foreignkey")
    op.create_foreign_key(
        op.f("dns_records_target_id_fkey"),
        "dns_records",
        "targets",
        ["target_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("dns_records_dns_lookup_id_fkey"),
        "dns_records",
        "dns_lookups",
        ["dns_lookup_id"],
        ["id"],
    )

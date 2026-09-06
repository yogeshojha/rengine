from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag
from shared.definitions.reports import SectionGroup


class WhoisConfig(SectionConfig):
    show_contacts: bool = flag(True, title="Show registrant and abuse contacts")
    show_status: bool = flag(True, title="Show domain status codes")
    show_nameservers: bool = flag(True, title="Show nameservers")


class WhoisSection(Section):
    name = "whois"
    title = "Registration"
    description = "The registration record for the subject."
    group = SectionGroup.INTELLIGENCE.value
    order = 10
    default_enabled = False
    config_model = WhoisConfig

    def build(self, ctx: RenderContext, cfg: WhoisConfig) -> dict | None:
        record = getattr(ctx.data.target, "whois_record", None)
        if record is None:
            return None
        facts = [
            ("Name", record.name),
            ("Registrar", record.registrar_name),
            (
                "Registered",
                record.registration_date.strftime("%d %B %Y")
                if record.registration_date
                else "",
            ),
            (
                "Last changed",
                record.last_changed_date.strftime("%d %B %Y")
                if record.last_changed_date
                else "",
            ),
            (
                "Expires",
                record.expiration_date.strftime("%d %B %Y")
                if record.expiration_date
                else "",
            ),
            (
                "DNSSEC",
                "Enabled"
                if record.dnssec
                else ("Not enabled" if record.dnssec is not None else ""),
            ),
            ("Country", record.country),
            ("Network", record.network_cidr),
        ]
        contacts = [
            ("Registrant", record.registrant_name),
            ("Registrant email", record.registrant_email),
            ("Abuse email", record.abuse_email),
        ]
        return {
            "facts": [(label, value) for label, value in facts if value],
            "contacts": [(label, value) for label, value in contacts if value]
            if cfg.show_contacts
            else [],
            "nameservers": list(record.nameservers or [])
            if cfg.show_nameservers
            else [],
            "status": list(record.domain_status or []) if cfg.show_status else [],
            "queried_at": record.queried_at,
        }

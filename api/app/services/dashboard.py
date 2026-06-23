from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.enums.dns import DnsRecordType
from shared.enums.scan import ScanStatus
from shared.enums.target import TargetType
from shared.enums.task_status import TaskStatus
from shared.logging import get_logger
from shared.models.dashboard import (
    DashboardSignals,
    SpoofableDomain,
    SpoofableSignal,
    StaleSignal,
    StaleTarget,
    TakeoverCandidate,
    TakeoverSignal,
)
from shared.models.dns import DnsRecord
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.models.target import Target
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

_CNAME_SCAN_CAP = 50000
_ITEMS_CAP = 100
_STALE_DAYS = 30

_DOMAIN_TYPES = (TargetType.DOMAIN, TargetType.URL)

# CNAME suffix → provider; a dangling CNAME to these is a takeover candidate
TAKEOVER_FINGERPRINTS: tuple[tuple[str, str], ...] = (
    ("s3.amazonaws.com", "AWS S3"),
    ("s3-website", "AWS S3"),
    ("cloudfront.net", "AWS CloudFront"),
    ("github.io", "GitHub Pages"),
    ("herokuapp.com", "Heroku"),
    ("herokudns.com", "Heroku"),
    ("herokussl.com", "Heroku"),
    ("azurewebsites.net", "Azure"),
    ("cloudapp.net", "Azure"),
    ("cloudapp.azure.com", "Azure"),
    ("trafficmanager.net", "Azure"),
    ("blob.core.windows.net", "Azure"),
    ("azureedge.net", "Azure"),
    ("myshopify.com", "Shopify"),
    ("fastly.net", "Fastly"),
    ("ghost.io", "Ghost"),
    ("wpengine.com", "WP Engine"),
    ("zendesk.com", "Zendesk"),
    ("surge.sh", "Surge"),
    ("bitbucket.io", "Bitbucket"),
    ("statuspage.io", "Statuspage"),
    ("uservoice.com", "UserVoice"),
    ("netlify.app", "Netlify"),
    ("netlify.com", "Netlify"),
    ("readme.io", "Readme"),
    ("pantheonsite.io", "Pantheon"),
    ("unbouncepages.com", "Unbounce"),
    ("tilda.ws", "Tilda"),
    ("helpscoutdocs.com", "Help Scout"),
    ("launchrock.com", "LaunchRock"),
    ("wordpress.com", "WordPress.com"),
)


def _match_takeover(cname: str) -> str | None:
    host = cname.strip().lower().rstrip(".")
    for suffix, provider in TAKEOVER_FINGERPRINTS:
        if suffix in host:
            return provider
    return None


# Only flag the absence of an effective sender policy; ~all/-all express a real
# policy (and ~all is usually DMARC-backed, which we can't see) so they're not flagged.
def _spf_reason(spf: str | None) -> str | None:
    if spf is None:
        return "No SPF record (mail configured)"
    if "+all" in spf:
        return "Permissive SPF (+all)"
    if "?all" in spf:
        return "Neutral SPF (?all)"
    return None


class DashboardService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def signals(self, project_id: UUID) -> DashboardSignals:
        return DashboardSignals(
            takeover=await self._takeover_candidates(project_id),
            spoofable=await self._spoofable_domains(project_id),
            stale=await self._stale_targets(project_id),
        )

    async def _takeover_candidates(self, project_id: UUID) -> TakeoverSignal:
        query = (
            select(Subdomain)
            .where(
                Subdomain.project_id == project_id,
                Subdomain.cname.is_not(None),
                Subdomain.cname != "",
            )
            .order_by(Subdomain.discovered_at.desc(), Subdomain.scan_id.desc())
            .limit(_CNAME_SCAN_CAP + 1)
        )
        rows = list((await self.session.execute(query)).scalars().all())
        if len(rows) > _CNAME_SCAN_CAP:
            logger.warning("takeover scan capped at %d cname rows", _CNAME_SCAN_CAP)
            rows = rows[:_CNAME_SCAN_CAP]
        rows.sort(key=lambda r: (r.discovered_at, str(r.scan_id)))
        latest: dict[tuple, Subdomain] = {}
        for r in rows:
            latest[(r.target_id, r.name)] = r

        candidates: list[TakeoverCandidate] = []
        for r in latest.values():
            if r.resolved_ips:
                continue
            provider = _match_takeover(r.cname or "")
            if provider is None:
                continue
            candidates.append(
                TakeoverCandidate(
                    name=r.name,
                    target_id=r.target_id,
                    cname=r.cname,
                    provider=provider,
                    last_seen=r.discovered_at,
                )
            )
        candidates.sort(key=lambda c: c.last_seen, reverse=True)
        return TakeoverSignal(count=len(candidates), items=candidates[:_ITEMS_CAP])

    async def _spoofable_domains(self, project_id: UUID) -> SpoofableSignal:
        targets = (
            await self.session.execute(
                select(Target.id, Target.target_value).where(
                    Target.project_id == project_id,
                    Target.target_type.in_(_DOMAIN_TYPES),
                    Target.dns_status == TaskStatus.SUCCESS,
                )
            )
        ).all()
        if not targets:
            return SpoofableSignal(count=0, items=[])
        names = dict(targets)

        records = (
            await self.session.execute(
                select(
                    DnsRecord.target_id, DnsRecord.record_type, DnsRecord.value
                ).where(
                    DnsRecord.target_id.in_(list(names.keys())),
                    DnsRecord.record_type.in_([DnsRecordType.MX, DnsRecordType.TXT]),
                )
            )
        ).all()
        has_mx: set[UUID] = set()
        spf: dict[UUID, str] = {}
        for tid, rtype, value in records:
            rt = getattr(rtype, "value", rtype)
            if rt == DnsRecordType.MX.value:
                has_mx.add(tid)
            elif (
                rt == DnsRecordType.TXT.value
                and value
                and value.lower().startswith("v=spf1")
            ):
                spf[tid] = value.lower()

        items: list[SpoofableDomain] = []
        for tid in has_mx:
            reason = _spf_reason(spf.get(tid))
            if reason is None:
                continue
            items.append(
                SpoofableDomain(target_id=tid, target_value=names[tid], reason=reason)
            )
        items.sort(key=lambda d: d.target_value)
        return SpoofableSignal(count=len(items), items=items[:_ITEMS_CAP])

    async def _stale_targets(self, project_id: UUID) -> StaleSignal:
        cutoff = utc_now() - timedelta(days=_STALE_DAYS)
        last_completed = (
            select(
                Scan.target_id.label("tid"),
                func.max(func.coalesce(Scan.completed_at, Scan.started_at)).label(
                    "last"
                ),
            )
            .where(
                Scan.project_id == project_id,
                Scan.status == ScanStatus.COMPLETED.value,
            )
            .group_by(Scan.target_id)
            .subquery()
        )
        rows = (
            await self.session.execute(
                select(
                    Target.id,
                    Target.target_value,
                    Target.target_type,
                    last_completed.c.last,
                )
                .join(last_completed, last_completed.c.tid == Target.id, isouter=True)
                .where(Target.project_id == project_id)
            )
        ).all()

        never: list[StaleTarget] = []
        stale: list[StaleTarget] = []
        for tid, value, ttype, last in rows:
            tt = getattr(ttype, "value", ttype)
            if last is None:
                never.append(
                    StaleTarget(
                        target_id=tid,
                        target_value=value,
                        target_type=tt,
                        last_scanned_at=None,
                    )
                )
            elif last < cutoff:
                stale.append(
                    StaleTarget(
                        target_id=tid,
                        target_value=value,
                        target_type=tt,
                        last_scanned_at=last,
                    )
                )
        never.sort(key=lambda t: t.target_value)
        stale.sort(key=lambda t: t.last_scanned_at or utc_now())
        items = (never + stale)[:_ITEMS_CAP]
        return StaleSignal(never_scanned=len(never), stale=len(stale), items=items)

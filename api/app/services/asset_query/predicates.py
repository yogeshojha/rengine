from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Text, and_, cast, exists, false, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import aliased

from shared.definitions.ports import SENSITIVE_PORTS
from shared.models.http_asset import HttpAsset
from shared.models.port import Port
from shared.models.subdomain import Subdomain

HTTP_OK = 200
HTTP_REDIRECT = 300
HTTP_CLIENT = 400
HTTP_SERVER = 500
HTTP_MAX = 600
AUTH_STATUS = (401, 403)
STATUS_BUCKETS = {
    "2xx": (HTTP_OK, HTTP_REDIRECT),
    "3xx": (HTTP_REDIRECT, HTTP_CLIENT),
    "4xx": (HTTP_CLIENT, HTTP_SERVER),
    "5xx": (HTTP_SERVER, HTTP_MAX),
}
AUTH_RE = "login|sign ?in|log ?in|admin|dashboard|portal|console|authenticat"
EXPIRING_DAYS = 30


def status_class(name: str):
    if name == "none":
        return Subdomain.http_status.is_(None)
    bucket = STATUS_BUCKETS.get(name)
    if bucket is None:
        return false()
    return and_(Subdomain.http_status >= bucket[0], Subdomain.http_status < bucket[1])


def cert_state(name: str, now: datetime):
    if name == "self-signed":
        return Subdomain.tls_self_signed.is_(True)
    if name == "expired":
        return or_(
            Subdomain.tls_expired.is_(True),
            and_(Subdomain.tls_not_after.isnot(None), Subdomain.tls_not_after < now),
        )
    if name == "expiring":
        return and_(
            Subdomain.tls_not_after.isnot(None),
            Subdomain.tls_expired.isnot(True),
            Subdomain.tls_not_after >= now,
            Subdomain.tls_not_after < now + timedelta(days=EXPIRING_DAYS),
        )
    if name == "valid":
        return and_(
            Subdomain.tls_not_after.isnot(None),
            Subdomain.tls_not_after >= now + timedelta(days=EXPIRING_DAYS),
            Subdomain.tls_self_signed.isnot(True),
        )
    return false()


def port_match(condition):
    return exists().where(
        and_(
            Port.scan_id == Subdomain.scan_id,
            condition,
            func.jsonb_exists(cast(Subdomain.resolved_ips, JSONB), Port.ip),
        )
    )


def seen_earlier():
    earlier = aliased(Subdomain)
    return exists(
        select(1).where(
            earlier.target_id == Subdomain.target_id,
            earlier.name == Subdomain.name,
            earlier.scan_id != Subdomain.scan_id,
            earlier.discovered_at < Subdomain.discovered_at,
        )
    )


def live():
    return and_(Subdomain.http_status >= HTTP_OK, Subdomain.http_status < HTTP_CLIENT)


def auth():
    return or_(
        Subdomain.http_status.in_(AUTH_STATUS),
        Subdomain.page_title.op("~*")(AUTH_RE),
    )


def resolved():
    return func.jsonb_array_length(cast(Subdomain.resolved_ips, JSONB)) > 0


def sensitive():
    return port_match(Port.number.in_(SENSITIVE_PORTS))


def issues(now: datetime):
    return or_(
        cert_state("expired", now),
        cert_state("expiring", now),
        Subdomain.tls_self_signed.is_(True),
        Subdomain.http_status >= HTTP_SERVER,
        and_(
            live(),
            Subdomain.waf.is_(None),
            Subdomain.is_cdn.is_(False),
        ),
        sensitive(),
    )


def asset_match(scan_id, condition):
    return Subdomain.name.in_(
        select(HttpAsset.host).where(HttpAsset.scan_id == scan_id, condition)
    )


def ip_text():
    return cast(Subdomain.resolved_ips, Text)

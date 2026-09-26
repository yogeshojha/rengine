from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from shared.definitions.asset_query import SECRET_FLAGS, SECRET_QUERY
from shared.definitions.secrets import SecretState
from shared.models.secret import Secret

from . import predicates as preds
from .scope import QueryScope
from .terms import date_match, string_match, target_match
from .walk import flag_builder, walker


@dataclass(frozen=True)
class SecretQueryContext:
    scope: QueryScope
    now: datetime


_FLAG_BUILDERS = {
    "new": lambda ctx: preds.secret_is_new(ctx.scope),
    "exposed": lambda _ctx: Secret.state == SecretState.EXPOSED.value,
    "public": lambda _ctx: Secret.state == SecretState.PUBLIC.value,
    "expired": lambda _ctx: Secret.state == SecretState.EXPIRED.value,
    "secret": lambda _ctx: Secret.is_secret.is_(True),
    "shared": lambda _ctx: Secret.hosts > 1,
}


_BUILDERS = {
    "target": lambda c, _ctx: target_match(Secret.target_id, c),
    "secret": lambda c, _ctx: string_match(Secret.kind, c),
    "fingerprint": lambda c, _ctx: string_match(Secret.fingerprint, c),
    "group": lambda c, _ctx: string_match(Secret.group, c),
    "vendor": lambda c, _ctx: string_match(Secret.vendor, c),
    "subject": lambda c, _ctx: string_match(Secret.subject, c),
    "state": lambda c, _ctx: string_match(Secret.state, c),
    "source": lambda c, _ctx: string_match(Secret.source, c),
    "host": lambda c, _ctx: string_match(Secret.host, c),
    "url": lambda c, _ctx: string_match(Secret.url, c),
    "seen": lambda c, ctx: date_match(Secret.discovered_at, c, ctx.now, future=False),
    "is": flag_builder(_FLAG_BUILDERS, SECRET_FLAGS),
}


compile_secret_query = walker(SECRET_QUERY, _BUILDERS)

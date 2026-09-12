"""URL rules applied before an endpoint row is written."""

from __future__ import annotations

import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import func, or_, select

from shared.definitions.endpoints import (
    NOISE_IGNORED_PARAMS,
    NOISE_KEEP_PER_FAMILY,
    NOISE_SIBLING_CAP,
    NOISE_STATIC_EXTENSIONS,
    STATIC_CLASSES,
    NoiseRule,
    ParsedUrl,
    classify,
    fold_index_file,
    is_artifact,
    is_ignored_param,
    is_platform_noise,
    lang_of,
    parse_url,
    sibling_key,
    strip_session_path,
)
from shared.models.endpoint import Endpoint
from shared.models.http_asset import HttpAsset

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_CHUNK = 500
_HTTP_PORT = 80


def _children_of(parent: str):
    """Rows directly under a folder: its files and its child folders."""
    return Endpoint.path.op("~")(f"^{re.escape(parent)}[^/]+/?$")


@dataclass(frozen=True)
class NoisePolicy:
    enabled: bool = True
    drops: bool = True
    strip_params: bool = True
    static_extensions: frozenset[str] = frozenset(NOISE_STATIC_EXTENSIONS)
    ignored_params: frozenset[str] = frozenset(NOISE_IGNORED_PARAMS)
    keep_per_family: int = NOISE_KEEP_PER_FAMILY
    sibling_cap: int = NOISE_SIBLING_CAP

    @classmethod
    def from_stage(cls, cfg: dict | None) -> NoisePolicy:
        """From the url_discovery stage's resolved config."""
        cfg = cfg or {}
        return cls(
            enabled=bool(cfg.get("drop_noise", True)),
            static_extensions=frozenset(
                e.strip().lower().lstrip(".")
                for e in cfg.get("static_extensions", NOISE_STATIC_EXTENSIONS)
                if e and e.strip()
            ),
            ignored_params=frozenset(
                p.strip().lower()
                for p in cfg.get("ignored_params", NOISE_IGNORED_PARAMS)
                if p and p.strip()
            ),
            keep_per_family=int(cfg.get("keep_per_family", NOISE_KEEP_PER_FAMILY)),
            sibling_cap=int(cfg.get("sibling_cap", NOISE_SIBLING_CAP)),
        )

    @classmethod
    def protected(cls) -> NoisePolicy:
        """Nothing is dropped and parameters stay as seen. For URLs a person chose or a tool answered."""
        return cls(drops=False, strip_params=False)

    @classmethod
    def off(cls) -> NoisePolicy:
        return cls(enabled=False, drops=False)


@dataclass
class Sifted:
    kept: list[tuple[object, ParsedUrl]] = field(default_factory=list)
    dropped: Counter = field(default_factory=Counter)


class Sifter:
    """Applies a policy to a scan's observations, remembering what it has let through."""

    def __init__(
        self, session: Session, scan_id: uuid.UUID, policy: NoisePolicy | None = None
    ) -> None:
        self.session = session
        self.scan_id = scan_id
        self.policy = policy or NoisePolicy()
        self._families: dict[str, int] = {}
        self._family_lang: dict[str, str | None] = {}
        self._siblings: dict[tuple[str, str, str], int] = {}
        self._known: set[str] = set()
        self._https_hosts: frozenset[str] | None = None
        self._preferred_lang: dict[str, str] | None = None

    # ---------- public ----------

    def clean(self, url: str, default_scheme: str = "https") -> str:
        """The URL with tracking parameters, session paths and index files removed."""
        if not self.policy.enabled:
            return url
        value = url.strip()
        if "://" not in value:
            value = f"{default_scheme}://{value}"
        try:
            parts = urlsplit(value)
        except ValueError:
            return url
        path = fold_index_file(strip_session_path(parts.path or "/"))
        pairs = [
            (n, v)
            for n, v in parse_qsl(parts.query, keep_blank_values=True)
            if n
            and not (
                self.policy.strip_params
                and is_ignored_param(n, self.policy.ignored_params)
            )
        ]
        scheme = parts.scheme.lower()
        host = (parts.hostname or "").lower()
        if (
            scheme == "http"
            and parts.port in (None, _HTTP_PORT)
            and host in self._https_only()
        ):
            scheme = "https"
            netloc = (
                parts.netloc.replace(":80", "")
                if parts.port == _HTTP_PORT
                else parts.netloc
            )
        else:
            netloc = parts.netloc
        return urlunsplit((scheme, netloc, path, urlencode(pairs), ""))

    def sift(self, observations: list, default_scheme: str = "https") -> Sifted:
        out = Sifted()
        parsed_all: list[tuple[object, ParsedUrl]] = []
        for obs in observations:
            parsed = parse_url(
                self.clean(obs.url, default_scheme), default_scheme=default_scheme
            )
            if parsed is None:
                out.dropped["rejected"] += 1
                continue
            parsed_all.append((obs, parsed))
        if not self.policy.enabled or not self.policy.drops:
            out.kept = parsed_all
            return out
        self._prime(parsed_all)
        for obs, parsed in parsed_all:
            rule = None if parsed.signature in self._known else self._judge(parsed)
            if rule is None:
                out.kept.append((obs, parsed))
                self._known.add(parsed.signature)
            else:
                out.dropped[rule] += 1
        return out

    # ---------- rules ----------

    def _judge(self, p: ParsedUrl) -> str | None:
        rule = self._row_rule(p)
        if rule is not None or p.path == "/":
            return rule
        return self._crowd_rule(p)

    def _row_rule(self, p: ParsedUrl) -> str | None:
        """Rules a URL fails on its own."""
        if is_artifact(p.path):
            return NoiseRule.ARTIFACT.value
        if (p.extension or "") in self.policy.static_extensions or classify(
            p.path, p.extension
        ) in STATIC_CLASSES:
            return NoiseRule.STATIC.value
        if is_platform_noise(p.path, p.params, p.param_values):
            return NoiseRule.PLATFORM.value
        return None

    def _crowd_rule(self, p: ParsedUrl) -> str | None:
        """Rules a URL fails because of what the scan already holds."""
        policy = self.policy
        family = p.family
        lang = lang_of(p.path)
        if lang is not None:
            preferred = self._preferred().get(p.host) or self._family_lang.get(family)
            if preferred is not None and preferred != lang:
                return NoiseRule.LOCALE.value
            self._family_lang.setdefault(family, lang)
        seen = self._families.get(family, 0)
        if seen >= policy.keep_per_family:
            return NoiseRule.FAMILY.value
        key = sibling_key(p.path, p.extension)
        if key is not None:
            skey = (p.host, key[0], key[1])
            siblings = self._siblings.get(skey, 0)
            if siblings >= policy.sibling_cap:
                return NoiseRule.SIBLINGS.value
            self._siblings[skey] = siblings + 1
        self._families[family] = seen + 1
        return None

    # ---------- state ----------

    def _prime(self, parsed: list[tuple[object, ParsedUrl]]) -> None:
        """Load what the scan already holds for the rows, families and folders in this batch."""
        signatures = sorted({p.signature for _, p in parsed} - self._known)
        for start in range(0, len(signatures), _CHUNK):
            chunk = signatures[start : start + _CHUNK]
            self._known.update(
                self.session.execute(
                    select(Endpoint.signature).where(
                        Endpoint.scan_id == self.scan_id, Endpoint.signature.in_(chunk)
                    )
                )
                .scalars()
                .all()
            )
        families = {p.family for _, p in parsed if p.family not in self._families}
        if families:
            rows = self.session.execute(
                select(Endpoint.family, func.count(), func.min(Endpoint.path))
                .where(Endpoint.scan_id == self.scan_id, Endpoint.family.in_(families))
                .group_by(Endpoint.family)
            ).all()
            for fam, count, sample in rows:
                self._families[fam] = int(count)
                self._family_lang.setdefault(fam, lang_of(sample or ""))
            for fam in families:
                self._families.setdefault(fam, 0)
        keys = {}
        for _, p in parsed:
            key = sibling_key(p.path, p.extension)
            if key is None:
                continue
            skey = (p.host, key[0], key[1])
            if skey not in self._siblings:
                keys[skey] = key
        if not keys:
            return
        by_host: dict[str, set[str]] = {}
        for host, parent, _kind in keys:
            by_host.setdefault(host, set()).add(parent)
        for host, parents in by_host.items():
            rows = self.session.execute(
                select(Endpoint.path, Endpoint.extension).where(
                    Endpoint.scan_id == self.scan_id,
                    Endpoint.host == host,
                    or_(*(_children_of(parent) for parent in parents)),
                )
            ).all()
            counts: Counter = Counter()
            for path, extension in rows:
                key = sibling_key(path, extension)
                if key is not None:
                    counts[(host, key[0], key[1])] += 1
            for skey in keys:
                if skey[0] == host:
                    self._siblings[skey] = counts.get(skey, 0)

    def _https_only(self) -> frozenset[str]:
        """Hosts whose http root answers with a redirect to https."""
        if self._https_hosts is None:
            rows = self.session.execute(
                select(HttpAsset.host, HttpAsset.location).where(
                    HttpAsset.scan_id == self.scan_id,
                    HttpAsset.scheme == "http",
                    HttpAsset.location.isnot(None),
                )
            ).all()
            self._https_hosts = frozenset(
                host.lower()
                for host, location in rows
                if (location or "").lower().startswith(f"https://{host.lower()}")
            )
        return self._https_hosts

    def _preferred(self) -> dict[str, str]:
        """The language each host's root redirects to."""
        if self._preferred_lang is None:
            rows = self.session.execute(
                select(HttpAsset.host, HttpAsset.location).where(
                    HttpAsset.scan_id == self.scan_id,
                    HttpAsset.location.isnot(None),
                    func.coalesce(HttpAsset.path, "/") == "/",
                )
            ).all()
            langs: dict[str, str] = {}
            for host, location in rows:
                try:
                    path = urlsplit(location or "").path or "/"
                except ValueError:
                    continue
                lang = lang_of(path)
                if lang:
                    langs.setdefault(host.lower(), lang)
            self._preferred_lang = langs
        return self._preferred_lang

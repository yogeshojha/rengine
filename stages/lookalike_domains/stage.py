from __future__ import annotations

import ipaddress
import secrets
import socket
from concurrent.futures import ThreadPoolExecutor

import httpx
from sqlalchemy import select

from shared.definitions.domains import registrable_domain
from shared.definitions.intensity import TransportTool
from shared.definitions.lookalikes import (
    FETCH_MAX_BYTES,
    FETCH_TIMEOUT,
    FETCH_USER_AGENT,
    FETCH_WORKERS,
    LOOKALIKE_STAGE,
    MAX_FETCHES,
    MAX_PERMUTATIONS,
    MAX_RDAP,
    MAX_REDIRECTS,
    NO_MAIL,
    THREAT_VERDICTS,
    VERDICT_RANK,
    Verdict,
)
from shared.enums.scan import Intensity, Phase, StageGroup, StageRole
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.target import Target
from shared.services import lookalikes
from shared.services.lookalikes import Lookalike, Page, Records
from shared.utils.net import is_public_address
from shared.utils.text import counted
from shared.utils.validation import normalize_domain
from stages.base import Stage, StageResult
from stages.dns_posture.lookup import DnsxLookup
from stages.lookalike_domains.config import LookalikeDomainsConfig
from tools.dnsx.client import DnsxClient, DnsxError
from tools.whois.parser import parse_domain_response
from tools.whois.providers.whoisit import RDAPProvider, RDAPProviderError

logger = get_logger(__name__)

_RUN_TIMEOUT = 900
_MIN_THREADS = 10
_TYPES = ("a", "aaaa", "mx", "ns")
_KEPT_BODY = 100_000


def _records(found: dict[str, list[str]] | None) -> Records:
    found = found or {}
    return Records(
        a=sorted(set(found.get("a", []))),
        aaaa=sorted(set(found.get("aaaa", []))),
        mx=sorted(
            {v.strip().lower().rstrip(".") for v in found.get("mx", [])} - NO_MAIL
        ),
        ns=sorted({v.strip().lower().rstrip(".") for v in found.get("ns", [])}),
    )


def _tld(name: str) -> str:
    root = registrable_domain(name) or name
    return root.partition(".")[2] or root


def _probes(names) -> dict[str, str]:
    """An unregistered name per TLD."""
    token = secrets.token_hex(8)
    return {tld: f"rngx-{token}.{tld}" for tld in {_tld(n) for n in names}}


def _registered(item: Lookalike, wildcard: dict[str, set[str]]) -> bool:
    rec = item.records
    if rec.ns or rec.mx:
        return True
    return rec.addressed and not set(rec.addresses) <= wildcard.get(
        _tld(item.domain), set()
    )


def _is_public(address: str) -> bool:
    try:
        return is_public_address(ipaddress.ip_address(address))
    except ValueError:
        return False


def _public(addresses: list[str]) -> list[str]:
    return [address for address in addresses if _is_public(address)]


def _addresses(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError:
        return []
    return list(dict.fromkeys(str(info[4][0]) for info in infos))


def _page(response: httpx.Response, url: str) -> Page:
    body = b""
    for chunk in response.iter_bytes():
        body += chunk
        if len(body) >= FETCH_MAX_BYTES:
            break
    return Page(
        status=response.status_code,
        final_url=url,
        title=lookalikes.title_of(body),
        body=body,
    )


def _fetch(
    client: httpx.Client, url: str, known: list[str] | None, *, vet: bool
) -> Page | None:
    """GET with redirects followed by hand, each hop sent to a public address when vet is set."""
    for _ in range(MAX_REDIRECTS + 1):
        target = httpx.URL(url)
        send, headers, extensions = target, {}, {}
        if vet:
            host = target.raw_host.decode("ascii")
            found = _public(known if known is not None else _addresses(host))
            if not found:
                return None
            send = target.copy_with(host=min(found, key=lambda a: ":" in a))
            headers = {"Host": target.netloc.decode("ascii")}
            if target.scheme == "https":
                extensions = {"sni_hostname": host}
        with client.stream(
            "GET", send, headers=headers, extensions=extensions
        ) as response:
            if not response.has_redirect_location:
                return _page(response, str(target))
            url = str(target.join(response.headers["location"]))
        known = None
    return None


class LookalikeDomainsStage(Stage):
    name = LOOKALIKE_STAGE
    title = "Lookalike domains"
    description = "Registered typo, homoglyph and TLD variants of the target's domain."
    phase = Phase.DISCOVERY.value
    group = StageGroup.ANALYSIS.value
    role = StageRole.CAPABILITY.value
    applies_to = frozenset({TargetType.DOMAIN.value, TargetType.URL.value})
    tools = ("dnsx",)
    transport_tool = TransportTool.DNSX.value
    touches_target = True
    passive_capable = True
    config_model = LookalikeDomainsConfig

    def run(self) -> StageResult:
        self._check_abort()
        cfg: LookalikeDomainsConfig = self.cfg
        host = normalize_domain(self.ctx.target_value)
        apex = registrable_domain(host) or host
        if not apex or "." not in apex:
            return StageResult(counts={"permutations": 0, "lookalikes": 0})

        names = lookalikes.permutations(
            apex, tld_swap=cfg.tld_swap, words=cfg.words, cap=MAX_PERMUTATIONS
        )
        self.emit_progress(f"resolving {counted(len(names), 'permutation')} of {apex}")
        try:
            client = DnsxClient(
                timeout=_RUN_TIMEOUT,
                threads=max(self.transport.threads, _MIN_THREADS),
                query_timeout=self.transport.timeout,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("dnsx"),
            )
        except DnsxError as exc:
            return StageResult(warnings=[str(exc)], partial=True)
        lookup = DnsxLookup(client, self.net_options())

        probes = _probes(n for n, _ in names)
        answers = lookup.records(
            [apex, *probes.values(), *(n for n, _ in names)], _TYPES
        )
        silent = [n for n, _ in names if n not in answers]
        self._check_abort()
        if silent:
            answers.update(lookup.records(silent, _TYPES))
        self._check_abort()

        apex_ns = set(_records(answers.get(apex)).ns)
        items = [
            Lookalike(domain=n, technique=t, records=_records(answers.get(n)))
            for n, t in names
        ]
        wildcard = {
            tld: set(_records(answers.get(probe)).addresses)
            for tld, probe in probes.items()
        }
        items = [i for i in items if _registered(i, wildcard)]
        tracked = self._tracked([i.domain for i in items])

        passive = self.ctx.resolved.intensity == Intensity.PASSIVE.value
        fetch = cfg.page_similarity and not passive
        warnings: list[str] = []
        fetched, partial = 0, False
        if fetch and items:
            fetched, warnings, partial = self._fetch_pages(apex, items)

        for item in items:
            item.parked = lookalikes.parked(item.records, item.page)
            item.link_reason = lookalikes.link_reason(
                apex=apex,
                records=item.records,
                page=item.page,
                apex_ns=apex_ns,
                tracked=item.domain in tracked,
            )
            item.verdict = lookalikes.verdict(item)
        items.sort(key=lambda i: (VERDICT_RANK[i.verdict], i.domain))

        if cfg.registration and items:
            missed = self._registration(items)
            if missed:
                warnings.append(
                    f"{counted(missed, 'lookalike')} without a registration date."
                )

        stored = lookalikes.replace_rows(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            apex=apex,
            items=items,
        )
        self.session.commit()
        threats = sum(1 for i in items if i.verdict in THREAT_VERDICTS)
        self.emit_progress(f"{counted(stored, 'lookalike')} registered")
        return StageResult(
            counts={
                "permutations": len(names),
                "lookalikes": stored,
                "lookalike_threats": threats,
                "pages_fetched": fetched,
            },
            warnings=warnings,
            partial=partial,
        )

    def _tracked(self, domains: list[str]) -> set[str]:
        if not domains:
            return set()
        rows = self.session.execute(
            select(Target.target_value).where(
                Target.project_id == self.ctx.project_id,
                Target.target_value.in_(domains),
            )
        ).scalars()
        return {str(v).lower() for v in rows}

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=FETCH_TIMEOUT,
            follow_redirects=False,
            verify=False,  # noqa: S501
            proxy=self.net_options().proxy_url or None,
            headers={"User-Agent": FETCH_USER_AGENT},
            limits=httpx.Limits(max_keepalive_connections=0),
        )

    @staticmethod
    def _get(
        client: httpx.Client,
        domain: str,
        known: list[str] | None = None,
        *,
        vet: bool = False,
    ) -> Page | None:
        for scheme in ("https", "http"):
            try:
                page = _fetch(client, f"{scheme}://{domain}/", known, vet=vet)
            except (httpx.HTTPError, httpx.InvalidURL, ValueError, UnicodeError):
                continue
            if page is not None:
                return page
        return None

    def _fetch_pages(
        self, apex: str, items: list[Lookalike]
    ) -> tuple[int, list[str], bool]:
        """Fetch each addressed lookalike and score it against the apex page."""
        try:
            client = self._client()
        except (ImportError, ValueError):
            return 0, ["Pages not fetched. The scan proxy is not supported."], True
        vet = not self.net_options().proxy_url
        named = [i for i in items if i.records.addressed]
        addressed = [i for i in named if not vet or _public(i.records.addresses)]
        addressed.sort(key=lambda i: (i.technique == "homoglyph", i.domain))
        chosen, cut = addressed[:MAX_FETCHES], len(addressed) - MAX_FETCHES
        warnings = []
        if private := len(named) - len(addressed):
            warnings.append(
                f"{counted(private, 'lookalike')} not fetched. "
                "They resolve only to private or reserved addresses."
            )
        self.emit_progress(f"comparing {counted(len(chosen), 'page')} to {apex}")
        with client:
            original = self._get(client, apex)
            reference = lookalikes.fuzzy_hash(original.body) if original else None

            def one(item: Lookalike) -> None:
                item.page = self._get(
                    client, item.domain, item.records.addresses, vet=vet
                )
                if item.page is not None and item.page.body:
                    item.similarity = lookalikes.similarity(reference, item.page.body)
                    item.page.body = item.page.body[:_KEPT_BODY]

            with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
                step = FETCH_WORKERS * 2
                for start in range(0, len(chosen), step):
                    self._check_abort()
                    list(pool.map(one, chosen[start : start + step]))
        if cut > 0:
            warnings.append(
                f"Page fetch capped at {MAX_FETCHES}. "
                f"{counted(cut, 'lookalike')} not fetched."
            )
        return len(chosen), warnings, False

    def _registration(self, items: list[Lookalike]) -> int:
        """Registrar and creation date, highest verdict first."""
        ranked = [i for i in items if i.verdict != Verdict.LINKED.value][:MAX_RDAP]
        provider = RDAPProvider(proxy_url=self.net_options().proxy_url)
        missed = 0
        for item in ranked:
            self._check_abort()
            try:
                parsed = parse_domain_response(
                    provider.lookup_domain(item.domain), item.domain
                )
            except (RDAPProviderError, ValueError, TypeError) as exc:
                logger.debug("rdap lookup failed", domain=item.domain, error=str(exc))
                missed += 1
                continue
            item.registered_at = parsed.registration_date
            registrar = next(
                (e.name for e in parsed.entities.registrar if e.name), None
            )
            item.registrar = registrar
        return missed

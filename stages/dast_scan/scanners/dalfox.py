"""dalfox over the request items, gated by a reflection probe so it fuzzes only what reflects."""

from __future__ import annotations

import secrets
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from shared.definitions.scan_surface import Tier
from shared.definitions.vulnerabilities import SCANNER_LABELS, CoverageStatus, Scanner
from shared.logging import get_logger
from shared.services.scan_resolve import redact_secrets
from shared.services.scan_surface import SurfacePlan
from shared.utils.datetime import utc_now
from stages.vulnerability_scan.scanners.base import (
    Coverage,
    ScannerResult,
    VulnScanner,
)
from tools.dalfox import DalfoxClient, DalfoxError, DalfoxOptions
from tools.httpx.client import HttpxClient, HttpxError
from tools.httpx.parser import parse_httpx_record

logger = get_logger(__name__)

_MARKER_LEN = 12
_PROBE_TIMEOUT = 8
_PER_INVOCATION = 100
_MIN_BATCH_SECONDS = 30


def _marker() -> str:
    return "rx" + secrets.token_hex(_MARKER_LEN // 2)


def _mark_url(url: str, marker: str) -> str:
    """The URL with every parameter value replaced by the marker."""
    parts = urlsplit(url)
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    if not pairs:
        return url
    marked = [(name, marker) for name, _ in pairs]
    return urlunsplit(parts._replace(query=urlencode(marked)))


class DalfoxScanner(VulnScanner):
    name = Scanner.DALFOX.value
    label = SCANNER_LABELS[Scanner.DALFOX.value]
    binary = "dalfox"

    def run(self) -> ScannerResult:
        ctx = self.ctx
        ok, reason = self.availability()
        if not ok:
            return self.skipped(reason or "dalfox is not installed on the scanner")
        plan: SurfacePlan = ctx.surface
        if not plan.requests:
            return self.skipped("This scan found no request with parameters to fuzz.")

        reflecting = self._reflecting(plan)
        if reflecting is None:
            coverage = Coverage(
                group=self.label,
                tier=Tier.DAST.value,
                severities=list(ctx.cfg.severities),
                hosts_total=len(plan.requests),
                rate_limit=ctx.transport.rate,
                concurrency=ctx.transport.threads,
            )
            coverage.status = CoverageStatus.PARTIAL.value
            coverage.error = (
                "The reflection probe did not complete. Nothing was fuzzed."
            )
            coverage.ended_at = utc_now()
            return ScannerResult(coverage=[coverage])
        coverage = Coverage(
            group=self.label,
            tier=Tier.DAST.value,
            severities=list(ctx.cfg.severities),
            hosts_total=len(plan.requests),
            hosts_covered=len(reflecting),
            rate_limit=ctx.transport.rate,
            concurrency=ctx.transport.threads,
        )
        if not reflecting:
            coverage.status = CoverageStatus.COMPLETED.value
            coverage.error = (
                "No parameter reflected in the response, so nothing was fuzzed."
            )
            coverage.ended_at = utc_now()
            return ScannerResult(coverage=[coverage])

        ctx.progress(
            f"{self.label.lower()}: {len(reflecting)} of {len(plan.requests)} requests reflect a parameter"
        )
        result = ScannerResult()
        result.coverage.append(self._fuzz(reflecting, coverage))
        return result

    def _reflecting(self, plan: SurfacePlan) -> list[str] | None:
        """One marked GET per request; keep the URLs whose marker comes back in the body."""
        ctx = self.ctx
        marker = _marker()
        probes: dict[str, str] = {}
        for item in plan.requests:
            marked = _mark_url(item.value, marker)
            if marked != item.value:
                probes[marked] = item.value
        if not probes:
            return []
        try:
            client = HttpxClient(
                rate_limit=ctx.transport.rate,
                threads=ctx.transport.threads,
                timeout=_PROBE_TIMEOUT,
                proxy_url=ctx.net.proxy_url,
                headers=ctx.net.headers,
                follow_redirects=False,
                **ctx.wiring("httpx"),
            )
        except HttpxError as exc:
            logger.warning("reflection probe unavailable", error=str(exc))
            return list(probes.values())
        reflecting: list[str] = []
        outcome = None
        with client.stream_probe(list(probes)) as stream:
            outcome = stream
            for record in stream.records:
                if ctx.aborted():
                    break
                fields = parse_httpx_record(record)
                key = (record.get("input") or "").strip() or fields.get("url")
                body = fields.get("response_body") or ""
                if key in probes and marker in body:
                    reflecting.append(probes[key])
        if outcome is not None and (
            outcome.timed_out or outcome.return_code not in (0, None)
        ):
            return None
        return reflecting

    def _fuzz(self, urls: list[str], coverage: Coverage) -> Coverage:  # noqa: PLR0915
        ctx = self.ctx
        secrets_list = [v for v in (ctx.net.headers or {}).values() if v]
        options = DalfoxOptions(
            workers=ctx.transport.threads,
            rate=ctx.transport.rate or 1,
            timeout=ctx.transport.timeout,
            retries=ctx.transport.retries,
            proxy_url=ctx.net.proxy_url,
            headers=dict(ctx.net.headers or {}),
            follow_redirects=bool(ctx.resolved.follow_redirects),
        )
        try:
            client = DalfoxClient(
                options=options,
                **ctx.wiring("dalfox"),
            )
        except DalfoxError as exc:
            coverage.status = CoverageStatus.SKIPPED.value
            coverage.error = str(exc)[:2000]
            coverage.ended_at = utc_now()
            return coverage

        wanted = set(ctx.cfg.severities)

        def _on_finding(finding) -> None:
            if finding.severity not in wanted:
                return
            if ctx.keep_evidence():
                finding.request = redact_secrets(finding.request, secrets_list)
                finding.response = redact_secrets(finding.response, secrets_list)
            else:
                finding.request = None
                finding.response = None
            stored = ctx.store([finding])
            coverage.findings += stored

        budget = ctx.cfg.max_minutes * 60 if ctx.cfg.max_minutes else None
        deadline = None if budget is None else time.monotonic() + budget
        total = 0
        errors = []
        notes = []
        if self._oast.enabled:
            notes.append("dalfox does not do out-of-band testing.")
        for start in range(0, len(urls), _PER_INVOCATION):
            if ctx.aborted():
                break
            timeout = None
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining < _MIN_BATCH_SECONDS:
                    left = len(urls) - start
                    notes.append(
                        f"{left} requests not fuzzed. The {ctx.cfg.max_minutes}-minute "
                        "budget ran out."
                    )
                    coverage.status = CoverageStatus.PARTIAL.value
                    break
                timeout = int(remaining)
            batch = urls[start : start + _PER_INVOCATION]
            run = client.scan(
                batch, on_finding=_on_finding, should_stop=ctx.aborted, timeout=timeout
            )
            total += run.requests or 0
            if run.error:
                errors.append(run.error)
            coverage.command = run.command
        coverage.requests_sent = total or None
        coverage.ended_at = utc_now()
        if errors:
            coverage.status = CoverageStatus.PARTIAL.value
            notes.insert(0, errors[0][:1500])
        if notes:
            coverage.error = " ".join(notes)[:2000]
        return coverage


__all__ = ["DalfoxScanner"]

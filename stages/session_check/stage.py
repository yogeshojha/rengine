from __future__ import annotations

import hashlib

import httpx

from shared.enums.scan import Phase, StageGroup, StageRole
from shared.enums.target import TargetType
from shared.logging import get_logger
from stages.base import ALL_TARGETS, Stage, StageResult
from stages.session_check.config import SessionCheckConfig

logger = get_logger(__name__)

_UNAUTHORISED = (401, 403)
_SERVER_ERROR = 500
_BODY_SAMPLE = 64 * 1024


class Verdict:
    LIVE = "live"
    IGNORED = "ignored"
    REFUSED = "refused"
    UNANSWERED = "unanswered"


class SessionCheckStage(Stage):
    name = "session_check"
    title = "Session Check"
    description = "Check the scan context's credentials before the scan runs."
    phase = Phase.DISCOVERY.value
    depends_on = frozenset({"seed_resolution"})
    group = StageGroup.WEB.value
    role = StageRole.SUPPORT.value
    consumes = frozenset()
    produces = frozenset()
    applies_to = ALL_TARGETS
    touches_target = True
    deferrable = False
    config_model = SessionCheckConfig

    def should_run(self) -> bool:
        return bool(self.cfg.enabled and self.ctx.resolved.auth_headers())

    def run(self) -> StageResult:
        self._check_abort()
        candidates = self._candidates()
        if not candidates:
            return self._result(
                Verdict.UNANSWERED,
                f"A {self.ctx.target_type} target has no URL to request. The session "
                "was not checked.",
            )

        client = self._client()
        try:
            for url in candidates:
                self._check_abort()
                outcome = self._compare(client, url)
                if outcome is not None:
                    verdict, detail = outcome
                    return self._result(verdict, detail, url=url)
        finally:
            client.close()

        return self._result(
            Verdict.UNANSWERED,
            f"nothing answered at {' or '.join(candidates)}. The session could "
            "not be checked",
        )

    def _candidates(self) -> list[str]:
        value = self.ctx.target_value.strip().rstrip("/")
        if not value:
            return []
        if self.ctx.target_type == TargetType.URL.value:
            return [value]
        if self.ctx.target_type != TargetType.DOMAIN.value:
            return []
        return [f"https://{value}", f"http://{value}"]

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.cfg.timeout,
            follow_redirects=True,
            verify=False,  # noqa: S501
            proxy=self.ctx.resolved.proxy_url or None,
        )

    def _compare(self, client: httpx.Client, url: str) -> tuple[str, str] | None:
        resolved = self.ctx.resolved
        signed = self._get(client, url, resolved.headers)
        if signed is None:
            return None
        bare = self._get(client, url, resolved.headers_without_auth())
        if bare is None:
            return None

        if signed.status in _UNAUTHORISED:
            return (
                Verdict.REFUSED,
                f"{url} answered {signed.status} with the scan context's credentials. "
                "They are wrong, expired or not accepted here",
            )
        if signed.status == bare.status and signed.digest == bare.digest:
            return (
                Verdict.IGNORED,
                f"{url} answered {signed.status} and the same {signed.length:,} bytes "
                "with and without the credentials, nothing in this scan is "
                "authenticated",
            )
        changed = (
            f"status {bare.status} to {signed.status}"
            if signed.status != bare.status
            else f"a different body, {bare.length:,} to {signed.length:,} bytes"
        )
        return (
            Verdict.LIVE,
            f"{url} answers differently with the credentials: {changed}",
        )

    def _get(self, client: httpx.Client, url: str, headers: dict) -> _Answer | None:
        try:
            response = client.get(url, headers=headers or None)
        except (httpx.HTTPError, ValueError) as e:
            logger.info("session check could not reach %s: %s", url, e)
            return None
        if response.status_code >= _SERVER_ERROR:
            return None
        body = response.content[:_BODY_SAMPLE]
        return _Answer(
            status=response.status_code,
            digest=hashlib.sha256(body).hexdigest(),
            length=len(response.content),
        )

    def _result(self, verdict: str, detail: str, url: str | None = None) -> StageResult:
        counts = {"checked": 1 if url else 0}
        if verdict == Verdict.LIVE:
            self.emit_progress(detail)
            return StageResult(counts=counts)
        self.emit_progress(detail)
        return StageResult(counts=counts, warnings=[detail], partial=True)


class _Answer:
    __slots__ = ("digest", "length", "status")

    def __init__(self, status: int, digest: str, length: int) -> None:
        self.status = status
        self.digest = digest
        self.length = length

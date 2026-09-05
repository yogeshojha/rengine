"""On-demand endpoint verification for one branch of the outline."""

from __future__ import annotations

import uuid

from celery import shared_task
from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB

from app.database import get_sync_session
from app.orchestrator.stage import load_resolved
from shared.definitions.endpoints import PROBE_COVERAGE_SOURCE, STATIC_CLASSES
from shared.definitions.vulnerabilities import CoverageStatus
from shared.logging import get_logger
from shared.models.endpoint import Endpoint, EndpointCoverage
from shared.models.scan import Scan
from shared.services import endpoint_inventory
from shared.services.endpoint_inventory import EndpointObservation
from shared.services.scope_filter import matches_any
from shared.utils.datetime import utc_now
from stages.endpoint_probe.config import EndpointProbeConfig
from tools.httpx.client import HttpxClient, HttpxError
from tools.httpx.parser import parse_httpx_record

logger = get_logger(__name__)

MAX_BRANCH_URLS = 2000


def branch_candidates(scan_id: uuid.UUID, host: str, dir_path: str | None):
    """Unverified, non-static endpoints under a folder, most useful first."""
    flagged = func.jsonb_array_length(cast(Endpoint.interest, JSONB)) > 0
    query = select(Endpoint.url, Endpoint.path).where(
        Endpoint.scan_id == scan_id,
        Endpoint.host == host,
        Endpoint.is_probed.is_(False),
        Endpoint.endpoint_class.notin_(tuple(STATIC_CLASSES)),
    )
    if dir_path and dir_path != "/":
        prefix = dir_path if dir_path.endswith("/") else f"{dir_path}/"
        escaped = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(Endpoint.dir_path.like(f"{escaped}%", escape="\\"))
    return query.order_by(
        flagged.desc(),
        (Endpoint.param_count > 0).desc(),
        Endpoint.depth.asc(),
        Endpoint.url.asc(),
    )


@shared_task(bind=True, name="app.tasks.endpoints.verify_branch", max_retries=0)
def verify_branch(
    self,  # noqa: ARG001
    scan_id: str,
    host: str,
    dir_path: str | None = None,
    limit: int = 500,
) -> dict:
    started = utc_now()
    cap = max(1, min(int(limit), MAX_BRANCH_URLS))
    with get_sync_session() as session:
        scan = session.get(Scan, uuid.UUID(scan_id))
        if scan is None:
            return {"error": "scan not found"}
        resolved = load_resolved(scan.execution_config)
        cfg = EndpointProbeConfig()
        rows = session.execute(
            branch_candidates(scan.id, host, dir_path).limit(cap * 4)
        ).all()
        excluded = resolved.excluded_paths or []
        if excluded:
            rows = [r for r in rows if not matches_any(r.path, excluded)]
        selected = [r.url for r in rows[:cap]]
        skipped = max(0, len(rows) - len(selected))
        where = f"{dir_path or '/'} on {host}"
        if not selected:
            return {"verified": 0, "answered": 0}

        try:
            client = HttpxClient(
                rate_limit=cfg.rate,
                threads=cfg.threads,
                timeout=cfg.timeout,
                proxy_url=resolved.proxy_url,
                headers=dict(resolved.headers or {}),
                follow_redirects=cfg.follow_redirects,
                extra_args=resolved.tool_args("httpx"),
            )
        except HttpxError as e:
            _store(
                session,
                scan,
                started,
                len(selected),
                0,
                None,
                CoverageStatus.SKIPPED.value,
                str(e)[:2000],
                f"On-demand verification of {where}",
            )
            logger.warning("httpx unavailable, branch stays unverified")
            return {"verified": 0, "answered": 0, "error": str(e)[:200]}

        observations: list[EndpointObservation] = []
        with client.stream_probe(selected) as stream:
            for record in stream.records:
                fields = parse_httpx_record(record)
                url = fields.get("url")
                if not url:
                    continue
                observations.append(
                    EndpointObservation(
                        url=url,
                        is_probed=True,
                        status_code=fields.get("status_code"),
                        content_type=fields.get("content_type"),
                        content_length=fields.get("content_length"),
                        title=fields.get("title"),
                        words=fields.get("words"),
                        lines=fields.get("lines"),
                        response_time=fields.get("response_time"),
                        redirect_location=fields.get("location"),
                        content_hash=fields.get("content_hash"),
                        tech=list(fields.get("tech") or []),
                        methods=[fields["method"]] if fields.get("method") else [],
                    )
                )
        written = endpoint_inventory.verify(
            session, scan_id=scan.id, observations=observations
        )
        status = (
            CoverageStatus.PARTIAL.value if skipped else CoverageStatus.COMPLETED.value
        )
        reason = f"On-demand verification of {where}" + (
            f"; {skipped} more were left unverified by the limit of {cap}."
            if skipped
            else ""
        )
        _store(
            session,
            scan,
            started,
            len(selected) + skipped,
            len(selected),
            written.updated,
            status,
            None,
            reason,
        )
        logger.info(
            "verified branch", host=host, dir_path=dir_path, requested=len(selected)
        )
        return {"verified": len(selected), "answered": written.updated}


def _store(
    session,
    scan: Scan,
    started,
    total: int,
    probed: int,
    answered: int | None,
    status: str,
    error: str | None,
    reason: str,
) -> None:
    ended = utc_now()
    session.add(
        EndpointCoverage(
            scan_id=scan.id,
            target_id=scan.target_id,
            project_id=scan.project_id,
            source=PROBE_COVERAGE_SOURCE,
            tool="httpx",
            status=status,
            hosts_total=1,
            hosts_scanned=1,
            urls_found=total,
            urls_probed=probed,
            urls_stored=answered,
            errors=None if answered is None else max(0, probed - answered),
            capped=total > probed,
            cap_reason=reason,
            error=error,
            started_at=started,
            ended_at=ended,
            duration_seconds=round((ended - started).total_seconds(), 2),
        )
    )
    session.commit()

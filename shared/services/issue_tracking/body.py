"""Issue title, labels, body and comments."""

from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from shared.config import base_settings
from shared.definitions.evidence import evidence_label
from shared.definitions.issue_trackers import (
    MAX_EVIDENCE_CHARS,
    MAX_GROUP_LOCATIONS,
    MAX_TITLE,
    TRACKER_LABEL,
    CommentKind,
    TrackerSpec,
)
from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import SEVERITY_LABELS
from shared.services.issue_trackers.document import Doc, rendered_size
from shared.services.scan_resolve import MASK, redact_credentials, redact_message
from shared.services.secret_mining.detectors import find as find_secrets
from shared.utils.net import authority
from shared.utils.text import clip, counted, strip_control

MAX_REFERENCES = 8
MAX_PROSE = 3000
MAX_RESPONSE = 1500
MAX_LOCATION = 300
MIN_SHOWN = 5
_ASSIGNED_SECRET = re.compile(
    r"(?i)((?<![\w.-])[\"']?[\w.-]{0,128}?(?:pass(?:word|wd)?|secret|token|api[_-]?key"
    r"|access[_-]?key|private[_-]?key|credential)[\w.-]{0,128}[\"']?\s*[:=]\s*)"
    r"(\"[^\"\n]*\"|'[^'\n]*'|[^\s,;&}\"']+)"
)
_SPACE = re.compile(r"\s+")
VULN_TAB = SurfaceDimension.VULNERABILITIES.value


def _clip(text: str | None, limit: int) -> str:
    return clip(strip_control(text or "").strip(), limit)


def finding_link(scan_id: Any, vuln_id: Any) -> str:
    query = urlencode({"tab": VULN_TAB, "vuln": str(vuln_id)})
    return f"{base_settings().ui_base_url}/scans/{scan_id}?{query}"


def check_link(scan_id: Any, template_id: str) -> str:
    query = urlencode({"tab": VULN_TAB, "vuln_q": f"template:{template_id}"})
    return f"{base_settings().ui_base_url}/scans/{scan_id}?{query}"


def scan_link(scan_id: Any) -> str:
    return f"{base_settings().ui_base_url}/scans/{scan_id}"


def _where(vuln: Any) -> str:
    return authority(vuln.matched_at or "", vuln.host) or vuln.matched_at or ""


def title_for(vulns: Sequence[Any], target_value: str, *, grouped: bool) -> str:
    lead = vulns[0]
    name = _SPACE.sub(
        " ", strip_control(lead.template_name or lead.template_id)
    ).strip()
    where = _SPACE.sub(" ", target_value if grouped else _where(lead)).strip()
    title = f"{name} on {where}"
    return clip(title, MAX_TITLE)


def marker(issue_id: uuid.UUID) -> str:
    """Reference that identifies this issue in its tracker."""
    return f"{TRACKER_LABEL}-{issue_id.hex[:12]}"


def labels_for(severity: str) -> list[str]:
    return [TRACKER_LABEL, f"severity-{severity}"]


def mask_secrets(text: str, *, keep_lines: bool = False) -> str:
    """Mask detected secrets and the values of credential-named assignments."""
    for found in sorted(
        find_secrets(text).matches, key=lambda m: m.start, reverse=True
    ):
        span = text[found.start : found.end]
        fill = MASK + ("\n" * span.count("\n") if keep_lines else "")
        text = f"{text[: found.start]}{fill}{text[found.end :]}"
    return _ASSIGNED_SECRET.sub(_masked_assignment, text)


def _masked_assignment(found: re.Match) -> str:
    value = found.group(2)
    quote = value[0] if value[:1] in "\"'" else ""
    return f"{found.group(1)}{quote}{MASK}{quote}"


def _location(value: str | None) -> str:
    return _clip(mask_secrets(value or ""), MAX_LOCATION)


def _date(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%d") if value else None


def _risk(lead: Any, target_value: str) -> list[tuple[str, str | None]]:
    kev = None
    if lead.is_kev:
        kev = f"Listed, due {lead.kev_due_date}" if lead.kev_due_date else "Listed"
    return [
        ("Severity", SEVERITY_LABELS.get(lead.severity, lead.severity)),
        ("Check", lead.template_id),
        ("Target", target_value),
        ("CVE", ", ".join(lead.cve_ids or []) or None),
        ("CWE", ", ".join(lead.cwe_ids or []) or None),
        ("CVSS", f"{lead.cvss_score:.1f}" if lead.cvss_score is not None else None),
        (
            "EPSS",
            f"{lead.epss_score * 100:.1f}%" if lead.epss_score is not None else None,
        ),
        ("CISA KEV", kev),
    ]


def _prose(doc: Doc, lead: Any) -> None:
    if lead.impact:
        doc.heading("Impact").paragraph(_clip(lead.impact, MAX_PROSE))
    if lead.remediation:
        doc.heading("Remediation").paragraph(_clip(lead.remediation, MAX_PROSE))


def _references(doc: Doc, lead: Any) -> None:
    refs = [str(r) for r in (lead.references or []) if r][:MAX_REFERENCES]
    if refs:
        doc.heading("References").bullets(refs)


def single_body(vuln: Any, target_value: str, *, evidence: int = 2) -> Doc:
    """Evidence level: 2 full, 1 command and request, 0 none."""
    doc = Doc().paragraph(_clip(vuln.description, MAX_PROSE))
    doc.heading("Details").facts(
        [
            *_risk(vuln, target_value),
            ("Location", _location(vuln.matched_at)),
            ("Evidence", evidence_label(vuln.evidence)),
            ("First seen", _date(vuln.discovered_at)),
        ]
    )
    _prose(doc, vuln)
    if evidence:
        curl = _clip(
            mask_secrets(redact_credentials(vuln.curl_command or "")),
            MAX_EVIDENCE_CHARS,
        )
        request = _clip(
            mask_secrets(redact_message(vuln.request) or ""), MAX_EVIDENCE_CHARS
        )
        response = (
            _clip(mask_secrets(redact_message(vuln.response) or ""), MAX_RESPONSE)
            if evidence > 1
            else ""
        )
        if curl or request or response:
            doc.heading("Reproduction")
            doc.code(curl, "shell").code(request, "http").code(response, "http")
    _references(doc, vuln)
    return doc.link("View finding in reNgine", finding_link(vuln.scan_id, vuln.id))


def _locations(doc: Doc, locations: Sequence[str], shown: int) -> None:
    doc.bullets([_location(v) for v in locations[:shown]])
    if len(locations) > shown:
        doc.paragraph(f"{counted(len(locations) - shown, 'more location')}.")


def grouped_body(
    vulns: Sequence[Any], target_value: str, *, shown: int = MAX_GROUP_LOCATIONS
) -> Doc:
    lead = vulns[0]
    shared = len({v.description for v in vulns}) == 1
    doc = Doc().paragraph(_clip(lead.description, MAX_PROSE) if shared else "")
    doc.heading("Details").facts(_risk(lead, target_value))
    doc.heading(f"Locations · {len(vulns)}")
    _locations(doc, [v.matched_at for v in vulns], shown)
    _prose(doc, lead)
    _references(doc, lead)
    return doc.link(
        "View findings in reNgine", check_link(lead.scan_id, lead.template_id)
    )


def issue_body(
    vulns: Sequence[Any],
    target_value: str,
    spec: TrackerSpec,
    *,
    grouped: bool,
    public: bool = False,
    reference: str | None = None,
) -> Doc:
    """The richest body that fits the tracker's limit."""
    if grouped and len(vulns) > 1:
        shown = MAX_GROUP_LOCATIONS
        doc = grouped_body(vulns, target_value, shown=shown)
        while rendered_size(doc, spec.body_format.value) > spec.body_limit:
            if shown <= MIN_SHOWN:
                break
            shown = max(MIN_SHOWN, shown // 2)
            doc = grouped_body(vulns, target_value, shown=shown)
    else:
        level = 0 if public else 2
        doc = single_body(vulns[0], target_value, evidence=level)
        while level and rendered_size(doc, spec.body_format.value) > spec.body_limit:
            level -= 1
            doc = single_body(vulns[0], target_value, evidence=level)
    return doc.paragraph(f"Reference: {reference}") if reference else doc


def added_comment(locations: Sequence[str], link: str) -> Doc:
    doc = Doc().paragraph("New location:" if len(locations) == 1 else "New locations:")
    _locations(doc, locations, MAX_GROUP_LOCATIONS)
    return doc.link("View finding in reNgine", link)


def _presence(kind: CommentKind, when: str | None, status: str | None) -> str:
    scan = f"the scan of {when}" if when else "the latest scan"
    if kind == CommentKind.NOT_OBSERVED:
        return f"Not observed in {scan}."
    if kind == CommentKind.OBSERVED_AGAIN:
        return f"Observed again in {scan}."
    if status:
        return f"Observed in {scan}. Issue status: {status}."
    return f"Observed in {scan}."


def presence_comment(
    kind: CommentKind,
    locations: Sequence[str],
    scan_id: Any,
    completed: datetime | None,
    status: str | None = None,
) -> Doc:
    doc = Doc().paragraph(_presence(kind, _date(completed), status))
    _locations(doc, locations, MAX_GROUP_LOCATIONS)
    return doc.link("View scan in reNgine", scan_link(scan_id))

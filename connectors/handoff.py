"""What a proxy receives: one raw HTTP request, its response where one was stored, and a note."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from urllib.parse import quote, urlsplit

from shared.definitions.connectors import (
    HANDOFF_USER_AGENT,
    MAX_HANDOFF_NOTES,
    MAX_HANDOFF_REQUEST,
    MAX_HANDOFF_RESPONSE,
    SEVERITY_HIGHLIGHT,
    SourceTool,
)
from shared.definitions.vulnerabilities import SEVERITY_LABELS, Protocol
from shared.services.scan_resolve import MASK
from shared.utils.net import host_port

_DEFAULT_PORTS = {"http": 80, "https": 443}
_BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})
_HEADER_LINE = re.compile(r"^([!#$%&'*+\-.^_`|~0-9A-Za-z]+):[ \t]*(.*)$")
_CHARSET = re.compile(r"(charset=)\"?([^\";\s]+)\"?", re.IGNORECASE)
_TRANSFER_HEADERS = ("transfer-encoding:", "content-encoding:")
_PATH_SAFE = "/%:@!$&'()*+,;=-._~"
_QUERY_SAFE = _PATH_SAFE + "?"
_FORM = "application/x-www-form-urlencoded"
_JSON = "application/json"
_XML = "application/xml"
_BOUNDARY = "----reNgineFormBoundary"
_LABEL_MAX = 120


@dataclass(frozen=True)
class Handoff:
    url: str
    method: str
    label: str
    request: str | None
    response: str | None = None
    notes: str | None = None
    color: str | None = None
    scan_id: uuid.UUID | None = None


def _lines(text: str) -> list[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _split(message: str) -> tuple[str, str, str]:
    head, sep, body = message.partition("\r\n\r\n")
    if not sep:
        head, sep, body = message.partition("\n\n")
    return head, sep, body


def normalise(message: str | None, limit: int) -> str | None:
    """CRLF in the head, the body byte for byte, cut at the limit."""
    if not message or not message.strip():
        return None
    head, sep, body = _split(message)
    text = "\r\n".join(_lines(head)) + "\r\n\r\n" + (body if sep else "")
    return text[:limit]


def _label(value: str) -> str:
    return value[:_LABEL_MAX]


def _header(head: str, name: str) -> str | None:
    wanted = name.lower()
    for line in head.split("\r\n"):
        match = _HEADER_LINE.match(line)
        if match and match.group(1).lower() == wanted:
            return match.group(2).strip()
    return None


def _set_header(lines: list[str], name: str, value: str) -> list[str]:
    """Replace every line carrying the header, or append it."""
    kept = [
        line
        for line in lines
        if not (
            _HEADER_LINE.match(line) and line.split(":", 1)[0].lower() == name.lower()
        )
    ]
    kept.append(f"{name}: {value}")
    return kept


def request_target(url: str) -> str:
    parts = urlsplit(url)
    path = quote(parts.path or "/", safe=_PATH_SAFE)
    return f"{path}?{quote(parts.query, safe=_QUERY_SAFE)}" if parts.query else path


def authority(url: str) -> str:
    """The Host header value: the port only when it is not the scheme's own."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.port and parts.port != _DEFAULT_PORTS.get(parts.scheme, 0):
        return host_port(host, parts.port)
    return host


def with_body(message: str, body: str | None, content_type: str = _FORM) -> str:
    """The message with this body, its type stated once and its length exact."""
    head, _, _ = _split(message)
    lines = _lines(head)
    if body:
        if content_type.startswith("multipart/"):
            lines = _set_header(lines, "Content-Type", content_type)
        elif _header("\r\n".join(lines), "Content-Type") is None:
            lines.append(f"Content-Type: {content_type}")
        lines = _set_header(lines, "Content-Length", str(len(body.encode())))
    elif _header("\r\n".join(lines), "Content-Length") is not None:
        lines = _set_header(lines, "Content-Length", "0")
    return "\r\n".join(lines) + "\r\n\r\n" + (body or "")


def build_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: str | None = None,
    content_type: str = _FORM,
) -> str:
    """A raw HTTP/1.1 request for a URL nothing was stored for."""
    lines = [
        f"{(method or 'GET').upper()} {request_target(url)} HTTP/1.1",
        f"Host: {authority(url)}",
        f"User-Agent: {HANDOFF_USER_AGENT}",
        "Accept: */*",
    ]
    lines.extend(f"{name}: {value}" for name, value in (headers or {}).items())
    return with_body("\r\n".join(lines) + "\r\n\r\n", body, content_type)


def _sample_values(samples: list[dict]) -> dict[str, str]:
    values: dict[str, str] = {}
    for sample in samples or []:
        if isinstance(sample, dict):
            for name, value in sample.items():
                values.setdefault(str(name), "" if value is None else str(value))
    return values


def _multipart(names: list[str], values: dict[str, str]) -> str:
    parts = [
        f'--{_BOUNDARY}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
        f"{values.get(name, '')}\r\n"
        for name in names
    ]
    return "".join(parts) + f"--{_BOUNDARY}--\r\n"


def _xml(names: list[str], values: dict[str, str]) -> str:
    inner = "".join(
        f"<{name}>{_xml_text(values.get(name, ''))}</{name}>" for name in names
    )
    return f'<?xml version="1.0" encoding="UTF-8"?><request>{inner}</request>'


def _xml_text(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def body_for(
    params: list[str],
    samples: list[dict],
    skip: set[str],
    content_type: str | None = None,
) -> tuple[str | None, str]:
    """A body template for the parameters the URL does not carry, in the declared type."""
    values = _sample_values(samples)
    names = [name for name in params or [] if name and name not in skip]
    if not names:
        return None, content_type or _FORM
    declared = (content_type or "").lower()
    if "json" in declared:
        return json.dumps({name: values.get(name, "") for name in names}), _JSON
    if "multipart" in declared:
        return _multipart(names, values), f"multipart/form-data; boundary={_BOUNDARY}"
    if "xml" in declared:
        return _xml(names, values), content_type or _XML
    body = "&".join(
        f"{quote(name, safe='')}={quote(values.get(name, ''), safe='')}"
        for name in names
    )
    return body, _FORM


def form_body(params: list[str], samples: list[dict], skip: set[str]) -> str | None:
    """name=value pairs for the parameters the URL does not already carry."""
    return body_for(params, samples, skip)[0]


def _query_names(url: str) -> set[str]:
    return {pair.split("=", 1)[0] for pair in urlsplit(url).query.split("&") if pair}


def request_message(message: str | None) -> str | None:
    """A stored raw request with the length of the body it ships."""
    text = normalise(message, MAX_HANDOFF_REQUEST)
    if not text:
        return None
    head, sep, body = text.partition("\r\n\r\n")
    if _header(head, "Content-Length") is None:
        return text
    lines = _set_header(head.split("\r\n"), "Content-Length", str(len(body.encode())))
    return "\r\n".join(lines) + sep + body


def _decoded(message: str) -> str:
    """Drop the transfer headers, state the length shipped and the UTF-8 the body is in."""
    head, sep, body = message.partition("\r\n\r\n")
    lines = [
        _CHARSET.sub(r"\1utf-8", line)
        if line.lower().startswith("content-type:")
        else line
        for line in head.split("\r\n")
        if not line.lower().startswith(_TRANSFER_HEADERS)
    ]
    lines = _set_header(lines, "Content-Length", str(len(body.encode())))
    return "\r\n".join(lines) + sep + body


def response_message(message: str | None) -> str | None:
    """A stored raw response, ready for a proxy to display."""
    text = normalise(message, MAX_HANDOFF_RESPONSE)
    return _decoded(text) if text else None


def response_text(head: str | None, body: str | None) -> str | None:
    """A raw response from a stored header block and body."""
    if not head or not head.strip():
        return None
    return response_message(head.rstrip("\r\n") + "\r\n\r\n" + (body or ""))


def restore_headers(request: str | None, headers: dict[str, str]) -> str | None:
    """Put the run's own header values back where the store masked them."""
    if not request or not headers or MASK not in request:
        return request
    by_name = {name.lower(): value for name, value in headers.items() if value}
    head, sep, body = request.partition("\r\n\r\n")
    out: list[str] = []
    for line in head.split("\r\n"):
        match = _HEADER_LINE.match(line)
        value = by_name.get(match.group(1).lower()) if match else None
        if match and value is not None and MASK in match.group(2):
            out.append(f"{match.group(1)}: {value}")
        else:
            out.append(line)
    return "\r\n".join(out) + sep + body


def _note(*lines: str | None) -> str:
    text = "\n".join(line for line in lines if line)
    return text[:MAX_HANDOFF_NOTES]


def from_finding(finding, *, link: str | None = None) -> Handoff | None:
    """The request a scanner sent, or None for a finding with no HTTP exchange."""
    url = finding.url or finding.matched_at
    request = request_message(finding.request)
    if request is None:
        if finding.protocol != Protocol.HTTP.value or not str(url).startswith(
            ("http://", "https://")
        ):
            return None
        request = build_request("GET", url)
    method = request.split(" ", 1)[0].upper() or "GET"
    severity = SEVERITY_LABELS.get(finding.severity, finding.severity)
    cves = ", ".join(finding.cve_ids or []) or None
    return Handoff(
        url=url,
        method=method,
        label=_label(finding.template_id),
        request=request,
        response=response_message(finding.response),
        notes=_note(
            f"reNgine · {severity} · {finding.template_id}",
            finding.template_name,
            cves,
            finding.matched_at,
            link,
        ),
        color=SEVERITY_HIGHLIGHT.get(finding.severity),
        scan_id=finding.scan_id,
    )


def from_asset(asset) -> Handoff:
    """The probe's request to a web asset root."""
    request = request_message(asset.raw_request) or build_request(
        asset.method or "GET", asset.url
    )
    return Handoff(
        url=asset.url,
        method=(asset.method or request.split(" ", 1)[0] or "GET").upper(),
        label=_label(authority(asset.url) or asset.host),
        request=request,
        response=response_text(asset.raw_response_header, asset.response_body),
        notes=_note(
            f"reNgine · web asset · {asset.url}",
            asset.title,
            f"{asset.status_code}" if asset.status_code else None,
        ),
        scan_id=asset.scan_id,
    )


def from_endpoint(endpoint, response=None) -> Handoff:
    """A request built from what discovery recorded: method, URL, parameters."""
    method = ((endpoint.methods or ["GET"])[0] or "GET").upper()
    body, content_type = (
        body_for(
            list(endpoint.params or []),
            list(endpoint.param_samples or []),
            _query_names(endpoint.url),
        )
        if method in _BODY_METHODS
        else (None, _FORM)
    )
    return Handoff(
        url=endpoint.url,
        method=method,
        label=_label(endpoint.path or "/"),
        request=build_request(
            method, endpoint.url, body=body, content_type=content_type
        ),
        response=response_text(
            getattr(response, "raw_response_header", None),
            getattr(response, "response_body", None),
        ),
        notes=_note(
            f"reNgine · endpoint · {endpoint.url}",
            f"{endpoint.status_code}" if endpoint.status_code else None,
            ", ".join(endpoint.sources or []) or None,
        ),
        scan_id=endpoint.scan_id,
    )


def from_candidate(candidate) -> Handoff:
    """A shape the proxy recorded, from its sample head when one was kept."""
    sample = normalise(candidate.request_sample, MAX_HANDOFF_REQUEST)
    method = (
        sample.split(" ", 1)[0].upper()
        if sample
        else ((candidate.methods or ["GET"])[0] or "GET").upper()
    ) or "GET"
    body, content_type = (
        body_for(
            list(candidate.params or []),
            [],
            _query_names(candidate.url),
            _header(_split(sample)[0], "Content-Type") if sample else None,
        )
        if method in _BODY_METHODS
        else (None, _FORM)
    )
    request = (
        with_body(sample, body, content_type)
        if sample
        else build_request(method, candidate.url, body=body, content_type=content_type)
    )
    tool = candidate.source_tool or SourceTool.PROXY.value
    return Handoff(
        url=candidate.url,
        method=method,
        label=_label(candidate.path or "/"),
        request=request,
        notes=_note(f"reNgine · browsed through {tool} · {candidate.url}"),
    )

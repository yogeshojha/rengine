"""List prices from OpenRouter's public model catalog."""

from __future__ import annotations

import json
import math
import re
import time
from contextlib import suppress
from urllib.parse import urlsplit

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shared.definitions.ai import (
    MAX_CATALOG_ID,
    OPENAI_CHAT_ID,
    PER_MTOK,
    Rates,
    model_alias,
)
from shared.definitions.datasets import DatasetKind
from shared.enums.instance import AIProvider
from shared.http import get_sync_client
from shared.logging import get_logger
from shared.models.ai import AiPrice
from shared.redis import sync_client
from shared.services import feed_ledger
from shared.services.locks import dataset, sync_lock

logger = get_logger(__name__)

CATALOG_URL = "https://openrouter.ai/api/v1/models"
CATALOG_HOST = "openrouter.ai"
CACHE_KEY = "ai:prices:v2"
MEMO_SECONDS = 600
MAX_BYTES = 8 << 20
CHUNK_BYTES = 1 << 16
_TIMEOUT = httpx.Timeout(15.0, connect=5.0)

_VENDOR: dict[str, str] = {
    AIProvider.ANTHROPIC.value: "anthropic",
    AIProvider.OPENAI.value: "openai",
    AIProvider.GOOGLE.value: "google",
}
_PROVIDER_OF: dict[str, str] = {vendor: key for key, vendor in _VENDOR.items()}
# closed models, served by their vendor alone
_CLOSED: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^claude-"), AIProvider.ANTHROPIC.value),
    (OPENAI_CHAT_ID, AIProvider.OPENAI.value),
    (re.compile(r"^gemini-"), AIProvider.GOOGLE.value),
)
_OPEN_WEIGHTS = re.compile(r"^gpt-oss")
_CLAUDE_VERSION = re.compile(r"-(\d+)-(\d+)$")

_memo: tuple[float, dict[str, Rates]] | None = None


def per_mtok(value: object) -> float | None:
    """A per-token price as dollars per million tokens."""
    try:
        per_token = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if per_token < 0 or not math.isfinite(per_token):
        return None
    return round(per_token * PER_MTOK, 6)


def row_rates(pricing: object) -> Rates | None:
    """The rates of one catalog row, or None without an input and an output price."""
    if not isinstance(pricing, dict):
        return None
    prompt = per_mtok(pricing.get("prompt"))
    completion = per_mtok(pricing.get("completion"))
    if prompt is None or completion is None:
        return None
    return Rates(
        prompt,
        completion,
        per_mtok(pricing.get("input_cache_read")),
        per_mtok(pricing.get("input_cache_write")),
    )


def parse(body: object) -> dict[str, Rates]:
    rows = body.get("data") if isinstance(body, dict) else None
    out: dict[str, Rates] = {}
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            continue
        if len(row["id"]) > MAX_CATALOG_ID:
            continue
        rates = row_rates(row.get("pricing"))
        if rates is not None:
            out[row["id"]] = rates
    return out


def read(body: bytes) -> dict[str, Rates]:
    """The rates a downloaded list names. Raises when it names none."""
    rates = parse(json.loads(body))
    if not rates:
        msg = "price list named no prices"
        raise ValueError(msg)
    return rates


def on_catalog_host(base_url: str) -> bool:
    host = (urlsplit(base_url).hostname or "").lower()
    return host == CATALOG_HOST or host.endswith(f".{CATALOG_HOST}")


def _closed(model: str) -> tuple[str, str] | None:
    """The first-party provider and bare id of a closed model, or None."""
    owner = None
    vendor, slash, rest = model.partition("/")
    if slash:
        owner = _PROVIDER_OF.get(vendor)
        if owner is None:
            return None
        model = rest
    if _OPEN_WEIGHTS.match(model):
        return None
    for pattern, provider in _CLOSED:
        if pattern.match(model) and owner in (None, provider):
            return provider, model
    return None


def catalog_ids(provider: str, model: str, base_url: str = "") -> list[str]:
    """The catalog ids a model is listed under, most exact first."""
    model = model.strip().removeprefix("models/")
    if not model:
        return []
    alias = model_alias(model)
    vendor = _VENDOR.get(provider)
    if vendor == "anthropic":
        return ["anthropic/" + _CLAUDE_VERSION.sub(r"-\1.\2", alias)]
    if vendor is not None:
        return list(dict.fromkeys((f"{vendor}/{model}", f"{vendor}/{alias}")))
    if on_catalog_host(base_url) and "/" in model:
        return [model]
    closed = _closed(model)
    return catalog_ids(*closed) if closed else []


def _encode(rates: dict[str, Rates]) -> str:
    return json.dumps(
        {
            "at": time.time(),
            "rates": {
                k: [r.input, r.output, r.cache_read, r.cache_write]
                for k, r in rates.items()
            },
        }
    )


def _decode(raw: str) -> dict[str, Rates] | None:
    try:
        return {k: Rates(*v) for k, v in json.loads(raw)["rates"].items()}
    except (ValueError, TypeError, KeyError, AttributeError):
        return None


def _remember(rates: dict[str, Rates]) -> None:
    global _memo  # noqa: PLW0603
    _memo = (time.monotonic(), rates)


def catalog() -> dict[str, Rates] | None:
    """Every listed rate by catalog id, or None before the list has loaded."""
    memo = _memo
    if memo is not None and time.monotonic() - memo[0] <= MEMO_SECONDS:
        return memo[1]
    try:
        raw = sync_client().get(CACHE_KEY)
    except Exception:
        raw = None
    rates = _decode(raw) if isinstance(raw, str) else None
    if rates:
        _remember(rates)
        return rates
    return memo[1] if memo is not None else None


def lookup(provider: str, model: str, *, base_url: str = "") -> Rates | None:
    """The live list rates for a model, or None."""
    ids = catalog_ids(provider, model, base_url)
    if not ids:
        return None
    rates = catalog()
    if not rates:
        return None
    return next((rates[i] for i in ids if i in rates), None)


def download() -> bytes:
    """The price list, refused on a redirect, an error status or past the size cap."""
    body = bytearray()
    with (
        get_sync_client(
            timeout=_TIMEOUT,
            follow_redirects=False,
            transport=httpx.HTTPTransport(retries=0),
        ) as client,
        client.stream(
            "GET", CATALOG_URL, headers={"Accept": "application/json"}
        ) as response,
    ):
        if response.status_code != httpx.codes.OK:
            msg = f"price list answered {response.status_code}"
            raise ValueError(msg)
        for chunk in response.iter_bytes(CHUNK_BYTES):
            body += chunk
            if len(body) > MAX_BYTES:
                msg = f"price list exceeded {MAX_BYTES} bytes"
                raise ValueError(msg)
    return bytes(body)


def stored(session: Session) -> dict[str, Rates]:
    rows = session.execute(select(AiPrice)).scalars()
    return {
        row.model_id: Rates(
            row.input_per_mtok,
            row.output_per_mtok,
            row.cache_read_per_mtok,
            row.cache_write_per_mtok,
        )
        for row in rows
    }


def _replace(session: Session, rates: dict[str, Rates]) -> None:
    session.execute(delete(AiPrice))
    session.execute(
        AiPrice.__table__.insert(),
        [
            {
                "model_id": model_id,
                "input_per_mtok": r.input,
                "output_per_mtok": r.output,
                "cache_read_per_mtok": r.cache_read,
                "cache_write_per_mtok": r.cache_write,
            }
            for model_id, r in rates.items()
        ],
    )


def publish(rates: dict[str, Rates]) -> None:
    """Share a loaded list with every process."""
    if not rates:
        return
    _remember(rates)
    try:
        sync_client().set(CACHE_KEY, _encode(rates))
    except Exception:
        logger.debug("price list not shared", exc_info=True)


def share(session: Session) -> bool:
    """Share the stored list. False when nothing is stored."""
    rates = stored(session)
    publish(rates)
    return bool(rates)


def load(session: Session) -> int | None:
    """Download the list into its table and share it. None when another load holds it."""
    kind = DatasetKind.AI_PRICES.value
    with sync_lock(session, dataset(kind)) as held:
        if not held:
            return None
        try:
            with feed_ledger.refreshing(session, kind) as refresh:
                body = download()
                rates = read(body)
                _replace(session, rates)
                refresh.rows, refresh.size = len(rates), len(body)
        except Exception:
            with suppress(Exception):
                share(session)
            raise
    publish(rates)
    return refresh.rows


def forget() -> None:
    """Drop this process's copy."""
    global _memo  # noqa: PLW0603
    _memo = None

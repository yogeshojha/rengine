"""Names each discovery source contributed to a run."""

from __future__ import annotations

from collections.abc import Iterable

from shared.definitions.api_keys import provider_name
from shared.definitions.discovery_sources import SourceStatus
from stages.subdomain.providers.base import ProviderResult, SourceStat


def _name(host: str) -> str:
    return host.strip().lower().rstrip(".")


def _owner(result: ProviderResult, sub: str | None) -> str:
    return f"{result.source.value}.{sub}" if sub else result.source.value


def _plural(count: int, word: str) -> str:
    return f"{count:,} {word}{'' if count == 1 else 's'}"


def _sub_status(names: int, stat: SourceStat | None) -> tuple[str, str | None]:
    if stat is not None and stat.skipped:
        return SourceStatus.SKIPPED.value, "Key not used by subfinder"
    errors = stat.errors if stat else 0
    note = _plural(errors, "failed request") if errors else None
    if names:
        return SourceStatus.FOUND.value, note
    if errors:
        return SourceStatus.FAILED.value, note
    return SourceStatus.EMPTY.value, None


def _row(
    key: str,
    label: str,
    via: str | None,
    names: int,
    only: int,
    status: str,
    note: str | None,
    *,
    keyed: bool = False,
) -> dict:
    return {
        "key": key,
        "label": label,
        "via": via,
        "names": names,
        "only": only,
        "status": status,
        "note": note,
        "keyed": keyed,
    }


def _owners(results: list[ProviderResult], kept: set[str]) -> dict[str, set[str]]:
    """Each kept name and every source that returned it."""
    owners: dict[str, set[str]] = {}
    for result in results:
        claimed: set[str] = set()
        for sub, hosts in result.breakdown.items():
            for name in map(_name, hosts):
                if name in kept:
                    owners.setdefault(name, set()).add(_owner(result, sub))
                    claimed.add(name)
        for name in map(_name, result.subdomains):
            if name in kept and name not in claimed:
                owners.setdefault(name, set()).add(_owner(result, None))
    return owners


def _tally(owners: dict[str, set[str]]) -> tuple[dict[str, int], dict[str, int]]:
    """Names per source, and names no other source returned."""
    found: dict[str, int] = {}
    alone: dict[str, int] = {}
    for sources in owners.values():
        for source in sources:
            found[source] = found.get(source, 0) + 1
        if len(sources) == 1:
            only = next(iter(sources))
            alone[only] = alone.get(only, 0) + 1
    return found, alone


def _rows_for(
    result: ProviderResult, found: dict[str, int], alone: dict[str, int]
) -> list[dict]:
    via = result.source.value
    if result.skipped:
        return [
            _row(via, via, None, 0, 0, SourceStatus.SKIPPED.value, result.skip_reason)
        ]
    if result.error:
        return [_row(via, via, None, 0, 0, SourceStatus.FAILED.value, result.error)]
    plain = _owner(result, None)
    if not result.breakdown and not result.keyed_sources:
        names = found.get(plain, 0)
        status = SourceStatus.FOUND.value if names else SourceStatus.EMPTY.value
        return [_row(plain, via, None, names, alone.get(plain, 0), status, result.note)]
    rows: list[dict] = []
    for sub in set(result.breakdown) | set(result.keyed_sources):
        key = _owner(result, sub)
        names = found.get(key, 0)
        provider = result.keyed_sources.get(sub)
        if not names and provider is None:
            continue
        status, note = _sub_status(names, result.source_stats.get(sub))
        label = provider_name(provider) if provider else sub
        rows.append(
            _row(
                key,
                label,
                via,
                names,
                alone.get(key, 0),
                status,
                note,
                keyed=provider is not None,
            )
        )
    if found.get(plain):
        rows.append(
            _row(
                plain,
                via,
                None,
                found[plain],
                alone.get(plain, 0),
                SourceStatus.FOUND.value,
                None,
            )
        )
    return rows


def source_report(results: Iterable[ProviderResult], kept: Iterable[str]) -> list[dict]:
    """One row per source that ran: names kept, names no other source found, outcome."""
    results = list(results)
    found, alone = _tally(_owners(results, {_name(n) for n in kept}))
    rows = [row for result in results for row in _rows_for(result, found, alone)]
    rows.sort(key=lambda r: (-r["names"], r["label"].lower()))
    return rows


def run_notes(results: Iterable[ProviderResult]) -> str | None:
    """One sentence per passive source that stopped at its time budget."""
    notes = [
        f"{r.source.value.capitalize()} {r.note}."
        for r in results
        if r.cut_short and r.note
    ]
    return " ".join(notes) or None

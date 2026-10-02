from __future__ import annotations

from shared.definitions.interest import TONE_WARNING
from shared.definitions.vulnerabilities import Severity


def check_rows(specs, group_labels, checks, *, warnings_only: bool) -> list[dict]:
    """One row per check that applied to at least one asset."""
    counts = {c.key: c for c in checks}
    rows = []
    for spec in specs:
        count = counts.get(spec.key)
        if count is None or count.applicable == 0:
            continue
        if warnings_only and spec.tone != TONE_WARNING:
            continue
        rows.append(
            {
                "label": spec.label,
                "help": spec.help,
                "group": group_labels[spec.group],
                "badge": Severity.MEDIUM.value
                if spec.tone == TONE_WARNING
                else Severity.INFO.value,
                "failing": count.failing,
                "applicable": count.applicable,
                "share": round(count.failing / count.applicable * 100),
            }
        )
    return rows

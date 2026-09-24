"""HTTP probe runs automatically: drop its switch, move the every-port setting to port scan.

Revision ID: c8e4f2a7d913
Revises: 5d0c2a9e7b41
Create Date: 2026-09-24
"""

from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision: str = "c8e4f2a7d913"
down_revision: str | None = "5d0c2a9e7b41"
branch_labels = None
depends_on = None

_PROBE = "http_probe"
_PORTS = "port_scan"
_MOVED = ("probe_all_ports", "http_on_every_port")
_DROPPED = {"enabled", _MOVED[0]}


def _migrate(stages: dict) -> tuple[dict, bool]:
    probe = stages.get(_PROBE)
    if not isinstance(probe, dict) or not set(probe) & _DROPPED:
        return stages, False
    out = dict(stages)
    if probe.get(_MOVED[0]) is True:
        ports = out.get(_PORTS) if isinstance(out.get(_PORTS), dict) else {}
        out[_PORTS] = {**ports, _MOVED[1]: True}
    kept = {k: v for k, v in probe.items() if k not in _DROPPED}
    if kept:
        out[_PROBE] = kept
    else:
        out.pop(_PROBE)
    return out, True


def _yaml_mentions(source: str | None) -> bool:
    if not source:
        return False
    try:
        import yaml  # noqa: PLC0415

        doc = yaml.safe_load(source) or {}
    except Exception:
        return False
    stages = doc.get("stages") if isinstance(doc, dict) else None
    probe = stages.get(_PROBE) if isinstance(stages, dict) else None
    return isinstance(probe, dict) and bool(set(probe) & _DROPPED)


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, stages, yaml_source FROM scan_engines")
    ).all()
    for id_, stages, yaml_source in rows:
        raw = stages if isinstance(stages, dict) else json.loads(stages or "{}")
        migrated, changed = _migrate(raw)
        drop_yaml = _yaml_mentions(yaml_source)
        if not changed and not drop_yaml:
            continue
        bind.execute(
            sa.text(
                "UPDATE scan_engines SET stages = :stages, "
                "yaml_source = CASE WHEN :drop THEN NULL ELSE yaml_source END "
                "WHERE id = :id"
            ),
            {"stages": json.dumps(migrated), "drop": drop_yaml, "id": id_},
        )


def downgrade() -> None:
    pass

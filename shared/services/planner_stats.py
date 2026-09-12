"""ANALYZE on the result tables."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.models.endpoint import Endpoint
from shared.models.http_asset import HttpAsset
from shared.models.interest import InterestSignal
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability

RESULT_TABLES: tuple[str, ...] = tuple(
    model.__tablename__
    for model in (
        Subdomain,
        Endpoint,
        Port,
        IpAddress,
        Vulnerability,
        HttpAsset,
        InterestSignal,
    )
)


def analyze_result_tables(session: Session) -> None:
    try:
        session.execute(text(f"ANALYZE {', '.join(RESULT_TABLES)}"))
        session.commit()
    except Exception:
        session.rollback()
        raise

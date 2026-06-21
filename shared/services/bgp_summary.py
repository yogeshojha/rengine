from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlmodel import select

from shared.models.bgp_summary import TargetBgpSummary
from shared.models.ripestat import (
    RIPEStatAnnouncedPrefix,
    RIPEStatASNNeighbour,
    RIPEStatASOverview,
    RIPEStatNetworkInfo,
    RIPEStatPrefixOverview,
)
from shared.models.target import Target
from shared.utils.datetime import utc_now


def write_bgp_summary_for_target(session: Session, target: Target) -> None:
    now = utc_now()

    if target.target_type.value == "asn":
        asn_number = int(target.target_value.upper().replace("AS", "").strip())

        prefix_count = session.execute(
            select(func.count(RIPEStatAnnouncedPrefix.id)).where(
                RIPEStatAnnouncedPrefix.asn == asn_number
            )
        ).scalar_one()

        peer_count = session.execute(
            select(func.count(RIPEStatASNNeighbour.id)).where(
                RIPEStatASNNeighbour.asn == asn_number
            )
        ).scalar_one()

        overview = session.execute(
            select(RIPEStatASOverview).where(RIPEStatASOverview.asn == asn_number)
        ).scalar_one_or_none()

        _upsert_summary(
            session,
            target_id=target.id,
            prefix_count=prefix_count,
            peer_count=peer_count,
            announced=overview.announced if overview else None,
            queried_at=now,
        )

    elif target.target_type.value == "ip":
        info = session.execute(
            select(RIPEStatNetworkInfo).where(
                RIPEStatNetworkInfo.ip == target.target_value
            )
        ).scalar_one_or_none()

        if info:
            overview = session.execute(
                select(RIPEStatASOverview).where(RIPEStatASOverview.asn == info.asn)
            ).scalar_one_or_none()

            _upsert_summary(
                session,
                target_id=target.id,
                asn=info.asn,
                prefix=info.prefix,
                holder=overview.holder if overview else None,
                queried_at=now,
            )
        else:
            _upsert_summary(session, target_id=target.id, queried_at=now)

    elif target.target_type.value == "ip_range":
        po = (
            session.execute(
                select(RIPEStatPrefixOverview).where(
                    RIPEStatPrefixOverview.prefix == target.target_value
                )
            )
            .scalars()
            .first()
        )

        if po:
            _upsert_summary(
                session,
                target_id=target.id,
                asn=po.asn,
                prefix=po.prefix,
                holder=po.holder,
                queried_at=now,
            )
        else:
            _upsert_summary(session, target_id=target.id, queried_at=now)


def _upsert_summary(session: Session, target_id, **fields) -> None:
    existing = session.execute(
        select(TargetBgpSummary).where(TargetBgpSummary.target_id == target_id)
    ).scalar_one_or_none()

    if existing:
        for key, value in fields.items():
            setattr(existing, key, value)
        session.add(existing)
    else:
        session.add(TargetBgpSummary(target_id=target_id, **fields))

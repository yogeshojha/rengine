import uuid

from sqlalchemy import DateTime, Uuid, and_, func, literal, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.notification import Notification, NotificationReceipt
from shared.services.project_access import ProjectSet, project_clause
from shared.utils.datetime import utc_now


class NotificationManager:
    @staticmethod
    def in_scope(stmt, access: ProjectSet):
        """Notifications of the projects the access opens, plus instance-wide ones."""
        if access is None:
            return stmt
        return stmt.where(
            project_clause(access, Notification.project_id)
            | Notification.project_id.is_(None)
        )

    @staticmethod
    def _one(notification_id: uuid.UUID, access: ProjectSet):
        return NotificationManager.in_scope(
            select(Notification.id).where(Notification.uid == notification_id), access
        )

    @staticmethod
    def receipt_join(stmt, user_id: uuid.UUID):
        return stmt.outerjoin(
            NotificationReceipt,
            and_(
                NotificationReceipt.notification_id == Notification.id,
                NotificationReceipt.user_id == user_id,
            ),
        ).where(NotificationReceipt.dismissed_at.is_(None))

    @staticmethod
    async def _stamp(
        session: AsyncSession,
        user_id: uuid.UUID,
        ids,
        *,
        dismiss: bool,
    ) -> int:
        now = utc_now()
        values = select(
            Notification.id,
            literal(user_id, type_=Uuid),
            literal(now, type_=DateTime(timezone=True)),
            literal(now if dismiss else None, type_=DateTime(timezone=True)),
        ).where(Notification.id.in_(ids))
        stmt = insert(NotificationReceipt).from_select(
            ["notification_id", "user_id", "read_at", "dismissed_at"], values
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["notification_id", "user_id"],
            set_={
                "read_at": func.coalesce(NotificationReceipt.read_at, now),
                **({"dismissed_at": now} if dismiss else {}),
            },
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount or 0

    @staticmethod
    async def mark_as_read(
        session: AsyncSession,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
        access: ProjectSet,
    ) -> bool:
        return (
            await NotificationManager._stamp(
                session,
                user_id,
                NotificationManager._one(notification_id, access),
                dismiss=False,
            )
            > 0
        )

    @staticmethod
    async def mark_all_as_read(
        session: AsyncSession, user_id: uuid.UUID, access: ProjectSet
    ) -> int:
        unread = NotificationManager.receipt_join(
            NotificationManager.in_scope(select(Notification.id), access), user_id
        ).where(NotificationReceipt.read_at.is_(None))
        return await NotificationManager._stamp(session, user_id, unread, dismiss=False)

    @staticmethod
    async def dismiss(
        session: AsyncSession,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
        access: ProjectSet,
    ) -> bool:
        return (
            await NotificationManager._stamp(
                session,
                user_id,
                NotificationManager._one(notification_id, access),
                dismiss=True,
            )
            > 0
        )

    @staticmethod
    async def dismiss_all(
        session: AsyncSession, user_id: uuid.UUID, access: ProjectSet
    ) -> int:
        shown = NotificationManager.receipt_join(
            NotificationManager.in_scope(select(Notification.id), access), user_id
        )
        return await NotificationManager._stamp(session, user_id, shown, dismiss=True)

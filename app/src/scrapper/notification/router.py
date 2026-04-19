from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from src.scrapper.notification.abstract import AbstractNotificationService, NotificationError

if TYPE_CHECKING:
    from uuid import UUID

    from src.scrapper.models import EventData
    from src.scrapper.notification.email_notification import EmailNotificationService
    from src.scrapper.repository.abstract import AbstractLinkRepository

__all__ = ("NotificationRouter",)

logger = logging.getLogger(__name__)


class NotificationRouter:
    def __init__(
        self,
        repository: AbstractLinkRepository,
        telegram_service: AbstractNotificationService,
        email_service: EmailNotificationService,
    ) -> None:
        self._repository = repository
        self._telegram_service = telegram_service
        self._email_service = email_service

    async def route(
        self,
        update_id: int,
        url: str,
        description: str,
        user_ids: list[UUID],
        event: EventData,
    ) -> None:
        if not user_ids:
            return

        routes = await self._repository.get_notification_routes(user_ids)

        tg_chat_ids = [
            r.tg_chat_id for r in routes if r.notify_telegram and r.tg_chat_id is not None
        ]
        emails = [r.email for r in routes if r.notify_email and r.email is not None]

        if tg_chat_ids:
            try:
                await self._telegram_service.send_update(
                    update_id=update_id,
                    url=url,
                    description=description,
                    tg_chat_ids=tg_chat_ids,
                )
            except NotificationError as exc:
                logger.exception(
                    "Telegram notification failed",
                    extra={"url": url, "error": str(exc)},
                )
            except Exception as exc:
                logger.exception(
                    "Telegram notification unexpected error",
                    extra={"url": url, "error": str(exc)},
                )

        if emails:
            try:
                await self._email_service.send_emails(emails, url, event)
            except Exception as exc:
                logger.exception(
                    "Email notification failed",
                    extra={"url": url, "error": str(exc)},
                )

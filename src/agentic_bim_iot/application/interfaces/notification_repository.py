from typing import Protocol

from agentic_bim_iot.domain.notification import Notification


class NotificationRepositoryError(RuntimeError):
    pass


class NotificationRepository(Protocol):
    """The norification repository contract"""
    def save(self, notification: Notification) -> None:
        ...

    def get(self, notification_id: str) -> Notification | None:
        ...

    def list_unread(self) -> list[Notification]:
        ...

    def mark_read(self, notification_id: str) -> None:
        ...

    def resolve_by_proposal(self, proposal_id: str) -> None:
        ...
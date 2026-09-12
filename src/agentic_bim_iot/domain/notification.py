from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field


class NotificationType(StrEnum):
    COMFORT_PROPOSAL = "comfort_proposal"


class NotificationStatus(StrEnum):
    """The possible state of a notification after is being generated"""
    UNREAD = "unread"
    READ = "read"
    RESOLVED = "resolved"


class Notification(BaseModel):
    """The Notification class  """
    model_config = ConfigDict(frozen=True)
    notification_id: str 
    notification_type: NotificationType
    status: NotificationStatus
    room_reference: str 
    proposal_id: str | None = None
    title: str 
    message: str 
    created_at_ms: int
    read_at_ms: int | None = None
    resolved_at_ms: int | None = None
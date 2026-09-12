from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field


class ProactiveCheckStatus(StrEnum):
    """The proactive check status"""
    COMFORTABLE = "comfortable"
    DATA_INCOMPLETE = "data_incomplete"
    PENDING_PROPOSAL_EXISTS = "pending_proposal_exists"
    COOLDOWN_ACTIVE = "cooldown_active"
    PROPOSAL_CREATED = "proposal_created"
    NO_ACTION_AVAILABLE = "no_action_available"
    FAILED = "failed"


class ProactiveCheckResult(BaseModel):
    """The result of the proactive check result"""
    model_config = ConfigDict(frozen=True)
    room_reference: str 
    status: ProactiveCheckStatus
    comfort_label: str | None = None
    comfort_score: int | None = None
    proposal_id: str | None = None
    message: str 
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from agentic_bim_iot.domain.comfort import ComfortAssessment
from agentic_bim_iot.domain.proposal import ActionProposal


class ApprovalOutcome(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFICATION_REQUESTED = "modification_requested"
    EXPIRED = "expired"
    STALE = "stale"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    ERROR = "error"


class ApprovalResult(BaseModel):
    """The result of the proposal"""
    model_config = ConfigDict(extra="forbid", frozen=True)
    outcome: ApprovalOutcome
    proposal: ActionProposal | None
    current_comfort_assessment: ComfortAssessment | None
    message: str = Field(min_length=1)
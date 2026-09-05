from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field
from agentic_bim_iot.domain.comfort import ComfortAssessment


class ProposalStatus(StrEnum):
    """The possible states of a proposal"""
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    EXECUTED = "executed"
    FAILED = "failed"
    STALE = "stale"


class ProposedAction(BaseModel):
    """The proposed action model"""
    model_config = ConfigDict(extra="forbid", frozen=True)
    action_id: str = Field(min_length=1)
    room_reference: str = Field(min_length=1)
    measurement: str = Field(min_length=1)
    current_value: float
    target_value: float
    unit: str = Field(min_length=1)
    actuator_guid: str = Field(min_length=1)
    actuator_type: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class ActionProposal(BaseModel):
    """The proposal that contains the actions """
    model_config = ConfigDict(extra="forbid", frozen=True)
    proposal_id: str = Field(min_length=1)
    room_reference: str = Field(min_length=1)
    actions: tuple[ProposedAction, ...] = Field(min_length=1)
    rationale: str = Field(min_length=1)
    status: ProposalStatus
    comfort_assessment: ComfortAssessment
    created_at_ms: int
    expires_at_ms: int
    supersedes_proposal_id: str | None = None


class PlanningResult(BaseModel):
    """The planning result"""
    model_config = ConfigDict(extra="forbid", frozen=True)
    comfort_assessment: ComfortAssessment
    proposal: ActionProposal | None
    message: str = Field(min_length=1)
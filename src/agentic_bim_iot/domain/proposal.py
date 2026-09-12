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


class ProposalSource(StrEnum):
    USER_REQUESTED = "user_requested"
    PROACTIVE_MONITOR = "proactive_monitor"



class ProposedAction(BaseModel):
    """The proposed action model"""
    model_config = ConfigDict(frozen=True)
    action_id: str 
    room_reference: str 
    measurement: str 
    current_value: float
    target_value: float
    unit: str 
    actuator_guid: str 
    actuator_type: str 
    reason: str 


class ActionProposal(BaseModel):
    """The proposal that contains the actions """
    model_config = ConfigDict(frozen=True)
    proposal_id: str 
    room_reference: str 
    actions: tuple[ProposedAction, ...] 
    rationale: str 
    status: ProposalStatus
    comfort_assessment: ComfortAssessment
    created_at_ms: int
    expires_at_ms: int
    supersedes_proposal_id: str | None = None
    source: ProposalSource = ProposalSource.USER_REQUESTED


class PlanningResult(BaseModel):
    """The planning result"""
    model_config = ConfigDict(frozen=True)
    comfort_assessment: ComfortAssessment
    proposal: ActionProposal | None
    message: str 
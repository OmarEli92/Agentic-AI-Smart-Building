from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field


class ActuationOperation(StrEnum):
    """The operation that could be executed"""
    SET_VALUE = "set_value"


class CommandAuthorizationSource(StrEnum):
    """The type of the command that could be received"""
    EXPLICIT_USER_REQUEST = "explicit_user_request"
    APPROVED_PROPOSAL = "approved_proposal"


class CommandStructuringStatus(StrEnum):
    """The status of the command"""
    READY = "ready"
    FAILED = "failed"


class ActuationCommand(BaseModel):
    """The actuation command"""
    model_config = ConfigDict(frozen=True)
    command_id: str 
    room_reference: str 
    measurement: str 
    operation: ActuationOperation
    target_value: float
    unit: str 
    actuator_guid: str 
    actuator_type: str 
    authorization_source: CommandAuthorizationSource
    proposal_id: str | None = None
    source_action_id: str | None = None
    created_at_ms: int


class CommandStructuringResult(BaseModel):
    """The acutal result of the command"""
    model_config = ConfigDict(frozen=True)
    status: CommandStructuringStatus
    commands: tuple[ActuationCommand, ...]
    message: str 
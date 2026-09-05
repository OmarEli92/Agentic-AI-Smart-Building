from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field


class ExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ExecutionBatchStatus(StrEnum):
    SUCCEEDED = "succeeded"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"


class ExecutionResult(BaseModel):
    """The execution result of a proposal"""
    model_config = ConfigDict(extra="forbid", frozen=True)
    execution_id: str = Field(min_length=1)
    command_id: str = Field(min_length=1)
    proposal_id: str | None = None
    room_reference: str = Field(min_length=1)
    measurement: str = Field(min_length=1)
    actuator_guid: str = Field(min_length=1)
    thingsboard_device_id: str | None = None
    target_value: float
    unit: str = Field(min_length=1)
    status: ExecutionStatus
    started_at_ms: int
    completed_at_ms: int
    error: str | None = None


class ExecutionBatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    status: ExecutionBatchStatus
    executions: tuple[ExecutionResult, ...]
    message: str = Field(min_length=1)
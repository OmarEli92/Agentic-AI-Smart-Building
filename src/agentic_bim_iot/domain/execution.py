from enum import StrEnum
from typing import Any
from pydantic import BaseModel, ConfigDict


class ExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ExecutionBatchStatus(StrEnum):
    SUCCEEDED = "succeeded"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"


class ExecutionResult(BaseModel):
    """The execution result of a proposal"""
    model_config = ConfigDict(frozen=True)
    execution_id: str 
    command_id: str 
    proposal_id: str | None = None
    room_reference: str 
    measurement: str 
    actuator_guid: str 
    thingsboard_device_id: str | None = None
    target_value: float
    unit: str 
    status: ExecutionStatus
    started_at_ms: int
    completed_at_ms: int
    error: str | None = None
    rpc_method: str | None = None
    rpc_response: Any | None = None


class ExecutionBatchResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    status: ExecutionBatchStatus
    executions: list[ExecutionResult]
    message: str 
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field
from agentic_bim_iot.domain.command import ActuationCommand


class SafetyValidationStatus(StrEnum):
    """The status of the safety validation of a command"""
    ALLOWED = "allowed"
    BLOCKED = "blocked"


class SafetyValidationResult(BaseModel):
    """The result of safety validation"""
    model_config = ConfigDict(frozen=True)
    status: SafetyValidationStatus
    commands: tuple[ActuationCommand, ...]
    violations: tuple[str, ...]
    message: str 
from typing import Protocol
from agentic_bim_iot.domain.command import ActuationCommand
from agentic_bim_iot.domain.safety import SafetyValidationResult


class SafetyPolicyValidator(Protocol):
    def validate(self, commands: tuple[ActuationCommand, ...]) -> SafetyValidationResult:
        ...
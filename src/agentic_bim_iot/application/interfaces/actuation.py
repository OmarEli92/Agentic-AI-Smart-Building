from typing import Protocol
from agentic_bim_iot.domain.command import ActuationCommand
from agentic_bim_iot.domain.execution import ExecutionResult


class ActuationService(Protocol):
    """The contract for the actuation service responsible for executing actuation on physical devices"""
    def execute(self, command: ActuationCommand) -> ExecutionResult:
        ...
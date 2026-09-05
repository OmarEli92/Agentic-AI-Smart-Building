from typing import Protocol
from agentic_bim_iot.domain.execution import ExecutionResult


class ExecutionRepositoryError(RuntimeError):
    pass


class ExecutionRepository(Protocol):
    """The contract for the execution repository"""
    def save(self, execution: ExecutionResult) -> None:
        ...

    def get(self, execution_id: str) -> ExecutionResult | None:
        ...

    def get_by_command_id(self, command_id: str) -> ExecutionResult | None:
        ...

    def get_latest(self) -> ExecutionResult | None:
        ...

    def list_by_proposal(self, proposal_id: str) -> list[ExecutionResult]:
        ...
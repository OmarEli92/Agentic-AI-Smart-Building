from typing import Protocol

from agentic_bim_iot.domain.command import CommandStructuringResult
from agentic_bim_iot.domain.models import SupervisorDecision
from agentic_bim_iot.domain.proposal import ActionProposal


class CommandStructuringError(RuntimeError):
    pass


class CommandStructurer(Protocol):
    """The contract for the command structurer"""
    def structure(self, user_query: str, supervisor_decision: SupervisorDecision, approved_proposal: ActionProposal | None = None) -> CommandStructuringResult:
        ...
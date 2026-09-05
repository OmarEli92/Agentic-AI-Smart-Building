from typing import Protocol
from agentic_bim_iot.domain.proposal import ActionProposal, PlanningResult


class PlanningEngineError(RuntimeError):
    pass


class PlanningEngine(Protocol):
    """The contract for the planning engine responsible for generating a plan of actions"""
    def plan(self, user_query: str, room_reference: str, previous_proposal : ActionProposal | None = None) -> PlanningResult:
        ...
from typing import Protocol

from langchain_core.runnables import RunnableConfig

from agentic_bim_iot.domain.comfort import ComfortAssessment
from agentic_bim_iot.domain.proposal import ActionProposal, PlanningResult, ProposalSource


class PlanningEngineError(RuntimeError):
    pass


class PlanningEngine(Protocol):
    """The contract for the planning engine responsible for generating a plan of actions."""

    def plan(self, user_query: str, room_reference: str, previous_proposal: ActionProposal | None = None, source: ProposalSource = ProposalSource.USER_REQUESTED, config: RunnableConfig | None = None) -> PlanningResult:
        ...

    def plan_from_assessment(self, user_query: str, room_reference: str, assessment: ComfortAssessment, previous_proposal: ActionProposal | None = None, source: ProposalSource = ProposalSource.USER_REQUESTED, config: RunnableConfig | None = None) -> PlanningResult:
        ...
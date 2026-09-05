import traceback

from agentic_bim_iot.application.graph.state import AgentState
from agentic_bim_iot.application.interfaces.planning import PlanningEngine, PlanningEngineError
from agentic_bim_iot.domain.approval import ApprovalOutcome
from agentic_bim_iot.domain.proposal import ActionProposal


class PlanningAgentNode:
    """The planning agent responsible for generating the plam"""
    def __init__(self, planning_engine: PlanningEngine | None) -> None:
        self._planning_engine = planning_engine

    def __call__(self, state: AgentState) -> dict[str, object]:
        if self._planning_engine is None:
            return {
                "planning_error": "Planning is not available for the configured semantic backend.",
                "final_answer": "Planning is not available for the configured semantic backend.",
            }

        decision = state.get("supervisor_decision")
        if decision is None:
            return {
                "planning_error": "The Supervisor decision is missing.",
                "final_answer": "I could not create an action proposal because the Supervisor decision is missing.",
            }

        previous_proposal = None
        room_reference = decision.room_reference
        approval_result = state.get("approval_result")

        if approval_result is not None and approval_result.outcome == ApprovalOutcome.MODIFICATION_REQUESTED:
            previous_proposal = approval_result.proposal
            if previous_proposal is not None and not room_reference:
                room_reference = previous_proposal.room_reference

        if not room_reference:
            return {
                "planning_error": "Room reference is required for planning.",
                "final_answer": "Which room would you like me to create an action recommendation for?",
            }

        try:
            result = self._planning_engine.plan(
                user_query=state["user_query"],
                room_reference=room_reference,
                previous_proposal=previous_proposal,
            )
        except PlanningEngineError as exc:
            print(f"\n{'=' * 70}\nPLANNING AGENT ERROR\n{'=' * 70}")
            traceback.print_exception(exc)
            print(f"{'=' * 70}\n")
            return {"planning_error": str(exc), "final_answer": str(exc)}

        if result.proposal is None:
            return {
                "comfort_assessment": result.comfort_assessment,
                "final_answer": result.message,
            }

        return {
            "comfort_assessment": result.comfort_assessment,
            "action_proposal": result.proposal,
            "final_answer": self._format_proposal(result.proposal),
        }

    @staticmethod
    def _format_proposal(proposal: ActionProposal) -> str:
        actions = [
            f"{a.measurement.capitalize()}: {a.current_value:g} {a.unit} -> {a.target_value:g} {a.unit} using {a.actuator_type}. {a.reason}"
            for a in proposal.actions
        ]
        return (
            f"Proposal {proposal.proposal_id} for {proposal.room_reference}: "
            f"{' '.join(actions)} {proposal.rationale} The proposal is pending approval."
        )
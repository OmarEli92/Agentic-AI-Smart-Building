from agentic_bim_iot.application.graph.state import AgentState
from agentic_bim_iot.application.interfaces.approval import ApprovalHandler, ApprovalHandlerError
from agentic_bim_iot.domain.approval import ApprovalOutcome, ApprovalResult


class ApprovalHandlerNode:
    def __init__(self, approval_handler: ApprovalHandler) -> None:
        self._approval_handler = approval_handler

    def __call__(self, state: AgentState) -> dict[str, object]:
        decision = state.get("supervisor_decision")

        if decision is None:
            result = ApprovalResult(
                outcome=ApprovalOutcome.ERROR,
                proposal=None,
                current_comfort_assessment=None,
                message="The Supervisor decision is missing.",
            )

            return {
                "approval_result": result,
                "approval_error": result.message,
                "final_answer": result.message,
            }

        try:
            result = self._approval_handler.handle(
                intent=decision.intent,
                user_query=state["user_query"],
                room_reference=decision.room_reference,
            )

        except ApprovalHandlerError as exc:
            result = ApprovalResult(
                outcome=ApprovalOutcome.ERROR,
                proposal=None,
                current_comfort_assessment=None,
                message=str(exc),
            )

            print()
            print("=" * 70)
            print("APPROVAL HANDLER ERROR")
            print("=" * 70)
            print(result.message)
            print("=" * 70)
            print()

            return {
                "approval_result": result,
                "approval_error": result.message,
                "final_answer": result.message,
            }

        print()
        print("=" * 70)
        print("APPROVAL RESULT")
        print("=" * 70)
        print(result)
        print("=" * 70)
        print()

        output: dict[str, object] = {
            "approval_result": result,
            "final_answer": result.message,
        }

        if result.proposal is not None:
            output["action_proposal"] = result.proposal

        if result.current_comfort_assessment is not None:
            output["comfort_assessment"] = result.current_comfort_assessment

        return output
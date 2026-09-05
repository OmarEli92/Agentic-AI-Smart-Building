from agentic_bim_iot.application.graph.state import AgentState
from agentic_bim_iot.application.interfaces.command import CommandStructurer, CommandStructuringError
from agentic_bim_iot.domain.approval import ApprovalOutcome
from agentic_bim_iot.domain.command import CommandStructuringResult, CommandStructuringStatus


class CommandStructuringNode:
    def __init__(self, command_structurer: CommandStructurer | None) -> None:
        self._command_structurer = command_structurer

    def __call__(self, state: AgentState) -> dict[str, object]:
        if self._command_structurer is None:
            result = CommandStructuringResult(status=CommandStructuringStatus.FAILED, commands=(), message="Command structuring is not available for the configured semantic backend.",)
            return {"command_result": result, "command_error": result.message, "final_answer": result.message}
        decision = state.get("supervisor_decision")
        if decision is None:
            result = CommandStructuringResult(status=CommandStructuringStatus.FAILED, commands=(), message="The Supervisor decision is missing.")
            return {"command_result": result, "command_error": result.message,"final_answer": result.message,}
        approved_proposal = None
        approval_result = state.get("approval_result")
        if approval_result is not None and approval_result.outcome == ApprovalOutcome.APPROVED:
            approved_proposal = approval_result.proposal

        try:
            result = self._command_structurer.structure(user_query=state["user_query"], supervisor_decision=decision, approved_proposal=approved_proposal)
        except CommandStructuringError as exc:
            result = CommandStructuringResult(status=CommandStructuringStatus.FAILED, commands=(), message=str(exc))
            return {"command_result": result, "command_error": str(exc), "final_answer": str(exc),}

        return {"command_result": result, "final_answer": result.message,}
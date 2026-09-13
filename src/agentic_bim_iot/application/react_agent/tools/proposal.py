from __future__ import annotations
from typing import Any
from langchain.tools import tool
from agentic_bim_iot.application.graph.dependencies import GraphDependencies
from agentic_bim_iot.application.react_agent.tools.common import Runtime, to_json, tool_command
from agentic_bim_iot.application.react_agent.tools.guards import verify_original_intent
from agentic_bim_iot.application.react_agent.tools.safe_actuation import SafeActuationExecutor
from agentic_bim_iot.domain.approval import ApprovalOutcome
from agentic_bim_iot.domain.enums import Intent
from agentic_bim_iot.domain.proposal import ProposalSource


def create_proposal_tools(*, dependencies: GraphDependencies, safe_actuation: SafeActuationExecutor) -> list[Any]:

    @tool
    def approve_and_execute_pending_proposal(runtime: Runtime):
        """
        Approve a pending proposal and execute it only afterfreshness, command structuring and safety validation."""
        decision, error = verify_original_intent(dependencies=dependencies, runtime=runtime,expected_intent=Intent.APPROVE_PROPOSAL)
        if error is not None or decision is None:
            return tool_command(runtime, error or "Approval authorization failed.")
        if not runtime.context.action_guard.claim("approve_and_execute_pending_proposal"):
            return tool_command(runtime, "Proposal approval/execution has already been attempted during this request.")
        try:
            approval = dependencies.approval_handler.handle(intent=Intent.APPROVE_PROPOSAL, user_query=runtime.context.user_query, room_reference=decision.room_reference)
            updates: dict[str, Any] = {"approval_result": approval}
            if approval.proposal is not None:
                updates["action_proposal"] = approval.proposal
            if approval.current_comfort_assessment is not None:
                updates["comfort_assessment"] = approval.current_comfort_assessment
            if approval.outcome != ApprovalOutcome.APPROVED or approval.proposal is None:
                return tool_command(runtime, approval.model_dump_json(indent=2), **updates)
            if dependencies.command_structurer is None:
                return tool_command(runtime, "Command structuring is unavailable for the configured semantic backend.", **updates)

            command_result = dependencies.command_structurer.structure(user_query=runtime.context.user_query, supervisor_decision=decision, approved_proposal=approval.proposal)
            return safe_actuation.execute(runtime=runtime, command_result=command_result, extra_updates=updates)
        except Exception as exc:
            return tool_command(runtime, f"Proposal approval/execution failed: {exc}")


    @tool
    def reject_pending_proposal(runtime: Runtime):
        """ Reject a pending proposal after validating that the original request explicitly asks for rejection."""
        decision, error = verify_original_intent(dependencies=dependencies, runtime=runtime, expected_intent=Intent.REJECT_PROPOSAL)
        if error is not None or decision is None:
            return tool_command(runtime, error or "Rejection authorization failed.")

        try:
            result = dependencies.approval_handler.handle(intent=Intent.REJECT_PROPOSAL, user_query=runtime.context.user_query, room_reference=decision.room_reference)
            updates: dict[str, Any] = {"approval_result": result}
            if result.proposal is not None:
                updates["action_proposal"] = result.proposal
            return tool_command(runtime, result.model_dump_json(indent=2), **updates)
        except Exception as exc:
            return tool_command(runtime, f"Proposal rejection failed: {exc}")


    @tool
    def modify_pending_proposal(runtime: Runtime):
        """Modify a pending proposal using the existing ApprovalHandler and PlanningEngine."""
        decision, error = verify_original_intent(dependencies=dependencies, runtime=runtime, expected_intent=Intent.MODIFY_PROPOSAL)
        if error is not None or decision is None:
            return tool_command(runtime, error or "Modification authorization failed.")

        try:
            approval = dependencies.approval_handler.handle(intent=Intent.MODIFY_PROPOSAL, user_query=runtime.context.user_query, room_reference=decision.room_reference)
            if approval.outcome != ApprovalOutcome.MODIFICATION_REQUESTED or approval.proposal is None:
                return tool_command(runtime, approval.model_dump_json(indent=2), approval_result=approval)
            if dependencies.planning_engine is None:
                return tool_command(runtime, "Planning is unavailable for the configured semantic backend.", approval_result=approval)
            result = dependencies.planning_engine.plan(user_query=runtime.context.user_query, room_reference=(approval.proposal.room_reference),previous_proposal=(approval.proposal))
            updates: dict[str, Any] = {"approval_result": approval, "comfort_assessment": result.comfort_assessment,}
            if result.proposal is not None:
                updates["action_proposal"] = result.proposal
            return tool_command(
                runtime,
                to_json({
                    "approval": approval.model_dump(mode="json"),
                    "message": result.message,
                    "replacement_proposal": (
                        result.proposal.model_dump(mode="json")
                        if result.proposal is not None
                        else None
                    ),
                }),
                **updates,
            )
        except Exception as exc:
            return tool_command(runtime, f"Proposal modification failed: {exc}")

    return [approve_and_execute_pending_proposal, reject_pending_proposal, modify_pending_proposal]
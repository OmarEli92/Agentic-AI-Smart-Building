from agentic_bim_iot.application.graph.state import AgentState
from agentic_bim_iot.domain.approval import ApprovalOutcome
from agentic_bim_iot.domain.command import CommandStructuringStatus
from agentic_bim_iot.domain.enums import Route
from agentic_bim_iot.domain.safety import SafetyValidationStatus



def route_after_supervisor(state: AgentState) -> Route:
    """Select the next graph branch from the structured Supervisor decision alreadu stored in the state"""
    decision = state["supervisor_decision"]
    if decision is None:
        raise RuntimeError("The Supervisor decision is missing from the graph state.")
    return decision.route




def route_after_approval(state: AgentState) -> ApprovalOutcome:
    approval_result = state.get("approval_result")
    if approval_result is None:
        return ApprovalOutcome.ERROR
    return approval_result.outcome




def route_after_command_structuring(state: AgentState) -> CommandStructuringStatus:
    command_result = state.get("command_result")
    if command_result is None:
        return CommandStructuringStatus.FAILED
    return command_result.status




def route_after_safety_validation(state: AgentState) -> SafetyValidationStatus:
    safety_result = state.get("safety_result")
    if safety_result is None:
        return SafetyValidationStatus.BLOCKED
    return safety_result.status
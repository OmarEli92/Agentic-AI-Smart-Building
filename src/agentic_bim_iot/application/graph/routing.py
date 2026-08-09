from agentic_bim_iot.application.graph.state import AgentState
from agentic_bim_iot.domain.enums import Route



def route_after_supervisor(state: AgentState) -> Route:
    """Select the next graph branch from the structured Supervisor decision alreadu stored in the state"""
    decision = state["supervisor_decision"]
    return decision.route
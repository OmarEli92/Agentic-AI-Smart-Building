from agentic_bim_iot.application.interfaces.supervisor import SuperVisor
from agentic_bim_iot.application.graph.state import AgentState

class SuperVisorNode:
    """An Adapter for the Supervisor node , it incapsulate the supervisor logic(the contract)"""
    def __init__(self, supervisor: SuperVisor):
        self._supervisor = supervisor
        
    def __call__(self, state: AgentState) -> dict[str, object]:
        decision = self._supervisor.decide(state['user_query'])
        return{"supervisor_decision": decision}

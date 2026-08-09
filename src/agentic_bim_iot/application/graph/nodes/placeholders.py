from agentic_bim_iot.application.graph.state import AgentState
from agentic_bim_iot.domain.enums import Route

class NotImplementedNode:
    """Questo lo uso solo ora come nodo temporaneo solo per assicurarmi che il workflow iniziale funzioni correttamente"""
    def __init__(self, route: Route):
        self._route = route
    
    def __call__(self, state: AgentState) -> dict[str, object]:
        return {"final_answer": f"Route '{self._route}' was selected correctly, but its component is not implemented yet."}
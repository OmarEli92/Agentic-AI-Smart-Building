from typing import Protocol
from agentic_bim_iot.application.graph.state import AgentState

class Node(Protocol):
    """The contract implemented by the LangGraph nodes"""
    def __call__(self, state: AgentState) -> dict[str, object]:
        ...
        
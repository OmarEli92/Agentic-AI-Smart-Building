from agentic_bim_iot.application.graph.state import AgentState

class RequestClarificationNode:
    """This node returnts the clarification question produced by the Supervisor
    in case the Facility Manager request was ambiguous."""
    def __call__(self, state: AgentState) -> dict[str, object]:
        decision = state['supervisor_decision']
        if not decision.clarification_question:
            raise ValueError("Classification route selected without a clarification question")
        
        return {"final_answer": decision.clarification_question}
    
class RespondUnsupportedNode:
    "This node handle the requests that are outside the supported system scope."
    def __call__(self, state: AgentState):
        return {"final_answer": "The request is outside the supported smart building workflow"}
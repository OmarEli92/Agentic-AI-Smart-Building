



from agentic_bim_iot.application.graph.state import AgentState
from agentic_bim_iot.application.interfaces.semantic import BIMQueryService, BIMQueryServiceError


class BIMInformationNode:
    """LangGraph node responsible for  BIM/Ontology information requests.
    """
    def __init__(self, bim_query_service: BIMQueryService):
        self._bim_query_service = bim_query_service
    
    def __call__(self, state: AgentState) -> dict [str, object]:
        try:
            result = self._bim_query_service.answer(state['user_query'])
        except BIMQueryServiceError as err:
            return {
                "semantic_error": str(err),
                "final_answer" : "I could not retrieve the requested BIM information."
            }
        return {
            "semantic_result": result,
            "final_answer": result.answer
        }




from agentic_bim_iot.application.graph.state import AgentState
from agentic_bim_iot.application.interfaces.semantic import SemanticQueryService, SemanticServiceError


class BIMInformationNode:
    """LangGraph node responsible for  BIM/Ontology information requests.
    """
    def __init__(self, semantic_service: SemanticQueryService):
        self._semantic_service = semantic_service
    
    def __call__(self, state: AgentState) -> dict [str, object]:
        try:
            result = self._semantic_service.answer_bim_query(state['user_query'])
        except SemanticServiceError as err:
            return {
                "semantic_error": str(err),
                "final_answer" : "I could not retrieve the requested BIM information."
            }
        return {
            "semantic_result": result,
            "final_answer": result.answer
        }
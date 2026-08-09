from agentic_bim_iot.application.graph.nodes.semantic import (
    BIMInformationNode,
)
from agentic_bim_iot.domain.semantic import SemanticQueryResult
from tests.fakes.semantic import FailingSemanticQueryService, FakeSemanticQueryService


def test_bim_information_node_returns_semantic_answer() -> None:
    semantic_result = SemanticQueryResult(
        answer=(
            "The first floor contains the Kitchen "
            "and the Living Room."
        ),
        generated_sparql=("SELECT ?room WHERE { ?floor ?p ?room . }"),
    )
    semantic_service = FakeSemanticQueryService(result=semantic_result)
    node = BIMInformationNode(semantic_service=semantic_service)
    state = {"user_query": ("Which rooms are located on the first floor?"),}
    result = node(state)
    assert result["semantic_result"] == semantic_result
    assert result["final_answer"] == (
        "The first floor contains the Kitchen "
        "and the Living Room."
    )
    assert semantic_service.received_queries == ["Which rooms are located on the first floor?"]
    
    
def test_bim_information_node_handles_expected_semantic_failure() -> None:
    node = BIMInformationNode(semantic_service=FailingSemanticQueryService())
    result = node({"user_query": "Which rooms are on the first floor?"})
    assert result["semantic_error"] == ("GraphDB is unavailable.")
    assert result["final_answer"] == ("I could not retrieve the requested BIM information.")
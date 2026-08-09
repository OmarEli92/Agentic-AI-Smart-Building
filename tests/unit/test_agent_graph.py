from agentic_bim_iot.application.graph.builder import build_agent_graph
from agentic_bim_iot.application.graph.dependencies import GraphDependencies
from agentic_bim_iot.domain.enums import Intent, Route
from agentic_bim_iot.domain.models import SupervisorDecision
from agentic_bim_iot.domain.semantic import SemanticQueryResult
from tests.fakes.semantic import FakeSemanticQueryService
from tests.fakes.supervisor import FakeSupervisor

def test_graph_routes_bim_request_to_bim_node():
    decision = SupervisorDecision(
        intent=Intent.BIM_INFORMATION,
        route=Route.BIM_AGENT,
        building_reference=None,
        floor_reference="first floor",
        room_reference=None,
        request_is_operational=False,
        request_is_explicit_actuation=False,
        clarification_required=False,
        clarification_question=None,
    )
    supervisor = FakeSupervisor(decision=decision,)
    graph = build_agent_graph(supervisor=supervisor)
    result = graph.invoke(
        {
            "user_query": (
                "Which rooms are located on the first floor?"
            ),
        }
    )
    
    assert result["supervisor_decision"] == decision
    assert result["final_answer"] == (
        "Route 'bim_agent' was selected correctly, "
        "but its component is not implemented yet."
    )
    
    
def test_graph_returns_requested_clarification() -> None:
    clarification = (
        "What target temperature should be set in the Kitchen?"
    )
    decision = SupervisorDecision(
        intent=Intent.DIRECT_ACTUATION,
        route=Route.REQUEST_CLARIFICATION,
        building_reference=None,
        floor_reference=None,
        room_reference="Kitchen",
        request_is_operational=True,
        request_is_explicit_actuation=True,
        clarification_required=True,
        clarification_question=clarification,
    )
    supervisor = FakeSupervisor(decision=decision)
    semantic_result = SemanticQueryResult(
        answer=(
            "Kitchen and Living Room are located "
            "on the first floor."
        )
    )
    semantic_service = FakeSemanticQueryService(result=semantic_result)
    dependencies = GraphDependencies(supervisor=supervisor,semantic_service=semantic_service,)
    graph = build_agent_graph(dependencies=dependencies)
    query = ("Which rooms are located on the first floor?")
    result = graph.invoke(
        {
            "user_query": query,
        }
    )
    
    assert result["supervisor_decision"] == decision
    assert result["semantic_result"] == semantic_result
    assert result["final_answer"] == (
        "Kitchen and Living Room are located "
        "on the first floor."
    )
    assert semantic_service.received_queries == [query]
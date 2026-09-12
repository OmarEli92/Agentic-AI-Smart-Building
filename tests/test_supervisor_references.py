from agentic_bim_iot.application.supervisor.reference_guard import extract_explicit_room_reference
from agentic_bim_iot.domain.enums import Intent, Route
from agentic_bim_iot.domain.models import SupervisorDecision
from agentic_bim_iot.infrastructure.llm.supervisor import LLMSupervisor


def test_extracts_kitchen_from_comfort_request() -> None:
    assert (extract_explicit_room_reference("What's the comfort in the Kitchen?") == "Kitchen")


def test_extracts_numeric_room_reference() -> None:
    assert extract_explicit_room_reference("Analyze comfort in room 101.") == "101"


def test_extracts_named_room_reference() -> None:
    assert (extract_explicit_room_reference("Improve comfort in Meeting Room 2.") == "Meeting Room 2")


def test_comfort_decision_recovers_explicit_room() -> None:
    incomplete = SupervisorDecision(intent=Intent.COMFORT_ANALYSIS, route=Route.COMFORT_ENGINE, room_reference=None,)
    recovered = LLMSupervisor._recover_explicit_references(user_query="What's the comfort in the Kitchen?", decision=incomplete)
    assert recovered.room_reference == "Kitchen"
    assert LLMSupervisor._requires_reference_repair(recovered) is False


def test_comfort_engine_never_receives_missing_room() -> None:
    incomplete = SupervisorDecision(intent=Intent.COMFORT_ANALYSIS, route=Route.COMFORT_ENGINE, room_reference=None)
    decision = LLMSupervisor._enforce_route_invariants(incomplete)
    assert decision.route == Route.REQUEST_CLARIFICATION
    assert decision.clarification_required is True
    assert decision.clarification_question is not None

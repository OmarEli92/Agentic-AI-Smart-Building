import pytest
from pydantic import ValidationError

from agentic_bim_iot.domain.enums import Intent, Route
from agentic_bim_iot.domain.models import SupervisorDecision

"""L'idea di questi test iniziali è semplicemente di verificare manualmente che il supervisor non accetti decisioni
incoerenti e contraddittoriee, attualmente è solo per verificare che i moduli siano importati correttamente al di fuori del src"""

def test_valid_explicit_direct_actuation() -> None:
    decision = SupervisorDecision(
        intent=Intent.DIRECT_ACTUATION,
        route=Route.COMMAND_STRUCTURING,
        building_reference="Open Smart Home",
        floor_reference=None,
        room_reference="Kitchen",
        request_is_operational=True,
        request_is_explicit_actuation=True,
        clarification_required=False,
        clarification_question=None,
        
    )

    assert decision.intent is Intent.DIRECT_ACTUATION
    assert decision.route is Route.COMMAND_STRUCTURING
    assert decision.room_reference == "Kitchen"
    assert decision.request_is_operational is True
    assert decision.request_is_explicit_actuation is True


def test_ambiguous_command_requires_a_question() -> None:
    with pytest.raises(ValidationError):
        SupervisorDecision(
            intent=Intent.DIRECT_ACTUATION,
            route=Route.REQUEST_CLARIFICATION,
            building_reference=None,
            floor_reference=None,
            room_reference="Kitchen",
            request_is_operational=True,
            request_is_explicit_actuation=True,
            clarification_required=True,
            clarification_question=None,
            
        )


def test_explicit_actuation_must_be_operational() -> None:
    with pytest.raises(ValidationError):
        SupervisorDecision(
            intent=Intent.DIRECT_ACTUATION,
            route=Route.COMMAND_STRUCTURING,
            building_reference=None,
            floor_reference=None,
            room_reference="Kitchen",
            request_is_operational=False,
            request_is_explicit_actuation=True,
            clarification_required=False,
            clarification_question=None,
        )
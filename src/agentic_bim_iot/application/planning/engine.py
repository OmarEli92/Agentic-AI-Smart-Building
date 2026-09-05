import json
import time
from typing import Any
from uuid import uuid4
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from agentic_bim_iot.application.interfaces.actuator import ActuatorResolutionError, ActuatorResolver
from agentic_bim_iot.application.interfaces.comfort import ComfortEngine, ComfortEngineError
from agentic_bim_iot.application.interfaces.planning import PlanningEngineError
from agentic_bim_iot.application.interfaces.proposal_repository import ProposalRepository, ProposalRepositoryError
from agentic_bim_iot.application.planning.models import PlanningDecisionDraft
from agentic_bim_iot.application.planning.prompt import PLANNING_SYSTEM_PROMPT
from agentic_bim_iot.domain.actuator import ActuatorReference
from agentic_bim_iot.domain.comfort import ComfortAssessment, ParameterComfortAssessment
from agentic_bim_iot.domain.proposal import ActionProposal, PlanningResult, ProposalStatus, ProposedAction


class LLMPlanningEngine:
    def __init__(self, chat_model: BaseChatModel, comfort_engine: ComfortEngine, actuator_resolver: ActuatorResolver,
        proposal_repository: ProposalRepository, proposal_ttl_seconds: int) -> None:
        self._comfort_engine = comfort_engine
        self._actuator_resolver = actuator_resolver
        self._proposal_repository = proposal_repository
        self._proposal_ttl_seconds = proposal_ttl_seconds
        self._structured_model = chat_model.with_structured_output(PlanningDecisionDraft, method="json_schema", strict=True, include_raw=True)

    def plan(self, user_query: str, room_reference: str, previous_proposal: ActionProposal | None = None) -> PlanningResult:
        room = room_reference.strip()
        if not room:
            raise PlanningEngineError("Room is required to create an action proposal.")
        try:
            assessment = self._comfort_engine.assess(room)
        except ComfortEngineError as exc:
            raise PlanningEngineError("The comfort assessment required by the planner failed.") from exc
        actionable_measurements = self._find_actionable_measurements(assessment)
        if not actionable_measurements:
            if previous_proposal is not None:
                self._mark_previous_proposal_stale(previous_proposal)
            return PlanningResult(comfort_assessment=assessment, proposal=None,message=f"No action proposal is required for {room} because the available comfort measurements are already within the configured ranges.",)
        try:
            actuator_references = self._actuator_resolver.resolve_many(room_reference=room, measurements=actionable_measurements)

        except ActuatorResolutionError as exc:
            raise PlanningEngineError("The actuator resolution required by the planner failed.") from exc
        candidates = self._build_candidates(assessment=assessment, actuator_references=actuator_references)
        if not candidates:
            return PlanningResult(comfort_assessment=assessment, proposal=None, message=f"The comfort assessment for {room} contains parameters outside the configured ranges, but no compatible actuator is available for those parameters.")
        draft = self._invoke_planner(
            user_query=user_query,
            room=room,
            assessment=assessment,
            candidates=candidates,
            previous_proposal=previous_proposal,
        )

        proposal = self._build_proposal(
            room=room,
            assessment=assessment,
            candidates=candidates,
            draft=draft,
            previous_proposal=previous_proposal
        )

        try:
            if previous_proposal is None:
                self._proposal_repository.save(proposal)
            else:
                self._proposal_repository.supersede(proposal=previous_proposal, replacement=proposal)

        except ProposalRepositoryError as exc:
            raise PlanningEngineError("The generated action proposal could not be persisted.") from exc
        return PlanningResult(comfort_assessment=assessment, proposal=proposal,
                    message=f"Action proposal '{proposal.proposal_id}' was created for {room} and is pending approval.",)

    @staticmethod
    def _find_actionable_measurements(assessment: ComfortAssessment) -> tuple[str, ...]:
        measurements = []
        for measurement, parameter in assessment.parameters.items():
            if parameter.value is None:
                continue
            if parameter.within_range is False:
                measurements.append(measurement)
        return tuple(measurements)

    @staticmethod
    def _build_candidates(assessment: ComfortAssessment, actuator_references: list[ActuatorReference]) -> dict[tuple[str, str], tuple[ActuatorReference, ParameterComfortAssessment]]:
        candidates: dict[tuple[str, str], tuple[ActuatorReference, ParameterComfortAssessment]] = {}

        for actuator in actuator_references:
            measurement = actuator.controlled_measurement.casefold()
            parameter = assessment.parameters.get(measurement)
            if parameter is None:
                continue
            if parameter.value is None:
                continue
            if parameter.within_range is not False:
                continue
            candidates[(measurement, actuator.actuator_guid)] = (actuator,parameter)
        return candidates

    def _invoke_planner(self, user_query: str, room: str, assessment: ComfortAssessment,
        candidates: dict[tuple[str, str], tuple[ActuatorReference, ParameterComfortAssessment]],
        previous_proposal: ActionProposal | None) -> PlanningDecisionDraft:
        candidate_payload = []
        for actuator, parameter in candidates.values():
            candidate_payload.append(
                {
                    "measurement": actuator.controlled_measurement,
                    "current_value": parameter.value,
                    "unit": parameter.unit,
                    "comfort_minimum": parameter.minimum,
                    "comfort_maximum": parameter.maximum,
                    "actuator_guid": actuator.actuator_guid,
                    "actuator_type": actuator.actuator_type,
                }
            )

        request_payload = {
            "facility_manager_request": user_query,
            "room_reference": room,
            "comfort_label": assessment.label.value,
            "comfort_score": assessment.total_score,
            "available_action_candidates": candidate_payload,
            "previous_proposal": previous_proposal.model_dump(mode="json") if previous_proposal is not None else None,
        }

        result: Any = self._structured_model.invoke([SystemMessage(content=PLANNING_SYSTEM_PROMPT),
                        HumanMessage(content=json.dumps(request_payload, indent=2))])

        if not isinstance(result, dict):
            raise PlanningEngineError("The planning model returned an unexpected structured-output result.")
        parsed = result.get("parsed")
        parsing_error = result.get("parsing_error")
        if isinstance(parsed, PlanningDecisionDraft):
            return parsed

        if parsing_error is not None:
            raise PlanningEngineError(f"The planning model returned invalid structured output: {parsing_error}")
        raise PlanningEngineError("The planning model did not return a valid proposal draft.")

    def _build_proposal(self, room: str,assessment: ComfortAssessment, candidates: dict[tuple[str, str], tuple[ActuatorReference, ParameterComfortAssessment]],
                        draft: PlanningDecisionDraft, previous_proposal: ActionProposal | None) -> ActionProposal:
        if not draft.actions:
            raise PlanningEngineError("The planning model returned no action despite having actionable actuator candidates.")

        proposed_actions = []
        used_measurements: set[str] = set()
        for draft_action in draft.actions:
            measurement = draft_action.measurement.strip().casefold()
            actuator_guid = draft_action.actuator_guid.strip()
            candidate_key = (measurement, actuator_guid)
            if candidate_key not in candidates:
                raise PlanningEngineError(
                    f"The planning model selected an actuator that was not provided by the semantic grounding layer for measurement '{measurement}'.")
            if measurement in used_measurements:
                raise PlanningEngineError(f"The planning model returned multiple actions for measurement '{measurement}'.")
            actuator, parameter = candidates[candidate_key]
            if parameter.value is None:
                raise PlanningEngineError(f"The current value for measurement '{measurement}' is unavailable.")
            target_value = float(draft_action.target_value)
            if not parameter.minimum <= target_value <= parameter.maximum:
                raise PlanningEngineError(f"The planning model proposed target {target_value} {parameter.unit} for '{measurement}', outside the configured comfort range {parameter.minimum}-{parameter.maximum} {parameter.unit}.")
            reason = draft_action.reason.strip()
            if not reason:
                raise PlanningEngineError(f"The planning model returned an empty reason for measurement '{measurement}'.")

            proposed_actions.append(
                ProposedAction(action_id=str(uuid4()),
                    room_reference=room,
                    measurement=measurement,
                    current_value=parameter.value,
                    target_value=target_value,
                    unit=parameter.unit,
                    actuator_guid=actuator.actuator_guid,
                    actuator_type=actuator.actuator_type,
                    reason=reason
                )
            )
            used_measurements.add(measurement)

        rationale = draft.rationale.strip()
        if not rationale:
            raise PlanningEngineError("The planning model returned an empty proposal rationale.")

        created_at_ms = time.time_ns() // 1_000_000
        expires_at_ms = created_at_ms + self._proposal_ttl_seconds * 1000

        return ActionProposal(proposal_id=str(uuid4()),
            room_reference=room,
            actions=tuple(proposed_actions),
            rationale=rationale,
            status=ProposalStatus.PENDING_APPROVAL,
            comfort_assessment=assessment,
            created_at_ms=created_at_ms,
            expires_at_ms=expires_at_ms,
            supersedes_proposal_id=previous_proposal.proposal_id if previous_proposal is not None else None,
        )

    def _mark_previous_proposal_stale(self, proposal: ActionProposal) -> None:
        stale_proposal = proposal.model_copy(update={"status": ProposalStatus.STALE})
        try:
            self._proposal_repository.update(stale_proposal)
        except ProposalRepositoryError as exc:
            raise PlanningEngineError("The previous proposal could not be invalidated.") from exc
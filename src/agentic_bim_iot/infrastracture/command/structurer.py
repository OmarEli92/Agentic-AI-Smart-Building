import json
import time
from typing import Any
from uuid import uuid4
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from agentic_bim_iot.application.command.models import DirectCommandDraft
from agentic_bim_iot.application.command.prompt import DIRECT_COMMAND_SYSTEM_PROMPT
from agentic_bim_iot.application.interfaces.actuator import ActuatorResolutionError, ActuatorResolver
from agentic_bim_iot.application.interfaces.command import CommandStructuringError
from agentic_bim_iot.domain.command import ActuationCommand, ActuationOperation, CommandAuthorizationSource, CommandStructuringResult, CommandStructuringStatus
from agentic_bim_iot.domain.comfort import MEASUREMENT_UNITS
from agentic_bim_iot.domain.enums import Intent
from agentic_bim_iot.domain.models import SupervisorDecision
from agentic_bim_iot.domain.proposal import ActionProposal, ProposalStatus
from agentic_bim_iot.infrastracture.observability.tracing import llm_run_config


class HybridCommandStructurer:
    """This class is responsible for transforming an operative request into one or more structured AcutationCommand"""
    def __init__(self, chat_model: BaseChatModel, actuator_resolver: ActuatorResolver) -> None:
        self._actuator_resolver = actuator_resolver
        self._structured_model = chat_model.with_structured_output(DirectCommandDraft, method="json_schema", strict=True, include_raw=True)

    def structure(self, user_query: str, supervisor_decision: SupervisorDecision, approved_proposal: ActionProposal | None = None) -> CommandStructuringResult:
        if approved_proposal is not None:
            return self._structure_approved_proposal(approved_proposal)

        return self._structure_direct_command(user_query=user_query, supervisor_decision=supervisor_decision)


    def _structure_approved_proposal(self, proposal: ActionProposal) -> CommandStructuringResult:
        if proposal.status != ProposalStatus.APPROVED:
            raise CommandStructuringError(f"Proposal '{proposal.proposal_id}' is not approved.")
        created_at_ms = time.time_ns() // 1_000_000
        commands = tuple(
            ActuationCommand(
                command_id=str(uuid4()),
                room_reference=action.room_reference,
                measurement=action.measurement,
                operation=ActuationOperation.SET_VALUE,
                target_value=action.target_value,
                unit=action.unit,
                actuator_guid=action.actuator_guid,
                actuator_type=action.actuator_type,
                authorization_source=CommandAuthorizationSource.APPROVED_PROPOSAL,
                proposal_id=proposal.proposal_id,
                source_action_id=action.action_id,
                created_at_ms=created_at_ms,
            )
            for action in proposal.actions)

        if not commands:
            raise CommandStructuringError(f"Proposal '{proposal.proposal_id}' does not contain executable actions.")
        return CommandStructuringResult(
            status=CommandStructuringStatus.READY,
            commands=commands,
            message=f"Proposal '{proposal.proposal_id}' was converted into {len(commands)} actuation command(s).",
        )

    def _structure_direct_command(self, user_query: str, supervisor_decision: SupervisorDecision) -> CommandStructuringResult:
        if supervisor_decision.intent != Intent.DIRECT_ACTUATION:
            raise CommandStructuringError("Direct command structuring requires a direct actuation intent.")
        if not supervisor_decision.request_is_explicit_actuation:
            raise CommandStructuringError("The request does not contain explicit actuation authorization.")
        room_reference = supervisor_decision.room_reference.strip() if supervisor_decision.room_reference else ""
        measurement = supervisor_decision.measurement_reference.strip().casefold() if supervisor_decision.measurement_reference else ""
        if not room_reference:
            raise CommandStructuringError("Room reference is required for direct actuation.")
        if not measurement:
            raise CommandStructuringError("Measurement reference is required for direct actuation.")
        if measurement not in MEASUREMENT_UNITS:
            raise CommandStructuringError(f"Measurement '{measurement}' is not supported for direct actuation.")
        draft = self._extract_direct_target(user_query=user_query, room_reference=room_reference, measurement=measurement)
        if draft.target_value is None:
            raise CommandStructuringError("An explicit absolute target value is required for direct actuation.")
        try:
            actuator = self._actuator_resolver.resolve(room_reference=room_reference, measurement=measurement)
        except ActuatorResolutionError as exc:
            raise CommandStructuringError("No compatible actuator could be grounded for the direct command.") from exc
        command = ActuationCommand(
            command_id=str(uuid4()),
            room_reference=room_reference,
            measurement=measurement,
            operation=ActuationOperation.SET_VALUE,
            target_value=float(draft.target_value),
            unit=MEASUREMENT_UNITS[measurement],
            actuator_guid=actuator.actuator_guid,
            actuator_type=actuator.actuator_type,
            authorization_source=CommandAuthorizationSource.EXPLICIT_USER_REQUEST,
            proposal_id=None,
            source_action_id=None,
            created_at_ms=time.time_ns() // 1_000_000,
        )
        return CommandStructuringResult(status=CommandStructuringStatus.READY, commands=(command,), message=f"The direct request was structured into an actuation command for {room_reference}.",)

    def _extract_direct_target(self, user_query: str, room_reference: str, measurement: str) -> DirectCommandDraft:
        payload = {
            "facility_manager_request": user_query,
            "resolved_room_reference": room_reference,
            "resolved_measurement": measurement,
            "canonical_unit": MEASUREMENT_UNITS[measurement],
        }
        result: Any = self._structured_model.invoke([SystemMessage(content=DIRECT_COMMAND_SYSTEM_PROMPT),
                                                     HumanMessage(content=json.dumps(payload, indent=2)),]
                                                    ,config=llm_run_config(
                                                    component="command_structuring",
                                                    operation="target_extraction",
                                                    ))
        if not isinstance(result, dict):
            raise CommandStructuringError("The command structuring model returned an unexpected structured-output result.")
        parsed = result.get("parsed")
        parsing_error = result.get("parsing_error")
        if isinstance(parsed, DirectCommandDraft):
            return parsed
        if parsing_error is not None:
            raise CommandStructuringError(f"The command structuring model returned invalid structured output: {parsing_error}")
        raise CommandStructuringError("The command structuring model did not return a valid direct command draft.")

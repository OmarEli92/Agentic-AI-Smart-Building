from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from agentic_bim_iot.application.supervisor.models import SupervisorDecisionDraft
from agentic_bim_iot.application.supervisor.prompt import SUPERVISOR_SYSTEM_PROMPT
from agentic_bim_iot.application.supervisor.reference_guard import (
    extract_explicit_measurement_reference,
    extract_explicit_room_reference,
)
from agentic_bim_iot.domain.enums import Intent, Route
from agentic_bim_iot.domain.models import SupervisorDecision
from agentic_bim_iot.infrastracture.observability.tracing import llm_run_config


class LLMSupervisor:
    """The LLMSupervisor class represents the implementation of the Supervisor contract.
    This component is provider agnostic: any LangChain/LangGraph BaseChatModel
    that supports structured output can be used.
    """

    def __init__(self, chat_model: BaseChatModel, system_prompt: str = SUPERVISOR_SYSTEM_PROMPT):
        self._system_prompt = system_prompt
        self.structured_model = chat_model.with_structured_output(
            SupervisorDecisionDraft,
            method="json_schema",
            strict=True,
            include_raw=True,
        )

    def decide(self, user_query: str) -> SupervisorDecision:
        """Interpret a Facility Manager request and produce a safe routing decision."""
        normalized_query = user_query.strip()
        if not normalized_query:
            raise ValueError("User query cannot be empty!")

        draft, raw_output = self._invoke(user_query=normalized_query)

        if draft is None:
            print("Supervisor structured output invalid. Requesting one bounded repair...")
            draft, _ = self._repair_invalid_output(user_query=normalized_query, raw_output=raw_output)

        if draft is None:
            decision = self._safe_clarification_decision()
            self._print_decision(decision)
            return decision

        draft = self._recover_explicit_references(user_query=normalized_query, decision=draft)

        if self._requires_reference_repair(draft):
            print("Supervisor reference extraction incomplete. Requesting one bounded repair...")
            repaired_draft, _ = self._repair_incomplete_decision(
                user_query=normalized_query,
                previous_decision=draft,
            )
            if repaired_draft is not None:
                draft = repaired_draft

            draft = self._recover_explicit_references(user_query=normalized_query, decision=draft)

        draft = self._enforce_route_invariants(draft)
        decision = SupervisorDecision.model_validate(draft.model_dump())
        self._print_decision(decision)
        return decision

    def _invoke(self, user_query: str) -> tuple[SupervisorDecisionDraft | None, str]:
        messages = [
            SystemMessage(content=self._system_prompt),
            HumanMessage(content=user_query),
        ]
        return self._invoke_structured(messages, operation="decision")

    def _invoke_structured(self, messages: list[SystemMessage | HumanMessage], *, 
                           operation: str, repair_attempt: bool = False) -> tuple[SupervisorDecisionDraft | None, str]:
        result: Any = self.structured_model.invoke(messages,config=llm_run_config(
            component="supervisor",
            operation=operation,
            repair_attempt=repair_attempt,
        ))
        parsed = result.get("parsed") if isinstance(result, dict) else None
        parsing_error = result.get("parsing_error") if isinstance(result, dict) else None
        raw_output = self._extract_raw_output(result.get("raw") if isinstance(result, dict) else None)
        if isinstance(parsed, SupervisorDecisionDraft):
            return parsed, raw_output
        if parsing_error is not None:
            print(f"Supervisor structured output parsing failed: {parsing_error}")
        return None, raw_output

    @staticmethod
    def _recover_explicit_references(*, user_query: str, decision: SupervisorDecisionDraft) -> SupervisorDecisionDraft:
        """Recover explicit references omitted by the LLM without reclassifying intent."""
        updates: dict[str, object] = {}
        if not decision.room_reference:
            room_reference = extract_explicit_room_reference(user_query)
            if room_reference:
                updates["room_reference"] = room_reference
        if (
            decision.intent in {Intent.TELEMETRY_INFORMATION, Intent.DIRECT_ACTUATION}
            and not decision.measurement_reference):
            measurement_reference = extract_explicit_measurement_reference(user_query)
            if measurement_reference:
                updates["measurement_reference"] = measurement_reference

        if not updates:
            return decision
        return decision.model_copy(update=updates)

    @staticmethod
    def _requires_reference_repair(decision: SupervisorDecisionDraft) -> bool:
        """Return True only when the selected workflow is missing required references."""
        if decision.intent == Intent.COMFORT_ANALYSIS:
            return not decision.room_reference
        if decision.intent in {Intent.TELEMETRY_INFORMATION, Intent.DIRECT_ACTUATION}:
            return not decision.room_reference or not decision.measurement_reference
        return False

    def _repair_invalid_output(self, *, user_query: str, raw_output: str) -> tuple[SupervisorDecisionDraft | None, str]:
        """Perform one repair when the first structured output cannot be parsed."""
        repair_prompt = f"""
You are repairing an invalid structured Supervisor output.

Original Facility Manager request:
{user_query}

Previous raw model output:
{raw_output or "<empty>"}

Re-read the ORIGINAL request and return one complete object matching the structured schema.

Every schema field must be present.
Use null only for nullable references that are genuinely absent.
Do not omit boolean fields.
Do not invent references.

Classify the request from the original text, not from the previous invalid output.

For ordinary informational telemetry questions such as temperature, humidity
or brightness retrieval, use intent = "telemetry_information" and
route = "telemetry_agent" when room and measurement are available.

For comfort evaluation requests, use intent = "comfort_analysis" and
route = "comfort_engine" when the room is available.

For explicit actuation commands that directly request a concrete physical
change, use intent = "direct_actuation".
Recover the explicit room and measurement whenever they are present.
Set request_is_operational = true.
Set request_is_explicit_actuation = true only when the user clearly requests
that the system perform the action.

Only proposal approval/modification/rejection requests may use the
corresponding proposal intents.

Return only the complete structured object required by the schema.
""".strip()

        messages = [
            SystemMessage(content=repair_prompt),
            HumanMessage(content=user_query),
        ]
        return self._invoke_structured(messages,operation="invalid_output_repair",repair_attempt=True)


    def _repair_incomplete_decision(self, *, user_query: str, previous_decision: SupervisorDecisionDraft) -> tuple[SupervisorDecisionDraft | None, str]:
        """Perform one targeted repair of missing workflow references."""
        repair_prompt = f"""
You are repairing an incomplete structured Supervisor decision.

Original Facility Manager request:
{user_query}

Previous structured decision:
{previous_decision.model_dump_json(indent=2)}

The intent classification is already available. Your task is to re-read the
ORIGINAL request and recover any explicit reference that was omitted.

CRITICAL RULES:

- Preserve the existing intent unless it is clearly inconsistent with the original request.
- If the original request explicitly contains a room or named space, copy it into room_reference.
- For telemetry_information, recover measurement_reference when the measurement is explicitly present.
- For direct_actuation, recover room_reference and measurement_reference whenever they are explicitly present.
- Do not invent references.
- Every schema field must be present in the output.
- Use null for nullable fields that are genuinely absent.

Workflow invariants:

1. comfort_analysis
   - If a room is present: route = "comfort_engine", clarification_required = false.
   - If no room is present: route = "request_clarification", clarification_required = true, and ask which room should be analyzed.

2. telemetry_information
   - If room and measurement are present: route = "telemetry_agent", clarification_required = false.
   - If either is genuinely absent: route = "request_clarification", clarification_required = true, and ask only for the missing information.

3. direct_actuation
   - If the request is an explicit command and room and measurement are present:
     route = "command_structuring", request_is_operational = true, request_is_explicit_actuation = true, clarification_required = false.
   - If the request expresses only a desired outcome without explicitly asking the system to execute an action:
     route = "planning_agent".
   - If the request is explicit but room or measurement is genuinely absent:
     route = "request_clarification", clarification_required = true, and ask only for the missing information.

Return the complete structured decision required by the schema.
""".strip()

        messages = [
            SystemMessage(content=repair_prompt),
            HumanMessage(content=user_query),
        ]
        return self._invoke_structured(messages,operation="invalid_output_repair", repair_attempt=True)

    @staticmethod
    def _enforce_route_invariants(decision: SupervisorDecisionDraft) -> SupervisorDecisionDraft:
        """Prevent downstream nodes from receiving structurally unusable decisions."""
        updates: dict[str, object] = {}
        if decision.request_is_explicit_actuation and not decision.request_is_operational:
            updates["request_is_operational"] = True
        if decision.intent == Intent.COMFORT_ANALYSIS:
            if decision.room_reference:
                updates.update({
                    "route": Route.COMFORT_ENGINE,
                    "clarification_required": False,
                    "clarification_question": None,
                })
            else:
                updates.update({
                    "route": Route.REQUEST_CLARIFICATION,
                    "clarification_required": True,
                    "clarification_question": "Which room would you like me to analyze?",
                })
            return decision.model_copy(update=updates)
        if decision.intent == Intent.TELEMETRY_INFORMATION:
            missing_room = not decision.room_reference
            missing_measurement = not decision.measurement_reference
            if not missing_room and not missing_measurement:
                updates.update({
                    "route": Route.TELEMETRY_AGENT,
                    "clarification_required": False,
                    "clarification_question": None,
                })
            else:
                if missing_room and missing_measurement:
                    question = "Which room and measurement would you like me to retrieve?"
                elif missing_room:
                    question = "Which room would you like me to retrieve the measurement from?"
                else:
                    question = "Which measurement would you like me to retrieve?"
                updates.update({
                    "route": Route.REQUEST_CLARIFICATION,
                    "clarification_required": True,
                    "clarification_question": decision.clarification_question or question,
                })
            return decision.model_copy(update=updates)
        if decision.intent == Intent.DIRECT_ACTUATION:
            if not decision.request_is_explicit_actuation:
                updates.update({
                    "route": Route.PLANNING_AGENT,
                    "clarification_required": False,
                    "clarification_question": None,
                })
                return decision.model_copy(update=updates)
            missing_room = not decision.room_reference
            missing_measurement = not decision.measurement_reference
            if not missing_room and not missing_measurement:
                updates.update({
                    "route": Route.COMMAND_STRUCTURING,
                    "request_is_operational": True,
                    "request_is_explicit_actuation": True,
                    "clarification_required": False,
                    "clarification_question": None,
                })
            else:
                if missing_room and missing_measurement:
                    question = "Which room and measurement should I control?"
                elif missing_room:
                    question = "Which room should I apply the command to?"
                else:
                    question = "Which measurement should I control?"
                updates.update({
                    "route": Route.REQUEST_CLARIFICATION,
                    "request_is_operational": True,
                    "request_is_explicit_actuation": True,
                    "clarification_required": True,
                    "clarification_question": question,
                })
            return decision.model_copy(update=updates)

        if decision.clarification_required:
            updates["route"] = Route.REQUEST_CLARIFICATION
            if not decision.clarification_question:
                updates["clarification_question"] = "Could you clarify the missing information in your request?"
            return decision.model_copy(update=updates)
        route_by_intent = {
            Intent.BIM_INFORMATION: Route.BIM_AGENT,
            Intent.ACTION_RECOMMENDATION: Route.PLANNING_AGENT,
            Intent.MODIFY_PROPOSAL: Route.APPROVAL_HANDLER,
            Intent.APPROVE_PROPOSAL: Route.APPROVAL_HANDLER,
            Intent.REJECT_PROPOSAL: Route.APPROVAL_HANDLER,
            Intent.EXECUTION_STATUS: Route.EXECUTION_STATUS,
            Intent.UNSUPPORTED: Route.RESPOND_UNSUPPORTED,
        }
        if decision.intent in route_by_intent:
            updates["route"] = route_by_intent[decision.intent]
        updates["clarification_required"] = False
        updates["clarification_question"] = None
        return decision.model_copy(update=updates)

    @staticmethod
    def _safe_clarification_decision() -> SupervisorDecision:
        return SupervisorDecision(
            intent=Intent.UNSUPPORTED,
            route=Route.REQUEST_CLARIFICATION,
            building_reference=None,
            floor_reference=None,
            room_reference=None,
            request_is_operational=False,
            request_is_explicit_actuation=False,
            clarification_required=True,
            clarification_question="I could not reliably interpret the request. Could you rephrase it?",
            measurement_reference=None,
        )

    @staticmethod
    def _extract_raw_output(raw_message: object | None) -> str:
        if raw_message is None:
            return ""
        content = getattr(raw_message, "content", "")
        return content if isinstance(content, str) else str(content)

    @staticmethod
    def _print_decision(decision: SupervisorDecision) -> None:
        print(f"\n{'=' * 70}\nSUPERVISOR DECISION\n{'=' * 70}\n{decision}\n{'=' * 70}\n")
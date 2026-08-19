from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from agentic_bim_iot.application.supervisor.prompt import SUPERVISOR_SYSTEM_PROMPT
from agentic_bim_iot.domain.enums import Intent, Route
from agentic_bim_iot.domain.models import SupervisorDecision


class LLMSupervisor:
    """The LLMSupervisor class represents the implementation of the Supervisor contract.

    This component is provider agnostic: any LangChain/LangGraph BaseChatModel
    that supports structured output can be used.
    """

    def __init__(self, chat_model: BaseChatModel, system_prompt: str = SUPERVISOR_SYSTEM_PROMPT):
        self._system_prompt = system_prompt
        self.structured_model = chat_model.with_structured_output(SupervisorDecision, method="json_schema", strict=True)

    def decide(self, user_query: str) -> SupervisorDecision:
        """Interpret the Facility Manager request and produce a valid SupervisorDecision object."""

        normalized_query = user_query.strip()
        if not normalized_query:
            raise ValueError("User query cannot be empty!")

        decision = self._invoke(user_query=normalized_query)

        print()
        print("=" * 70)
        print("SUPERVISOR DECISION")
        print("=" * 70)
        print(decision)
        print("=" * 70)
        print()

        if self._requires_telemetry_repair(decision):
            print("Supervisor telemetry extraction incomplete. Requesting one bounded repair...")
            decision = self._repair_telemetry_decision(user_query=normalized_query, previous_decision=decision)

            print()
            print("=" * 70)
            print("SUPERVISOR REPAIRED DECISION")
            print("=" * 70)
            print(decision)
            print("=" * 70)
            print()

        return decision

    def _invoke(self, user_query: str) -> SupervisorDecision:
        messages = [SystemMessage(content=self._system_prompt), HumanMessage(content=user_query)]
        return self.structured_model.invoke(messages)

    @staticmethod
    def _requires_telemetry_repair(decision: SupervisorDecision) -> bool:
        return decision.intent == Intent.TELEMETRY_INFORMATION and (not decision.room_reference or not decision.measurement_reference)

    def _repair_telemetry_decision(self, *, user_query: str, previous_decision: SupervisorDecision) -> SupervisorDecision:
        repair_prompt = f"""
        You are repairing an incomplete structured SupervisorDecision for a telemetry request.

        Original Facility Manager request:
        {user_query}

        Previous structured decision:
        {previous_decision.model_dump_json(indent=2)}

        The previous decision already classified the request as telemetry_information, but room_reference, measurement_reference, or both are missing.

        Read the ORIGINAL user request carefully and return a complete SupervisorDecision.

        For this repair:

        - Preserve intent = "telemetry_information".
        - If the original request explicitly contains a room, extract it into room_reference.
        - If the original request explicitly contains a measurement, extract it into measurement_reference.
        - Examples of measurements are temperature, humidity, brightness, CO2 and other sensor measurements.
        - Do not invent a room or measurement.
        - Do not discard information that is explicitly present in the original request.
        - If both room_reference and measurement_reference can be extracted, use route = "telemetry_agent" and clarification_required = false.
        - If one of them is genuinely absent from the original request, use route = "request_clarification", clarification_required = true and provide clarification_question.
        - Preserve the other fields from the previous decision unless the original request requires changing them.

        Examples:

        Original request:
        What is the temperature in the Kitchen?

        Required fields:
        room_reference = "Kitchen"
        measurement_reference = "temperature"
        route = "telemetry_agent"
        clarification_required = false

        Original request:
        What is the humidity in the Bathroom?

        Required fields:
        room_reference = "Bathroom"
        measurement_reference = "humidity"
        route = "telemetry_agent"
        clarification_required = false

        Return the complete structured SupervisorDecision required by the schema.
        """.strip()

        messages = [SystemMessage(content=repair_prompt), HumanMessage(content=user_query)]
        repaired_decision = self.structured_model.invoke(messages)

        if repaired_decision.room_reference and repaired_decision.measurement_reference:
            return repaired_decision.model_copy(update={"intent": Intent.TELEMETRY_INFORMATION, "route": Route.TELEMETRY_AGENT, "clarification_required": False, "clarification_question": None})

        return repaired_decision.model_copy(update={"intent": Intent.TELEMETRY_INFORMATION, "route": Route.REQUEST_CLARIFICATION, "clarification_required": True, "clarification_question": repaired_decision.clarification_question or "Which room and measurement would you like me to retrieve?"})
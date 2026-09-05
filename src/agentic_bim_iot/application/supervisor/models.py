from pydantic import BaseModel, ConfigDict, Field
from agentic_bim_iot.domain.enums import Intent, Route


class SupervisorDecisionDraft(BaseModel):
    """Untrusted structured output produced by the LLM Supervisor before domain validation."""
    model_config = ConfigDict(extra="forbid")
    intent: Intent = Field(description="Primary intent of the Facility Manager request")
    route: Route = Field(description="Route proposed by the LLM before deterministic normalization")
    building_reference: str | None = Field(description="Building reference explicitly present in the request, otherwise null")
    floor_reference: str | None = Field(description="Floor reference explicitly present in the request, otherwise null")
    room_reference: str | None = Field(description="Room or named space explicitly present in the request, otherwise null")
    request_is_operational: bool = Field(description="True if the request may change the physical environment")
    request_is_explicit_actuation: bool = Field(description="True if the user explicitly specified the physical action")
    clarification_required: bool = Field(description="True if the request cannot safely continue without clarification")
    clarification_question: str | None = Field(description="Clarification question when clarification is required, otherwise null")
    measurement_reference: str | None = Field(description="Measurement explicitly requested by the user, otherwise null")
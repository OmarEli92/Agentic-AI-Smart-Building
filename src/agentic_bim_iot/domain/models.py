from typing import Self
from pydantic import BaseModel, ConfigDict, Field, model_validator
from agentic_bim_iot.domain.enums import Intent, Route


class SupervisorDecision(BaseModel):
    """It represents the structured decision produced by the LLM based Supervisor
    which is the agent who interpet the intent of a request from the Facility Manager.
    It also defines a contract of how the output should be structured"""
    model_config = ConfigDict(extra="forbid")
    intent: Intent = Field(
        description="Primary intent of the Facility Manager request"
    )
    route: Route = Field(
        description="Next LangGraph node to execute."
    )
    building_reference: str | None = None
    floor_reference: str | None = None
    room_reference: str | None = Field(
        default=None,
        description=(
            "Room explicitly mentioned in the user request. "
            "Example: in 'What is the temperature in the Kitchen?' "
            "the value is 'Kitchen'."
        )
    )
    request_is_operational: bool = Field(
        description="True if the request may change the physical environment.",
        default=False
    )
    request_is_explicit_actuation: bool = Field(
        description="True if the user explicitly specified the physical action.",
        default=False
    )
    clarification_required: bool = Field(
        description="True if execution cannot safely continue without clarification.",
        default=False
    )
    clarification_question: str | None = None
    measurement_reference: str | None = Field(
    default=None,
    description=("Measurement explicitly requested by the user. "
            "Examples: temperature, humidity, brightness. "
            "In 'What is the temperature in the Kitchen?' "
            "the value is 'temperature'.")
    )


    @model_validator(mode="after")
    def validate_decision_consistency(self) -> Self:
        """This method checks the coherence and consistency of the intentions and routes """
        if self.clarification_required:
            if self.route is not Route.REQUEST_CLARIFICATION:
                raise ValueError(
                    "Clarification requires the type Route.REQUEST_CLARIFICATIOON"
                )
            
            if not self.clarification_question:
                raise ValueError(
                    "A clarification question is required."
                )
        # se c'è da chiarire la rotta ma l'oggetto non richeide di chiarire
        if (self.route is Route.REQUEST_CLARIFICATION
            and not self.clarification_required):
            raise ValueError(
                "Route.REQUEST_CLARIFICATION requires clarification."
            )
        # se viene richiesta un attuazione su un dispositivo ma la richiesta non è una richiesta del tipo operazionale
        if self.request_is_explicit_actuation and not self.request_is_operational:
            raise ValueError(
                "Explicit actuation must also be operational."
            )
        return self
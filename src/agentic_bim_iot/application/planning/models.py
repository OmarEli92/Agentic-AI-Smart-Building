from pydantic import BaseModel, ConfigDict, Field


class PlanningActionDraft(BaseModel):
    """The draft of the planning action"""
    model_config = ConfigDict(extra="forbid")
    measurement: str = Field(min_length=1)
    actuator_guid: str = Field(min_length=1)
    target_value: float
    reason: str = Field(min_length=1)


class PlanningDecisionDraft(BaseModel):
    """The draft that contains the decision to make"""
    model_config = ConfigDict(extra="forbid")
    actions: list[PlanningActionDraft]
    rationale: str = Field(min_length=1)
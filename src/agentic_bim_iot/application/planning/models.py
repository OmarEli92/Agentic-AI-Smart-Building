from pydantic import BaseModel, ConfigDict, Field


class PlanningActionDraft(BaseModel):
    """The draft of the planning action"""
    model_config = ConfigDict(extra="forbid")
    measurement: str 
    actuator_guid: str 
    target_value: float
    reason: str 


class PlanningDecisionDraft(BaseModel):
    """The draft that contains the decision to make"""
    model_config = ConfigDict(extra="forbid")
    actions: list[PlanningActionDraft]
    rationale: str 
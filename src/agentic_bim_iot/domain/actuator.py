from pydantic import BaseModel, ConfigDict, Field

class ActuatorReference(BaseModel):
    """The Actuator in the building"""
    model_config = ConfigDict(extra="forbid", frozen=True)
    room_reference: str = Field(min_length=1)
    controlled_measurement : str = Field(min_length=1)
    actuator_guid : str = Field(min_length=1)
    actuator_type : str = Field(min_length=1)

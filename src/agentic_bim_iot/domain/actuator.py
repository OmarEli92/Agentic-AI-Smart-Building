from pydantic import BaseModel, ConfigDict, Field

class ActuatorReference(BaseModel):
    """The Actuator in the building"""
    model_config = ConfigDict(frozen=True)
    room_reference: str 
    controlled_measurement : str 
    actuator_guid : str 
    actuator_type : str 

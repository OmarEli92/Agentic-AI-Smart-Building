from pydantic import BaseModel, ConfigDict, Field


class SensorReference(BaseModel):
    """Semantic reference to the physical sensor device associated with a room and a requested measurement."""
    model_config = ConfigDict(extra="forbid",frozen=True)
    room_reference: str 
    measurement: str 
    sensor_guid: str 
    
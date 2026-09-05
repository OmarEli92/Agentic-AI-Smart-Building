from pydantic import BaseModel, ConfigDict, Field


class IoTDeviceReference(BaseModel):
    """The IoT device base model , it is used for the mapping between the id used by the BIM
    and the id saved in the IoT platform"""
    model_config = ConfigDict(extra="forbid",frozen=True)
    semantic_sensor_guid: str = Field(min_length=1)
    platform_device_id: str = Field(min_length=1)
    platform_device_name: str = Field(min_length=1)
    

class IoTActuatorDeviceReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    semantic_actuator_guid: str = Field(min_length=1)
    platform_device_id: str = Field(min_length=1)
    platform_device_name: str = Field(min_length=1)
from pydantic import BaseModel, ConfigDict, Field


class IoTDeviceReference(BaseModel):
    """The IoT device base model , it is used for the mapping between the id used by the BIM
    and the id saved in the IoT platform"""
    model_config = ConfigDict(extra="forbid",frozen=True)
    semantic_sensor_guid: str 
    platform_device_id: str 
    platform_device_name: str 
    

class IoTActuatorDeviceReference(BaseModel):
    model_config = ConfigDict(frozen=True)
    semantic_actuator_guid: str 
    platform_device_id: str 
    platform_device_name: str 
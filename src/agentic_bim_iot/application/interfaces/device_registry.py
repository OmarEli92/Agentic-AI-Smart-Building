from typing import Protocol
from agentic_bim_iot.domain.iot import IoTDeviceReference
from agentic_bim_iot.domain.sensor import SensorReference


class DeviceRegistryError(RuntimeError):
    """The excpected error when resolving an IoT device"""
    

class DeviceRegistry(Protocol):
    """The interface used for resolving the IoT device if already provisioned"""
    def resolve(self, sensor: SensorReference) -> IoTDeviceReference:
        ...
        
class DeviceProvisioner(Protocol):
    """It ensures that an IoT device actually exists for a semantic sensor"""
    def ensure(self, sensor: SensorReference, *,label: str | None = None) -> IoTDeviceReference:
        ...
        
        
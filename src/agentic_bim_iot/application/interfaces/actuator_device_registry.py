from collections.abc import Sequence
from typing import Protocol

from agentic_bim_iot.domain.actuator import ActuatorReference
from agentic_bim_iot.domain.iot import IoTActuatorDeviceReference


class ActuatorDeviceRegistry(Protocol):
    """The contract for the actuator device registry"""

    def resolve(self, actuator: ActuatorReference) -> IoTActuatorDeviceReference:
        ...


class ActuatorDeviceProvisioner(Protocol):
    def ensure(self, actuator: ActuatorReference, *, label: str | None = None, controlled_measurements: Sequence[str] | None = None) -> IoTActuatorDeviceReference:
        ...
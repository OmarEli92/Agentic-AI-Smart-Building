from collections.abc import Sequence
from typing import Protocol
from agentic_bim_iot.domain.actuator import ActuatorReference

class ActuatorResolutionError(RuntimeError):
    ...
    
class ActuatorResolver(Protocol):
    """The actuator interface that resolve the actuator based on the room reference and the designated meausrement"""
    def resolve(self, room_reference: str, measurement: str) -> ActuatorReference:
        ...
        
    def resolve_many(self, room_reference: str, measurements: Sequence[str]) -> list[ActuatorReference]:
        ...
        
    
from collections.abc import Sequence
from typing import Protocol
from agentic_bim_iot.domain.sensor import SensorReference


class SensorResolutionError(RuntimeError):
    """Expected error when resolving a semantic sensor reference."""


class SensorResolver(Protocol):
    """Resolve the semantic sensor associated with a roomand a requested measurement, the bim contain the information of all the devices
    installed in any room"""

    def resolve(self, room_reference: str, measurement: str) -> SensorReference:
        ...

    def resolve_many(self, room_reference: str, measurements: Sequence[str]) -> list[SensorReference]:
        ...
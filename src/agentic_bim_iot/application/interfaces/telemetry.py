from typing import Protocol

from agentic_bim_iot.domain.sensor import SensorReference
from agentic_bim_iot.domain.telemetry import TelemetryReading


class TelemetryServiceError(RuntimeError):
    """Expected Error ehn retrieving operational telemetry."""


class TelemetryService(Protocol):
    """Read the telemetry from the IoT platform."""

    def read_latest(self,sensor: SensorReference) -> TelemetryReading:
        ...
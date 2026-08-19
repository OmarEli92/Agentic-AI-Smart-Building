from pydantic import BaseModel, ConfigDict, JsonValue
from agentic_bim_iot.domain.sensor import SensorReference


class TelemetryReading(BaseModel):
    """This class represent the telemetry value retrieved from ThingsBoard."""
    model_config = ConfigDict(extra="forbid",frozen=True)
    sensor: SensorReference
    thingsboard_device_id: str
    telemetry_key: str
    value: JsonValue
    timestamp_ms: int
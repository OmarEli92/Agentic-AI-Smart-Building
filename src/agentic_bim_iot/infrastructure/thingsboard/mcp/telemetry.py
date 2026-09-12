from agentic_bim_iot.application.interfaces.device_registry import DeviceRegistry, DeviceRegistryError
from agentic_bim_iot.application.interfaces.telemetry import TelemetryServiceError
from agentic_bim_iot.domain.sensor import SensorReference
from agentic_bim_iot.domain.telemetry import TelemetryReading
from agentic_bim_iot.infrastructure.observability.tracing import trace_observation
from agentic_bim_iot.infrastructure.thingsboard.mcp.client import ThingsBoardMCPClient, ThingsBoardMCPError
from agentic_bim_iot.infrastructure.thingsboard.mcp.response import extract_latest_telemetry
from agentic_bim_iot.infrastructure.thingsboard.telemetry_keys import measurement_to_telemetry_key


class ThingsBoardMCPTelemetryService:
    """This class is repsonsible for reading live telemetry"""

    def __init__(self, client: ThingsBoardMCPClient, device_registry: DeviceRegistry) -> None:
        self._client = client
        self._device_registry = device_registry

    def read_latest(self, sensor: SensorReference) -> TelemetryReading:
        """Read the latest telemetry of the selected sensor."""
        telemetry_key = measurement_to_telemetry_key(sensor.measurement)
        try:
            device = self._device_registry.resolve(sensor)
            print()
            print("=" * 70)
            print("THINGSBOARD MCP TELEMETRY LOOKUP")
            print("=" * 70)
            print(f"Room: {sensor.room_reference}")
            print(f"Measurement: {sensor.measurement}")
            print(f"Semantic GUID: {sensor.sensor_guid}")
            print(f"ThingsBoard ID: {device.platform_device_id}")
            print(f"Telemetry key: {telemetry_key}")

        except DeviceRegistryError as exc:
            raise TelemetryServiceError("No IoT device is mapped to the resolved BIM sensor.") from exc
        with trace_observation(
            "thingsboard.mcp.read_latest",
            as_type="tool",
            input_payload={
                "platform_device_id": device.platform_device_id,
                "semantic_sensor_guid": sensor.sensor_guid,
                "room_reference": sensor.room_reference,
                "measurement": sensor.measurement,
                "telemetry_key": telemetry_key
            }
        ) as observation:
            try:
                payload = self._client.call_tool("getLatestTimeseries",
                    {
                        "entityType": "DEVICE",
                        "entityIdStr": device.platform_device_id,
                        "keys": telemetry_key,
                        "useStrictDataTypes": "true",
                    },
                )
                value, timestamp_ms = extract_latest_telemetry(payload=payload,telemetry_key=telemetry_key)
                print(f"Latest telemetry: {payload}")
                print("=" * 70)
                print()

            except ThingsBoardMCPError as exc:
                print()
                print("=" * 70)
                print("THINGSBOARD MCP TELEMETRY ERROR")
                print("=" * 70)
                print(f"{type(exc).__name__}: {exc}")
                print("=" * 70)
                print()

                raise TelemetryServiceError(f"ThingsBoard MCP telemetry retrieval failed: {exc}") from exc
            reading = TelemetryReading(
                sensor=sensor,
                thingsboard_device_id=device.platform_device_id,
                telemetry_key=telemetry_key,
                value=value,
                timestamp_ms=timestamp_ms
            )
            observation.update(
                output={
                    "value": reading.value,
                    "timestamp_ms": reading.timestamp_ms
                }
            )

            return reading
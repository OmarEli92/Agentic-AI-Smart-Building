from tb_ce_client import ThingsboardClient
from tb_ce_client.exceptions import ApiException

from agentic_bim_iot.application.interfaces.device_registry import DeviceRegistry, DeviceRegistryError
from agentic_bim_iot.application.interfaces.telemetry import TelemetryServiceError
from agentic_bim_iot.domain.sensor import SensorReference
from agentic_bim_iot.domain.telemetry import TelemetryReading
from agentic_bim_iot.infrastructure.observability.tracing import trace_observation
from agentic_bim_iot.infrastructure.thingsboard.telemetry_keys import measurement_to_telemetry_key


class ThingsBoardTelemetryService:
    """TelemetryService adapter implementation of the IoT service, in our case ThingsBoard."""

    def __init__(self, client: ThingsboardClient, device_registry: DeviceRegistry):
        self._client = client
        self._device_registry = device_registry

    def read_latest(self, sensor: SensorReference) -> TelemetryReading:
        """Read the latest telemetry of the selected sensor."""
        telemetry_key = measurement_to_telemetry_key(sensor.measurement)
        try:
            device = self._device_registry.resolve(sensor)
            print()
            print("=" * 70)
            print("THINGSBOARD TELEMETRY LOOKUP")
            print("=" * 70)
            print(f"Room: {sensor.room_reference}")
            print(f"Measurement: {sensor.measurement}")
            print(f"Semantic GUID: {sensor.sensor_guid}")
            print(f"ThingsBoard ID: {device.platform_device_id}")
            print(f"Telemetry key: {telemetry_key}")

        except DeviceRegistryError as exc:
            raise TelemetryServiceError("No IoT device is mapped to the resolved BIM sensor.") from exc
        with trace_observation(
            "thingsboard.read_latest",
            as_type="tool",
            input_payload={
                "platform_device_id": device.platform_device_id,
                "semantic_sensor_guid": sensor.sensor_guid,
                "room_reference": sensor.room_reference,
                "measurement": sensor.measurement,
                "telemetry_key": telemetry_key,
            },
        ) as observation:
            try:
                latest = self._client.get_latest_timeseries(
                    entity_type="DEVICE",
                    entity_id=device.platform_device_id,
                    keys=telemetry_key,
                    use_strict_data_types=True,
                )

                print(f"Latest telemetry: {latest}")
                print("=" * 70)
                print()

            except ApiException as exc:
                raise TelemetryServiceError("ThingsBoard telemetry retrieval failed.") from exc
            values = latest.get(telemetry_key,[])
            if not values:
                raise TelemetryServiceError(f"No telemetry is available for the key '{telemetry_key}'.")
            latest_value = values[0]
            if latest_value.ts is None:
                raise TelemetryServiceError("ThingsBoard returned telemetry without a timestamp.")
            reading = TelemetryReading(
                sensor=sensor,
                thingsboard_device_id=device.platform_device_id,
                telemetry_key=telemetry_key,
                value=latest_value.value,
                timestamp_ms=latest_value.ts
            )

            observation.update(
                output={
                    "value": reading.value,
                    "timestamp_ms": reading.timestamp_ms
                }
            )
            return reading
from agentic_bim_iot.application.interfaces.device_registry import DeviceRegistryError
from agentic_bim_iot.domain.iot import IoTDeviceReference
from agentic_bim_iot.domain.sensor import SensorReference
from agentic_bim_iot.infrastracture.observability.tracing import trace_observation
from agentic_bim_iot.infrastracture.thingsboard.mcp.client import ThingsBoardMCPClient, ThingsBoardMCPError
from agentic_bim_iot.infrastracture.thingsboard.mcp.response import extract_device


class ThingsBoardMCPDeviceRegistry:
    """This class is responsible for resolving the devices"""

    def __init__(self, client: ThingsBoardMCPClient) -> None:
        self._client = client

    def resolve(self, sensor: SensorReference) -> IoTDeviceReference:
        with trace_observation(
            "thingsboard.mcp.resolve_sensor_device",
            as_type="tool",
            input_payload={
                "sensor_guid": sensor.sensor_guid,
                "room_reference": sensor.room_reference,
                "measurement": sensor.measurement,
            },
        ) as observation:
            try:
                payload = self._client.call_tool(
                    "getTenantDevice",
                    {
                        "deviceName": sensor.sensor_guid,
                    },
                )
                device_id, device_name = extract_device(payload=payload, expected_name=sensor.sensor_guid)
            except ThingsBoardMCPError as exc:
                raise DeviceRegistryError(f"No ThingsBoard device is found for the semantic sensor ID: {sensor.sensor_guid}") from exc

            reference = IoTDeviceReference(semantic_sensor_guid=sensor.sensor_guid, platform_device_id=device_id, platform_device_name=device_name)

            observation.update(
                output={
                    "platform_device_id": reference.platform_device_id,
                    "platform_device_name": reference.platform_device_name,
                }
            )

            return reference
from agentic_bim_iot.application.interfaces.device_registry import DeviceRegistryError
from agentic_bim_iot.domain.actuator import ActuatorReference
from agentic_bim_iot.domain.iot import IoTActuatorDeviceReference
from agentic_bim_iot.infrastructure.observability.tracing import trace_observation
from agentic_bim_iot.infrastructure.thingsboard.mcp.client import ThingsBoardMCPClient,ThingsBoardMCPError
from agentic_bim_iot.infrastructure.thingsboard.mcp.response import extract_device


class ThingsBoardMCPActuatorDeviceRegistry:
    """This class is reposible for resolving semantic actuator references"""

    def __init__(self, client: ThingsBoardMCPClient) -> None:
        self._client = client

    def resolve(self, actuator: ActuatorReference,) -> IoTActuatorDeviceReference:
        with trace_observation(
            "thingsboard.mcp.resolve_actuator_device",
            as_type="tool",
            input_payload={
                "actuator_guid": actuator.actuator_guid,
                "room_reference": actuator.room_reference,
                "measurement": actuator.controlled_measurement,
                "actuator_type": actuator.actuator_type,
            },
        ) as observation:

            try:
                payload = self._client.call_tool("getTenantDevice",{"deviceName": actuator.actuator_guid})
                device_id, device_name = extract_device(payload=payload, expected_name=actuator.actuator_guid,)
            except ThingsBoardMCPError as exc:
                raise DeviceRegistryError(f"No ThingsBoard device is found for the semantic actuator ID: {actuator.actuator_guid}") from exc

            reference = IoTActuatorDeviceReference(semantic_actuator_guid=actuator.actuator_guid, platform_device_id=device_id, platform_device_name=device_name)
            observation.update(
                output={
                    "platform_device_id": reference.platform_device_id,
                    "platform_device_name": reference.platform_device_name,
                }
            )
            return reference
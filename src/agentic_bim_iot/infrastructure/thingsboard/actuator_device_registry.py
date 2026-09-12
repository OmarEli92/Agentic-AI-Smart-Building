import json
from collections.abc import Sequence
from tb_ce_client import ThingsboardClient
from tb_ce_client.exceptions import ApiException, NotFoundException
from tb_ce_client.models import Device
from agentic_bim_iot.application.interfaces.device_registry import DeviceRegistryError
from agentic_bim_iot.domain.actuator import ActuatorReference
from agentic_bim_iot.domain.iot import IoTActuatorDeviceReference
from agentic_bim_iot.infrastructure.observability.tracing import trace_observation


class ThingsBoardActuatorDeviceRegistry:
    """The resolver that associates the GUID in the ontology with the id on ThingsBoard.
    For the sake of this implementation, the GUID corresponds to the name of the device on ThingsBoard.
    """

    def __init__(self, client: ThingsboardClient) -> None:
        self._client = client

    def resolve(self, actuator: ActuatorReference) -> IoTActuatorDeviceReference:
        with trace_observation(
            "thingsboard.resolve_actuator_device",
            as_type="tool",
            input_payload={
                "actuator_guid": actuator.actuator_guid,
                "room_reference": actuator.room_reference,
                "measurement": actuator.controlled_measurement,
                "actuator_type": actuator.actuator_type,
            }
        ) as observation:
            try:
                device = self._client.get_tenant_device_by_name(device_name=actuator.actuator_guid)
            except NotFoundException as exc:
                raise DeviceRegistryError(f"No ThingsBoard device is found for the semantic actuator ID: {actuator.actuator_guid}") from exc
            except ApiException as exc:
                raise DeviceRegistryError(
                    "ThingsBoard actuator device lookup failed."
                ) from exc

            reference = self._to_reference(actuator=actuator, device=device)
            observation.update(
                output={
                    "platform_device_id": reference.platform_device_id,
                    "platform_device_name": reference.platform_device_name,
                }
            )
            return reference

    def ensure(self, actuator: ActuatorReference, *, label: str | None = None, controlled_measurements: Sequence[str] | None = None) -> IoTActuatorDeviceReference:
        try:
            device = self._client.get_tenant_device_by_name(device_name=actuator.actuator_guid)
            changed = False
            if label is not None and device.label != label:
                device.label = label
                changed = True
            if device.type != actuator.actuator_type:
                device.type = actuator.actuator_type
                changed = True
            if changed:
                device = self._client.save_device(device)

        except NotFoundException:
            try:
                device = self._client.save_device(Device(name=actuator.actuator_guid, label=label, type=actuator.actuator_type))
            except ApiException as exc:
                raise DeviceRegistryError("Could not create the ThingsBoard actuator device.") from exc

        except ApiException as exc:
            raise DeviceRegistryError("ThingsBoard actuator device lookup failed.") from exc

        reference = self._to_reference(actuator=actuator, device=device)
        measurements = controlled_measurements or (actuator.controlled_measurement)
        attributes = {
            "semanticGuid": actuator.actuator_guid,
            "roomReference": actuator.room_reference,
            "actuatorType": actuator.actuator_type,
            "controlledMeasurements": list(measurements)
        }

        try:
            self._client.save_entity_attributes_v2(
                entity_type="DEVICE",
                entity_id=reference.platform_device_id,
                scope="SERVER_SCOPE",
                body=json.dumps(attributes)
            )
        except ApiException as exc:
            raise DeviceRegistryError("Could not save the ThingsBoard actuator attributes.") from exc
        return reference

    @staticmethod
    def _to_reference(*, actuator: ActuatorReference, device) -> IoTActuatorDeviceReference:
        if device.id is None:
            raise DeviceRegistryError("ThingsBoard returned an actuator device without an ID.")
        return IoTActuatorDeviceReference(
            semantic_actuator_guid=actuator.actuator_guid,
            platform_device_id=device.id.get_id(),
            platform_device_name=device.name
        )
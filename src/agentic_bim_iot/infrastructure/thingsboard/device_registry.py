from tb_ce_client import ThingsboardClient
from tb_ce_client.exceptions import ApiException,NotFoundException
from tb_ce_client.models import Device
from agentic_bim_iot.application.interfaces.device_registry import DeviceRegistryError
from agentic_bim_iot.domain.iot import IoTDeviceReference
from agentic_bim_iot.domain.sensor import SensorReference
from agentic_bim_iot.infrastructure.observability.tracing import trace_observation


class ThingsBoardDeviceRegistry:
    """ The Thingsboard implementation of the semantic to IoT device mapping.
    In this first implementation we based on the OSH dataset, so the BIM sensor GUID is 
    also the Thingsboard device name."""
    
    def __init__(self, client: ThingsboardClient):
        self._client = client

    def resolve(self, sensor: SensorReference) -> IoTDeviceReference:
        with trace_observation(
            "thingsboard.resolve_sensor_device",
            as_type="tool",
            input_payload={
                "sensor_guid": sensor.sensor_guid,
                "room_reference": sensor.room_reference,
                "measurement": sensor.measurement,
            },
        ) as observation:
            try:
                device = self._client.get_tenant_device_by_name(device_name=sensor.sensor_guid)
            except NotFoundException as exc:
                raise DeviceRegistryError(f"No Thingsboard device is found for the semantic sensor ID:{sensor.sensor_guid}") from exc
            except ApiException as exc:
                raise DeviceRegistryError("Thingboard device lookup failed") from exc
            reference = self._to_reference(sensor=sensor, device=device)
            observation.update(
                output={
                    "platform_device_id": reference.platform_device_id,
                    "platform_device_name": reference.platform_device_name,
                }
            )
            return reference

    def ensure(self, sensor: SensorReference, label: str | None = None) -> IoTDeviceReference:
        try:
            device = self._client.get_tenant_device_by_name(device_name=sensor.sensor_guid)
            if label is not None and device.label != label:
                device.label = label
                device = self._client.save_device(device)

        except NotFoundException:
            try:
                device = self._client.save_device(Device(name=sensor.sensor_guid, label=label))
            except ApiException as exc:
                raise DeviceRegistryError("Could not find the ThingsBoard device.") from exc
        except ApiException as exc:
            raise DeviceRegistryError("ThingsBoard device lookup failed.") from exc
        return self._to_reference(sensor=sensor, device=device)

    @staticmethod
    def _to_reference(*, sensor: SensorReference, device) -> IoTDeviceReference:
        if device.id is None:
            raise DeviceRegistryError("ThingsBoard returned a device without an ID.")
        return IoTDeviceReference(
            semantic_sensor_guid=sensor.sensor_guid,
            platform_device_id=device.id.get_id(),
            platform_device_name=device.name,
        )
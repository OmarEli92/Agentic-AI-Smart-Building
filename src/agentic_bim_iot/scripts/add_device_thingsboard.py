import json
from contextlib import ExitStack

from tb_ce_client.exceptions import NotFoundException
from tb_ce_client.models import Device

from agentic_bim_iot.config.settings import get_settings
from agentic_bim_iot.infrastracture.llm.factory import create_chat_model
from agentic_bim_iot.infrastracture.semantic.factory import (
    create_semantic_services,
)
from agentic_bim_iot.infrastracture.thingsboard.factory import (
    create_thingsboard_client,
)


def main() -> None:
    settings = get_settings()

    with ExitStack() as resources:
        chat_model = create_chat_model(settings)

        semantic_services = create_semantic_services(
            settings=settings,
            chat_model=chat_model,
            resources=resources,
        )

        sensor = semantic_services.sensor_resolver.resolve(
            room_reference="Kitchen",
            measurement="temperature",
        )

        print(f"Resolved sensor GUID: {sensor.sensor_guid}")

        client = create_thingsboard_client(
            settings=settings,
            resources=resources,
        )

        try:
            device = client.get_tenant_device_by_name(
                device_name=sensor.sensor_guid
            )

            print("ThingsBoard device already exists.")

        except NotFoundException:
            device = client.save_device(
                Device(
                    name=sensor.sensor_guid,
                    type="MultiSensor",
                )
            )

            print("ThingsBoard device created.")

        device_id = device.id.get_id()

        client.save_entity_telemetry(
            entity_type="DEVICE",
            entity_id=device_id,
            scope="ANY",
            body=json.dumps(
                {
                    "temperature": 22.4,
                }
            ),
        )

        print("Telemetry written.")

        latest = client.get_latest_timeseries(
            entity_type="DEVICE",
            entity_id=device_id,
            keys="temperature",
            use_strict_data_types=True,
        )

        print(f"Latest telemetry: {latest}")


if __name__ == "__main__":
    main()
import json
from collections import defaultdict
from contextlib import ExitStack
from csv import DictReader
from pathlib import Path

from tb_ce_client.exceptions import ApiException

from agentic_bim_iot.config.settings import get_settings
from agentic_bim_iot.domain.sensor import SensorReference
from agentic_bim_iot.infrastructure.thingsboard.device_registry import ThingsBoardDeviceRegistry
from agentic_bim_iot.infrastructure.thingsboard.factory import create_thingsboard_client
from agentic_bim_iot.infrastructure.thingsboard.telemetry_keys import measurement_to_telemetry_key


SRC_DIR = Path(__file__).resolve().parents[3]
DATASET_DIR = SRC_DIR / "resources" / "telemetry" / "OSH_Measurements"

SENSOR_GUID_BY_ROOM = {
    "Kitchen": "b3ca6858-e675-4f4a-bca7-863846825601",
    "Bathroom": "b3ca6858-e675-4f4a-bca7-86384682547a",
    "Dining": "b3ca6858-e675-4f4a-bca7-86384683a0fc",
    "Bedroom": "b3ca6858-e675-4f4a-bca7-86384682559d",
    "Living": "b3ca6858-e675-4f4a-bca7-863846825941",
    "Toilet": "b3ca6858-e675-4f4a-bca7-8638468254e5",
    "Outdoor": "b3ca6858-e675-4f4a-bca7-863484682547",
}

BATCH_SIZE = 1000


def main() -> None:
    settings = get_settings()

    if not DATASET_DIR.is_dir():
        raise RuntimeError(f"Dataset directory not found: {DATASET_DIR}")

    csv_paths = sorted(DATASET_DIR.glob("*.csv"))
    if not csv_paths:
        raise RuntimeError(f"No CSV files found in: {DATASET_DIR}")

    print()
    print("=" * 70)
    print("OPEN SMART HOME -> THINGSBOARD")
    print("=" * 70)
    print(f"Dataset directory: {DATASET_DIR}")
    print(f"CSV files found: {len(csv_paths)}")
    print()

    with ExitStack() as resources:
        thingsboard_client = create_thingsboard_client(settings=settings, resources=resources)
        device_registry = ThingsBoardDeviceRegistry(client=thingsboard_client)
        current_snapshot = defaultdict(dict)
        device_names = {}
        total_samples = 0
        for path in csv_paths:
            room, measurement = parse_filename(path)
            if room not in SENSOR_GUID_BY_ROOM:
                print(f"Skipping {path.name}: no GUID configured for room '{room}'.")
                continue
            sensor_guid = SENSOR_GUID_BY_ROOM[room]
            telemetry_key = measurement_to_telemetry_key(measurement)
            print()
            print("-" * 70)
            print(f"File: {path.name}")
            print(f"Room: {room}")
            print(f"Measurement: {telemetry_key}")
            print(f"Sensor GUID: {sensor_guid}")
            sensor = SensorReference(room_reference=room,measurement=telemetry_key,sensor_guid=sensor_guid)
            device = device_registry.ensure(sensor, label=build_device_label(room))
            print(f"ThingsBoard ID: {device.platform_device_id}")
            samples = read_csv(path)
            if not samples:
                print("No valid samples found.")
                continue
            print(f"Samples: {len(samples)}")
            upload_historical_samples(
                client=thingsboard_client,
                device_id=device.platform_device_id,
                telemetry_key=telemetry_key,
                samples=samples,
            )
            total_samples += len(samples)
            latest_timestamp, latest_value = max(samples, key=lambda sample: sample[0])
            current_snapshot[device.platform_device_id][telemetry_key] = latest_value
            device_names[device.platform_device_id] = device.platform_device_name
            print(f"Historical upload completed for {room} / {telemetry_key}")
            print(f"Latest dataset sample: {latest_value} (original timestamp={latest_timestamp})")
        print()
        print("=" * 70)
        print("PUBLISHING CURRENT SNAPSHOT")
        print("=" * 70)
        publish_current_snapshot(
            client=thingsboard_client,
            snapshots=current_snapshot,
            device_names=device_names,
        )
    print()
    print("=" * 70)
    print("IMPORT COMPLETED")
    print("=" * 70)
    print(f"Historical samples uploaded: {total_samples}")
    print(f"ThingsBoard devices updated: {len(current_snapshot)}")
    print("=" * 70)


def parse_filename(path: Path) -> tuple[str, str]:
    stem = path.stem
    if stem == "OSH_OutdoorTemperature":
        return "Outdoor", "temperature"
    parts = stem.rsplit("_", 1)
    if len(parts) != 2:
        raise RuntimeError(f"Unsupported dataset filename: {path.name}")
    room = parts[0].strip()
    measurement = parts[1].strip().casefold()
    return room, measurement


def read_csv(path: Path) -> list[tuple[int, float]]:
    samples = []
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = DictReader(file, delimiter="\t", fieldnames=["time", "value"])
        for row in reader:
            try:
                timestamp_seconds = int(row["time"])
                value = float(row["value"])
            except (TypeError, ValueError):
                continue
            timestamp_ms = timestamp_seconds * 1000
            samples.append((timestamp_ms, value))
    return samples


def upload_historical_samples(*,client,device_id: str,telemetry_key: str,samples: list[tuple[int, float]]) -> None:
    for start in range(0, len(samples), BATCH_SIZE):
        batch = samples[start:start + BATCH_SIZE]

        payload = [
            {"ts": timestamp_ms, "values": {telemetry_key: value}}
            for timestamp_ms, value in batch
        ]

        try:
            client.save_entity_telemetry(
                entity_type="DEVICE",
                entity_id=device_id,
                scope="ANY",
                body=json.dumps(payload),
            )
        except ApiException as exc:
            raise RuntimeError(
                f"Could not upload telemetry '{telemetry_key}' to ThingsBoard device '{device_id}'."
            ) from exc


def publish_current_snapshot(*,client,snapshots: dict,device_names: dict[str, str]) -> None:
    for device_id, values in snapshots.items():
        try:
            client.save_entity_telemetry(
                entity_type="DEVICE",
                entity_id=device_id,
                scope="ANY",
                body=json.dumps(values),
            )
        except ApiException as exc:
            raise RuntimeError(
                f"Could not publish current telemetry to ThingsBoard device '{device_id}'."
            ) from exc

        print(f"{device_names[device_id]} -> {values}")


def build_device_label(room: str) -> str:
    if room == "Outdoor":
        return "Outdoor Sensor"
    return f"{room} MultiSensor"


if __name__ == "__main__":
    main()
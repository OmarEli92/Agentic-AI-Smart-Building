from collections.abc import Sequence
from agentic_bim_iot.domain.actuator import ActuatorReference
from agentic_bim_iot.infrastracture.semantic.graphdb.graph_store import SPARQLResult


def _normalize_measurements(measurements: Sequence[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for measurement in measurements:
        value = measurement.strip().casefold()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return tuple(normalized)


def _extract_references(records: SPARQLResult, *, room: str, requested_measurements: Sequence[str]) -> list[ActuatorReference]:
    requested = set(requested_measurements)
    references: dict[tuple[str, str, str], ActuatorReference] = {}
    for record in records:
        if "measurement" not in record or "actuatorGuid" not in record or "actuatorType" not in record:
            continue
        measurement = str(record["measurement"]).strip().casefold()
        actuator_guid = str(record["actuatorGuid"]).strip()
        actuator_type = _local_name(str(record["actuatorType"]).strip())
        if measurement not in requested or not actuator_guid or not actuator_type:
            continue
        reference = ActuatorReference(room_reference=room, controlled_measurement=measurement, actuator_guid=actuator_guid, actuator_type=actuator_type)
        references[(measurement, actuator_guid, actuator_type)] = reference
    return list(references.values())


def _local_name(value: str) -> str:
    if "#" in value:
        return value.rsplit("#", 1)[1]
    if "/" in value:
        return value.rstrip("/").rsplit("/", 1)[1]
    return value
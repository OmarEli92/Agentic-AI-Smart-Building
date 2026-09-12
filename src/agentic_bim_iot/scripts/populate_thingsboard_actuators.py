from collections import defaultdict, deque
from contextlib import ExitStack
from pathlib import Path
from rdflib import Graph, Namespace, RDF, RDFS, URIRef
from agentic_bim_iot.config.settings import get_settings
from agentic_bim_iot.domain.actuator import ActuatorReference
from agentic_bim_iot.infrastructure.semantic.actuator.profile import BOP_ACTUATOR_ONTOLOGY_PROFILE
from agentic_bim_iot.infrastructure.thingsboard.actuator_device_registry import ThingsBoardActuatorDeviceRegistry
from agentic_bim_iot.infrastructure.thingsboard.factory import create_thingsboard_client


BOP = Namespace("https://w3id.org/bop#")
BOT = Namespace("https://w3id.org/bot#")
PROPS = Namespace("https://w3id.org/props#")


def main() :
    settings = get_settings()
    ontology_path = Path(settings.graphdb_ontology_path)
    if not ontology_path.is_absolute():
        ontology_path = (Path.cwd() / ontology_path)
    if not ontology_path.is_file():
        raise RuntimeError(f"Ontology file not found: {ontology_path}")
    graph = Graph()
    graph.parse(ontology_path, format="turtle")
    actuators = discover_actuators(graph)
    if not actuators:
        raise RuntimeError("No supported actuators were found in the ontology.")
    grouped = defaultdict(list)
    for actuator in actuators:
        grouped[actuator.actuator_guid].append(actuator)

    print()
    print("=" * 70)
    print("ONTOLOGY ACTUATORS -> THINGSBOARD")
    print("=" * 70)
    print(f"Ontology: {ontology_path}")
    print(f"Actuator devices found: {len(grouped)}")

    with ExitStack() as resources:
        client = create_thingsboard_client(settings=settings, resources=resources)
        registry = ThingsBoardActuatorDeviceRegistry(client=client)
        for actuator_guid, references in sorted(grouped.items()):
            reference = references[0]
            measurements = tuple(sorted({item.controlled_measurement for item in references}))
            device = registry.ensure(reference, label=build_device_label(reference), controlled_measurements=measurements)
            print()
            print("-" * 70)
            print(f"Room: {reference.room_reference}")
            print(f"Actuator type: {reference.actuator_type}")
            print(f"Semantic GUID: {actuator_guid}")
            print(f"Controlled measurements: {', '.join(measurements)}")
            print(f"ThingsBoard ID: {device.platform_device_id}")

    print()
    print("=" * 70)
    print("ACTUATOR PROVISIONING COMPLETED")
    print("=" * 70)


def discover_actuators(graph: Graph) -> list[ActuatorReference]:
    measurement_by_type = {URIRef(quantity_type): measurement for measurement, quantity_type in (BOP_ACTUATOR_ONTOLOGY_PROFILE.measurement_types.items())}
    references: dict[tuple[str, str, str, str], ActuatorReference] = {}
    actuator_nodes = {actuator for actuator, actuator_type in graph.subject_objects(RDF.type) if actuator_type == BOP.Actuator or is_subclass_of(graph, actuator_type, BOP.Actuator)}
    for actuator in actuator_nodes:
        actuator_guid = first_string(graph.objects(actuator, BOT.hasGuid))
        if not actuator_guid:
            continue
        room = next(
            graph.objects(actuator, BOP.actsOnRoom), None)
        if room is None:
            continue
        room_reference = first_string(
            graph.objects(room, PROPS.longNameIfcSpatialStructureElement_attribute_simple))
        if not room_reference:
            room_reference = local_name(str(room))
        actuator_type = resolve_actuator_type(graph, actuator)
        if not actuator_type:
            continue
        for quantity in graph.objects( actuator, BOP.actsOn):
            for quantity_type in graph.objects(quantity, RDF.type):
                measurement = measurement_by_type.get(URIRef(quantity_type))
                if measurement is None:
                    continue
                reference = ActuatorReference(room_reference=room_reference, controlled_measurement=measurement, actuator_guid=actuator_guid, actuator_type=actuator_type)
                references[(room_reference.casefold(), measurement, actuator_guid, actuator_type)] = reference

    return list(references.values())


def resolve_actuator_type(graph: Graph, actuator) -> str | None:
    candidates = []
    for actuator_type in graph.objects(actuator, RDF.type):
        if actuator_type == BOP.Actuator:
            continue
        if is_subclass_of(graph, actuator_type, BOP.Actuator):
            candidates.append(local_name(str(actuator_type)))

    if not candidates:
        return None
    return sorted(candidates)[0]


def is_subclass_of(graph: Graph, candidate, parent) -> bool:
    queue = deque([candidate])
    visited = set()
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        for superclass in graph.objects(current, RDFS.subClassOf):
            if superclass == parent:
                return True
            queue.append(superclass)
    return False


def first_string(values) -> str | None:
    for value in values:
        normalized = str(value).strip()
        if normalized:
            return normalized
    return None

def local_name(value: str) -> str:
    if "#" in value:
        return value.rsplit("#", 1)[1]
    if "/" in value:
        return (value.rstrip("/").rsplit("/", 1)[1])
    return value


def build_device_label(actuator: ActuatorReference) -> str:
    return (f"{actuator.room_reference} {actuator.actuator_type}")


if __name__ == "__main__":
    main()
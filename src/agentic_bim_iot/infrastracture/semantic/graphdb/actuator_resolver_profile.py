from collections.abc import Sequence
from agentic_bim_iot.application.interfaces.actuator import ActuatorResolutionError
from agentic_bim_iot.domain.actuator import ActuatorReference
from agentic_bim_iot.infrastracture.semantic.actuator.profile import ActuatorOntologyProfile
from agentic_bim_iot.infrastracture.semantic.graphdb.graph_store import GraphStoreError, SPARQLGraphStore
from agentic_bim_iot.infrastracture.semantic.graphdb.query_validation import InvalidSPARQLQuery, validate_select_query
from agentic_bim_iot.utility import _extract_references, _normalize_measurements


class GraphDBOntologyProfileActuatorResolver:
    """The implementation for the Ontology Profile actuator resolver which doesn't leveragae the LLM """
    def __init__(self, graph_store: SPARQLGraphStore, profile: ActuatorOntologyProfile) -> None:
        self._graph_store = graph_store
        self._profile = profile

    def resolve(self, room_reference: str, measurement: str) -> ActuatorReference:
        references = self.resolve_many(room_reference, [measurement])
        if not references:
            raise ActuatorResolutionError("No actuator was found for the requested room and measurement.")
        if len(references) > 1:
            raise ActuatorResolutionError("Multiple actuators were found for the requested room and measurement.")
        return references[0]

    def resolve_many(self, room_reference: str, measurements: Sequence[str]) -> list[ActuatorReference]:
        room = room_reference.strip()
        requested_measurements = _normalize_measurements(measurements)
        if not room:
            raise ActuatorResolutionError("Room is required to resolve actuators.")
        if not requested_measurements:
            return []
        unsupported = [measurement for measurement in requested_measurements if measurement not in self._profile.measurement_types]
        if unsupported:
            raise ActuatorResolutionError(f"The configured ontology profile does not support these measurements: {', '.join(unsupported)}.")
        generated_query = self._build_query(room=room, measurements=requested_measurements)
        try:
            validated_query = validate_select_query(generated_query)
            records = self._graph_store.execute_select(validated_query)
        except (GraphStoreError, InvalidSPARQLQuery) as exc:
            raise ActuatorResolutionError("The GraphDB ontology-profile actuator resolution failed.") from exc
        return _extract_references(records, room=room, requested_measurements=requested_measurements)

    def _build_query(self, *, room: str, measurements: Sequence[str]) -> str:
        values = "\n".join(f'    ("{self._escape_sparql_string(measurement)}" <{self._profile.measurement_types[measurement]}>)' for measurement in measurements)
        escaped_room = self._escape_sparql_string(room.casefold())
        return f"""
SELECT DISTINCT ?measurement ?actuatorGuid ?actuatorType
WHERE {{
  VALUES (?measurement ?quantityType) {{
{values}
  }}
  ?room <{self._profile.room_name_property}> ?roomName .
  FILTER(CONTAINS(LCASE(STR(?roomName)), "{escaped_room}")) .
  ?actuator <{self._profile.acts_on_room_property}> ?room .
  ?actuator <{self._profile.acts_on_property}> ?quantity .
  ?actuator <{self._profile.guid_property}> ?actuatorGuid .
  ?actuator a ?actuatorType .
  ?actuatorType <{self._profile.subclass_property}>* <{self._profile.actuator_root_class}> .
  FILTER(?actuatorType != <{self._profile.actuator_root_class}>) .
  ?quantity a ?quantityType .
}}
""".strip()

    @staticmethod
    def _escape_sparql_string(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
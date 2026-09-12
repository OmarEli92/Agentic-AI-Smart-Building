from collections.abc import Sequence

from langchain_core.language_models.chat_models import BaseChatModel

from agentic_bim_iot.application.interfaces.sensor import SensorResolutionError
from agentic_bim_iot.domain.sensor import SensorReference
from agentic_bim_iot.infrastructure.semantic.graphdb.graph_store import GraphStoreError, SPARQLGraphStore, SPARQLResult
from agentic_bim_iot.infrastructure.semantic.graphdb.query_pipeline import GraphDBQueryPipeline
from agentic_bim_iot.infrastructure.semantic.graphdb.query_validation import InvalidSPARQLQuery
from agentic_bim_iot.infrastructure.semantic.prompts.graphdb_sensor import SPARQL_SENSOR_PROMPT


class GraphDBSensorResolver:
    """ Resolve sensor GUIDs through the existing Text to SPARQL sensor component of the
    previous implementation of the system but with an extra 'repairing' prompt to mitigate the problem of semanthically correct queries
    but out of scopew.
    """

    def __init__(self, chat_model: BaseChatModel, graph_store: SPARQLGraphStore, max_repair_retries: int = 2):
        self._graph_store = graph_store
        self._max_repair_retries = max_repair_retries
        self._query_pipeline = GraphDBQueryPipeline(chat_model=chat_model, graph_store=graph_store, generation_prompt=SPARQL_SENSOR_PROMPT,
                                                    max_repair_retries=max_repair_retries, component="sensor_text_to_sparql",)

    def resolve(self, room_reference: str, measurement: str) -> SensorReference:
        """Resolve the sensor GUID"""
        room = room_reference.strip()
        requested_measurement = measurement.strip().casefold()
        if not room or not requested_measurement:
            raise SensorResolutionError("Room and measurement are required to resolve a sensor.")
        #we rebuild the question base d on the room reference and the measurement
        question = f"What is the {requested_measurement} in the {room}?"
        sensor_guid = self._resolve_sensor_guid(question)
        return SensorReference(room_reference=room, measurement=requested_measurement, sensor_guid=sensor_guid)

    def resolve_many(self, room_reference: str, measurements: Sequence[str]) -> list[SensorReference]:
        room = room_reference.strip()
        requested_measurements = self._normalize_measurements(measurements)
        if not room:
            raise SensorResolutionError("Room is required to resolve sensors.")
        if not requested_measurements:
            return []
        question = f"What's the comfort in the {room}?"
        sensor_guid = self._resolve_sensor_guid(question)
        return [SensorReference(room_reference=room, measurement=measurement, sensor_guid=sensor_guid) for measurement in requested_measurements]

    def _resolve_sensor_guid(self, question: str) -> str:
        try:
            records = self._query_pipeline.execute_once(question)
        except (GraphStoreError, InvalidSPARQLQuery) as exc:
            raise SensorResolutionError("The GraphDB sensor resolution pipeline failed.") from exc

        return self._extract_sensor_guid(records)

    @staticmethod
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

    @staticmethod
    def _extract_sensor_guid(records: SPARQLResult) -> str:
        sensor_guids = {
            str(record["sensorGuid"])
            for record in records
            if "sensorGuid" in record and record["sensorGuid"] is not None
        }
        if not sensor_guids:
            raise SensorResolutionError("No sensor was found for the requested room.")
        if len(sensor_guids) > 1:
            raise SensorResolutionError("The semantic backend returned multiple sensor GUIDs for the requested room.")
        return next(iter(sensor_guids))
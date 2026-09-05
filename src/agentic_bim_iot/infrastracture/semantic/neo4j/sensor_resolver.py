from collections.abc import Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from neo4j import Driver
from neo4j.exceptions import DriverError, Neo4jError
from neo4j_graphrag.exceptions import Neo4jGraphRagError
from neo4j_graphrag.retrievers import Text2CypherRetriever
from neo4j_graphrag.schema import get_schema

from agentic_bim_iot.application.interfaces.sensor import SensorResolutionError
from agentic_bim_iot.domain.sensor import SensorReference
from agentic_bim_iot.infrastracture.semantic.prompts.neo4j_sensor import CYPHER_SENSOR_PROMPT_TEXT


class Neo4jSensorResolver:
    """Resolve room MultiSensor GUIDs through the Neo4j Text-to-Cypher pipeline."""

    def __init__(self, chat_model: BaseChatModel, driver: Driver, database: str = "neo4j", max_repair_retries: int = 2) -> None:
        self._driver = driver
        self._database = database
        self._max_repair_retries = max_repair_retries

        try:
            schema = get_schema(driver=driver, database=database)
            self._retriever = Text2CypherRetriever(driver=driver, llm=chat_model, neo4j_schema=schema,
                                                   custom_prompt=CYPHER_SENSOR_PROMPT_TEXT, neo4j_database=database)
        except (Neo4jGraphRagError, Neo4jError, DriverError) as exc:
            raise SensorResolutionError("Could not initialize the Neo4j sensor resolver.") from exc

    def resolve(self, room_reference: str, measurement: str) -> SensorReference:
        """Resolve one measurement to the main MultiSensor GUID of the room."""
        room = room_reference.strip()
        requested_measurement = measurement.strip().casefold()

        if not room or not requested_measurement:
            raise SensorResolutionError("Room and measurement are required to resolve a sensor.")

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

        return [
            SensorReference(room_reference=room, measurement=measurement, sensor_guid=sensor_guid)
            for measurement in requested_measurements
        ]

    def _resolve_sensor_guid(self, question: str) -> str:
        try:
            result = self._retriever.get_search_results(query_text=question)
            self._print_attempt(cypher=result.metadata.get("cypher"), records=result.records)
        except (Neo4jGraphRagError, Neo4jError, DriverError) as exc:
            raise SensorResolutionError("The Neo4j sensor resolution pipeline failed.") from exc

        return self._extract_sensor_guid(result.records)

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
    def _extract_sensor_guid(records) -> str:
        sensor_guids: set[str] = set()

        for record in records:
            if "sensorGuid" not in record.keys():
                continue

            value = record["sensorGuid"]

            if value is not None:
                sensor_guids.add(str(value))

        if not sensor_guids:
            raise SensorResolutionError("No sensor was found for the requested room.")

        if len(sensor_guids) > 1:
            raise SensorResolutionError("The semantic backend returned multiple sensor GUIDs for the requested room.")

        return next(iter(sensor_guids))

    @staticmethod
    def _print_attempt(*, cypher: str | None, records) -> None:
        print()
        print("=" * 70)
        print("NEO4J SENSOR RESOLUTION")
        print("=" * 70)
        print("\nCYPHER:")
        print(cypher)
        print("\nNEO4J RECORDS:")
        print(records)
        print(f"\nNUMBER OF RECORDS: {len(records)}")
        print("=" * 70)
        print()
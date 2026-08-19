from langchain_core.language_models.chat_models import BaseChatModel
from neo4j import Driver
from neo4j.exceptions import DriverError, Neo4jError
from neo4j_graphrag.exceptions import Neo4jGraphRagError
from neo4j_graphrag.retrievers import Text2CypherRetriever
from neo4j_graphrag.schema import get_schema
from agentic_bim_iot.application.interfaces.sensor import SensorResolutionError
from agentic_bim_iot.domain.sensor import SensorReference
from agentic_bim_iot.infrastracture.semantic.prompts.neo4j_execution_repair import CYPHER_SENSOR_EXECUTION_REPAIR_PROMPT_TEXT
from agentic_bim_iot.infrastracture.semantic.prompts.neo4j_sensor import CYPHER_SENSOR_PROMPT_TEXT


class Neo4jSensorResolver:
    """
    Resolve sensor GUIDs using Neo4j's Text2CypherRetriever
    and the existing sensor Cypher prompt.
    """

    def __init__(self,chat_model: BaseChatModel,driver: Driver,database: str = "neo4j") -> None:
        try:
            schema = get_schema(driver=driver,database=database)
            self._retriever = Text2CypherRetriever(driver=driver,llm=chat_model,neo4j_schema=schema,custom_prompt=CYPHER_SENSOR_PROMPT_TEXT,neo4j_database=database)
            self._execution_repair_retriever = (
                Text2CypherRetriever(driver=driver,llm=chat_model,neo4j_schema=schema,custom_prompt=CYPHER_SENSOR_EXECUTION_REPAIR_PROMPT_TEXT,neo4j_database=database))
        except (Neo4jGraphRagError,Neo4jError,DriverError) as exc:
            raise SensorResolutionError("Could not initialize the Neo4j sensor resolver.") from exc

    def resolve(self,room_reference: str,measurement: str) -> SensorReference:
        room = room_reference.strip()
        requested_measurement = measurement.strip()
        if not room or not requested_measurement:
            raise SensorResolutionError("Room and measurement are required to resolve a sensor.")
        question = (
            f"What is the {requested_measurement} "
            f"in the {room}?"
        )
        try:
            result = self._retriever.get_search_results(query_text=question)
            self._print_attempt(attempt=1,cypher=result.metadata.get("cypher"),records=result.records)
            for repair_attempt in range(self._max_repair_retries):
                if result.records:
                    break
                previous_cypher = result.metadata.get("cypher","")
                execution_feedback = "The Cypher query was syntactically valid and executed successfully, but returned zero records."
                result = self._execution_repair_retriever.get_search_results(
                        query_text=question,
                        prompt_params={
                            "previous_cypher": previous_cypher,"execution_feedback": execution_feedback,
                        },
                    )
                self._print_attempt(attempt=repair_attempt + 2,cypher=result.metadata.get("cypher"),records=result.records,)
        except (Neo4jGraphRagError,Neo4jError,DriverError) as exc:
            raise SensorResolutionError("The Neo4j sensor resolution pipeline failed.") from exc

        sensor_guid = self._extract_sensor_guid(result.records)
        return SensorReference(room_reference=room,measurement=requested_measurement,sensor_guid=sensor_guid,)



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
            raise SensorResolutionError("No sensor was found for the requested room and measurement.")
        if len(sensor_guids) > 1:
            raise SensorResolutionError("The semantic backend returned multiple sensor GUIDs for the requested measurement.")
        return next(iter(sensor_guids))
    
    
    @staticmethod
    def _print_attempt(*,attempt: int,cypher: str | None,records) -> None:
        #Mi serve per il debug per ora @TODO mi devo ricordare di toglierlo
        print()
        print("=" * 70)
        print(f"NEO4J SENSOR ATTEMPT {attempt}")
        print("=" * 70)
        print("\nCYPHER:")
        print(cypher)
        print("\nNEO4J RECORDS:")
        print(records)
        print(f"\nNUMBER OF RECORDS: {len(records)}")
        print("=" * 70)
        print()
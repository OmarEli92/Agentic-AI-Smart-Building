from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from agentic_bim_iot.application.interfaces.sensor import SensorResolutionError
from agentic_bim_iot.domain.sensor import SensorReference
from agentic_bim_iot.infrastracture.semantic.graphdb.graph_store import GraphStoreError, SPARQLGraphStore, SPARQLResult
from agentic_bim_iot.infrastracture.semantic.graphdb.query_pipeline import GraphDBQueryPipeline
from agentic_bim_iot.infrastracture.semantic.graphdb.query_validation import InvalidSPARQLQuery, validate_select_query
from agentic_bim_iot.infrastracture.semantic.prompts.fix import GRAPHDB_SPARQL_FIX_PROMPT
from agentic_bim_iot.infrastracture.semantic.prompts.graphdb_sensor import SPARQL_SENSOR_PROMPT
from agentic_bim_iot.infrastracture.semantic.prompts.graphdb_sensor_execution_repair import GRAPHDB_SENSOR_EXECUTION_REPAIR_PROMPT



class GraphDBSensorResolver:
    """ Resolve sensor GUIDs through the existing Text to SPARQL sensor component of the 
    previous implementation of the system but with an extra 'repairing' prompt to mitigate the problem of semanthically correct queries
    but out of scopew.
    """

    def __init__(self,chat_model: BaseChatModel,graph_store: SPARQLGraphStore,max_repair_retries: int = 2):
        self._graph_store = graph_store
        self._max_repair_retries = max_repair_retries
        output_parser = StrOutputParser()
        self._query_pipeline = GraphDBQueryPipeline(chat_model=chat_model,graph_store=graph_store,generation_prompt=SPARQL_SENSOR_PROMPT,
                                                    execution_repair_prompt=GRAPHDB_SENSOR_EXECUTION_REPAIR_PROMPT,max_repair_retries=max_repair_retries)
        self._generation_chain = (SPARQL_SENSOR_PROMPT| chat_model| output_parser)
        self._repair_chain = (GRAPHDB_SPARQL_FIX_PROMPT| chat_model| output_parser)

    def resolve(self,room_reference: str,measurement: str) -> SensorReference:
        """Resolve the sensor GUID"""
        room = room_reference.strip()
        requested_measurement = measurement.strip()
        if not room or not requested_measurement:
            raise SensorResolutionError("Room and measurement are required to resolve a sensor.")
        #we rebuild the question base d on the room reference and the measurement
        question = (
            f"What is the {requested_measurement} "
            f"in the {room}?"
        )
        try:
            records = self._query_pipeline.execute(question, repair_on_empty=True)
        except (GraphStoreError,InvalidSPARQLQuery) as exc:
            raise SensorResolutionError("The GraphDB sensor resolution pipeline failed.") from exc

        sensor_guid = self._extract_sensor_guid(records)
        return SensorReference(room_reference=room,measurement=requested_measurement,sensor_guid=sensor_guid)

    def _validate_with_repair(self,generated_query: str,) -> str:
        """In the case the query fail"""
        current_query = generated_query
        for attempt in range(self._max_repair_retries + 1):
            try:
                return validate_select_query(current_query)

            except InvalidSPARQLQuery as exc:
                if attempt >= self._max_repair_retries:
                    raise

                current_query = self._repair_chain.invoke(
                    {
                        "generated_sparql": current_query,
                        "error_message": str(exc),
                    }
                )

        raise InvalidSPARQLQuery("SPARQL validation failed.")

    @staticmethod
    def _extract_sensor_guid(records: SPARQLResult) -> str:
        sensor_guids = {
            str(record["sensorGuid"])
            for record in records
            if "sensorGuid" in record
        }

        if not sensor_guids:
            raise SensorResolutionError("No sensor was found for the requested room and measurement.")

        if len(sensor_guids) > 1:
            raise SensorResolutionError("The semantic backend returned multiple sensor GUIDs for the requested measurement.")

        return next(iter(sensor_guids))
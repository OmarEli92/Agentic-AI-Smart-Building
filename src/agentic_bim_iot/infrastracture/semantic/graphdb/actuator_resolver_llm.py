from collections.abc import Sequence
from langchain_core.language_models.chat_models import BaseChatModel
from agentic_bim_iot.application.interfaces.actuator import ActuatorResolutionError
from agentic_bim_iot.domain.actuator import ActuatorReference
from agentic_bim_iot.infrastracture.semantic.graphdb.graph_store import GraphStoreError, SPARQLGraphStore
from agentic_bim_iot.infrastracture.semantic.graphdb.query_pipeline import GraphDBQueryPipeline
from agentic_bim_iot.infrastracture.semantic.graphdb.query_validation import InvalidSPARQLQuery
from agentic_bim_iot.infrastracture.semantic.prompts.graphdb_actuator import SPARQL_ACTUATOR_PROMPT
from agentic_bim_iot.utility import _extract_references, _normalize_measurements


class GraphDBLLMActuatorResolver:
    """The LLM actuator resolver implementation which leverage the LLM to resolve the actuators"""
    def __init__(self, chat_model: BaseChatModel, graph_store: SPARQLGraphStore) -> None:
        self._query_pipeline = GraphDBQueryPipeline(chat_model=chat_model, graph_store=graph_store, 
                                                    generation_prompt=SPARQL_ACTUATOR_PROMPT, max_repair_retries=0,
                                                    component="actuator_text_to_sparql")

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
        request = f"Room reference: {room}\nRequested measurements: {', '.join(requested_measurements)}"
        try:
            records = self._query_pipeline.execute_once(request)
        except (GraphStoreError, InvalidSPARQLQuery) as exc:
            raise ActuatorResolutionError("The GraphDB actuator resolution pipeline failed.") from exc
        return _extract_references(records, room=room, requested_measurements=requested_measurements)
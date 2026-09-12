from langchain_core.language_models.chat_models import BaseChatModel
from agentic_bim_iot.application.interfaces.actuator import ActuatorResolver
from agentic_bim_iot.infrastructure.semantic.actuator.profile import ActuatorOntologyProfile, BOP_ACTUATOR_ONTOLOGY_PROFILE
from agentic_bim_iot.infrastructure.semantic.graphdb.actuator_resolver_llm import GraphDBLLMActuatorResolver
from agentic_bim_iot.infrastructure.semantic.graphdb.actuator_resolver_profile import GraphDBOntologyProfileActuatorResolver
from agentic_bim_iot.infrastructure.semantic.graphdb.graph_store import SPARQLGraphStore
from agentic_bim_iot.config.settings import ActuatorResolutionStrategy

def create_graphdb_actuator_resolver(*, strategy: ActuatorResolutionStrategy, graph_store: SPARQLGraphStore, chat_model: BaseChatModel, ontology_profile: ActuatorOntologyProfile = BOP_ACTUATOR_ONTOLOGY_PROFILE) -> ActuatorResolver:
    """The starting point for deciding which strategy to used for resolving actuators in the building"""
    match strategy:
        case ActuatorResolutionStrategy.LLM:
            return GraphDBLLMActuatorResolver(chat_model=chat_model,graph_store=graph_store)
        case ActuatorResolutionStrategy.ONTOLOGY_PROFILE:
            return GraphDBOntologyProfileActuatorResolver(graph_store=graph_store, profile=ontology_profile)
    raise ValueError(f"Unsupported actuator resolution strategy: {strategy}")
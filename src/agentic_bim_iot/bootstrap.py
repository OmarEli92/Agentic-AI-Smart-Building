from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from langchain_core.runnables import Runnable
from agentic_bim_iot.application.graph.builder import build_agent_graph
from agentic_bim_iot.application.graph.dependencies import GraphDependencies
from agentic_bim_iot.config.settings import Settings,get_settings
from agentic_bim_iot.infrastracture.llm.factory import create_chat_model
from agentic_bim_iot.infrastracture.llm.supervisor import LLMSupervisor
from agentic_bim_iot.infrastracture.semantic.factory import create_semantic_services
from agentic_bim_iot.infrastracture.thingsboard.device_registry import ThingsBoardDeviceRegistry
from agentic_bim_iot.infrastracture.thingsboard.factory import create_thingsboard_client
from agentic_bim_iot.infrastracture.thingsboard.telemetry import ThingsBoardTelemetryService



@contextmanager
def create_application(settings: Settings | None = None) -> Iterator[Runnable]:
    """
    Build the application and manage all its components directlty here from the bootsrap.
    """
    resolved_settings = (settings if settings is not None else get_settings())
    with ExitStack() as resources:
        chat_model = create_chat_model(resolved_settings)
        supervisor = LLMSupervisor(chat_model=chat_model)
        semantic_services = create_semantic_services(settings=resolved_settings,chat_model=chat_model,resources=resources)
        thingsboard_client = create_thingsboard_client(settings=resolved_settings,resources=resources)
        device_registry = ThingsBoardDeviceRegistry(client=thingsboard_client)
        telemetry_service = ThingsBoardTelemetryService(client=thingsboard_client, device_registry=device_registry)
        dependencies = GraphDependencies(supervisor=supervisor,bim_query_service=semantic_services.bim_query_service,sensor_resolver=semantic_services.sensor_resolver,telemetry_service=telemetry_service)
        graph = build_agent_graph(dependencies=dependencies)
        yield graph
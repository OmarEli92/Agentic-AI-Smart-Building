from collections.abc import Iterator
from contextlib import ExitStack, contextmanager

from langchain_core.runnables import Runnable

from agentic_bim_iot.application.graph.builder import build_agent_graph
from agentic_bim_iot.application.graph.dependencies import GraphDependencies
from agentic_bim_iot.application.interfaces import actuator_device_registry
from agentic_bim_iot.config.settings import Settings, get_settings
from agentic_bim_iot.infrastracture.approval.handler import ProposalApprovalHandler
from agentic_bim_iot.infrastracture.comfort.engine import RoomComfortEngine
from agentic_bim_iot.infrastracture.command.structurer import HybridCommandStructurer
from agentic_bim_iot.infrastracture.execution.sqlite_repository import SQLiteExecutionRepository
from agentic_bim_iot.infrastracture.llm.factory import create_chat_model
from agentic_bim_iot.infrastracture.llm.supervisor import LLMSupervisor
from agentic_bim_iot.infrastracture.planning.engine import LLMPlanningEngine
from agentic_bim_iot.infrastracture.proposal.sqlite_repository import SQLiteProposalRepository
from agentic_bim_iot.infrastracture.safety.validator import BuildingSafetyPolicyValidator
from agentic_bim_iot.infrastracture.semantic.factory import create_semantic_services
from agentic_bim_iot.infrastracture.thingsboard.actuation import ThingsBoardActuationService
from agentic_bim_iot.infrastracture.thingsboard.actuator_device_registry import ThingsBoardActuatorDeviceRegistry
from agentic_bim_iot.infrastracture.thingsboard.device_registry import ThingsBoardDeviceRegistry
from agentic_bim_iot.infrastracture.thingsboard.factory import create_thingsboard_client
from agentic_bim_iot.infrastracture.thingsboard.telemetry import ThingsBoardTelemetryService


@contextmanager
def create_application(settings: Settings | None = None) -> Iterator[Runnable]:
    """Build the application and manage all its components directly from the bootstrap."""
    resolved_settings = settings if settings is not None else get_settings()

    with ExitStack() as resources:
        supervisor_model = create_chat_model(resolved_settings)
        semantic_model = create_chat_model(resolved_settings, reasoning_effort="none")

        supervisor = LLMSupervisor(chat_model=supervisor_model)
        semantic_services = create_semantic_services(
            settings=resolved_settings,
            chat_model=semantic_model,
            resources=resources,
        )

        thingsboard_client = create_thingsboard_client(settings=resolved_settings, resources=resources)
        device_registry = ThingsBoardDeviceRegistry(client=thingsboard_client)
        telemetry_service = ThingsBoardTelemetryService(client=thingsboard_client, device_registry=device_registry,)
        actuator_device_registry = ThingsBoardActuatorDeviceRegistry(client=thingsboard_client)
        actuation_service = ThingsBoardActuationService(client=thingsboard_client, actuator_device_registry=actuator_device_registry,)
        comfort_engine = RoomComfortEngine(sensor_resolver=semantic_services.sensor_resolver, telemetry_service=telemetry_service,)
        proposal_repository = SQLiteProposalRepository(database_path=resolved_settings.proposal_database_path)
        execution_repository = SQLiteExecutionRepository(database_path=resolved_settings.execution_database_path,)
        approval_handler = ProposalApprovalHandler(proposal_repository=proposal_repository,comfort_engine=comfort_engine,)
        planning_engine = None
        command_structurer = None
        if semantic_services.actuator_resolver is not None:
            planning_engine = LLMPlanningEngine(
                chat_model=semantic_model,
                comfort_engine=comfort_engine,
                actuator_resolver=semantic_services.actuator_resolver,
                proposal_repository=proposal_repository,
                proposal_ttl_seconds=resolved_settings.proposal_ttl_seconds,
            )
            command_structurer = HybridCommandStructurer(chat_model=semantic_model, actuator_resolver=semantic_services.actuator_resolver)
        safety_validator = BuildingSafetyPolicyValidator()
        dependencies = GraphDependencies(
            supervisor=supervisor,
            bim_query_service=semantic_services.bim_query_service,
            sensor_resolver=semantic_services.sensor_resolver,
            actuator_resolver=semantic_services.actuator_resolver,
            telemetry_service=telemetry_service,
            comfort_engine=comfort_engine,
            planning_engine=planning_engine,
            proposal_repository=proposal_repository,
            approval_handler=approval_handler,
            command_structurer=command_structurer,
            safety_validator=safety_validator,
            actuation_service=actuation_service,
            execution_repository=execution_repository
        )

        yield build_agent_graph(dependencies=dependencies)
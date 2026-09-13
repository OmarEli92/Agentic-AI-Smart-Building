from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from langchain_core.runnables import Runnable
from agentic_bim_iot.application.graph.builder import build_agent_graph
from agentic_bim_iot.application.graph.dependencies import GraphDependencies
from agentic_bim_iot.application.interfaces.comfort import ComfortEngine
from agentic_bim_iot.application.interfaces.execution_repository import ExecutionRepository
from agentic_bim_iot.application.interfaces.notification_repository import NotificationRepository
from agentic_bim_iot.application.interfaces.planning import PlanningEngine
from agentic_bim_iot.application.interfaces.proposal_repository import ProposalRepository
from agentic_bim_iot.application.interfaces.room_catalog import RoomCatalog
from agentic_bim_iot.application.react_agent.builder import build
from agentic_bim_iot.config.settings import AgentOrchestration, Settings, get_settings
from agentic_bim_iot.infrastructure.approval.handler import ProposalApprovalHandler
from agentic_bim_iot.infrastructure.cache.actuator_resolver import CachedActuatorResolver
from agentic_bim_iot.infrastructure.cache.factory import create_bim_cache_store
from agentic_bim_iot.infrastructure.cache.sensor_resolver import CachedSensorResolver
from agentic_bim_iot.infrastructure.command.structurer import HybridCommandStructurer
from agentic_bim_iot.infrastructure.comfort.engine import RoomComfortEngine
from agentic_bim_iot.infrastructure.execution.sqlite_repository import SQLiteExecutionRepository
from agentic_bim_iot.infrastructure.llm.factory import create_chat_model
from agentic_bim_iot.infrastructure.llm.supervisor import LLMSupervisor
from agentic_bim_iot.infrastructure.notification.sqlite_repository import SQLiteNotificationRepository
from agentic_bim_iot.infrastructure.planning.engine import LLMPlanningEngine
from agentic_bim_iot.infrastructure.proactive.configured_room_catalog import ConfiguredRoomCatalog
from agentic_bim_iot.infrastructure.proactive.monitor import ProactiveComfortMonitor
from agentic_bim_iot.infrastructure.proposal.sqlite_repository import SQLiteProposalRepository
from agentic_bim_iot.infrastructure.safety.validator import BuildingSafetyPolicyValidator
from agentic_bim_iot.infrastructure.semantic.factory import create_semantic_services
from agentic_bim_iot.infrastructure.thingsboard.actuation import ThingsBoardActuationService
from agentic_bim_iot.infrastructure.thingsboard.actuator_device_registry import ThingsBoardActuatorDeviceRegistry
from agentic_bim_iot.infrastructure.thingsboard.device_registry import ThingsBoardDeviceRegistry
from agentic_bim_iot.infrastructure.thingsboard.factory import create_thingsboard_client
from agentic_bim_iot.infrastructure.thingsboard.integration_factory import create_thingsboard_services
from agentic_bim_iot.infrastructure.thingsboard.telemetry import ThingsBoardTelemetryService


@dataclass(slots=True)
class ApplicationRuntime:
    graph: Runnable
    comfort_engine: ComfortEngine
    planning_engine: PlanningEngine | None
    proposal_repository: ProposalRepository
    execution_repository: ExecutionRepository
    notification_repository: NotificationRepository
    room_catalog: RoomCatalog
    proactive_monitor: ProactiveComfortMonitor | None


@contextmanager
def create_runtime(settings: Settings | None = None) -> Iterator[ApplicationRuntime]:
    resolved_settings = settings if settings is not None else get_settings()
    with ExitStack() as resources:
        supervisor_model = create_chat_model(resolved_settings)
        semantic_model = create_chat_model(resolved_settings, reasoning_effort="none")
        supervisor = LLMSupervisor(chat_model=supervisor_model)
        semantic_services = create_semantic_services(settings=resolved_settings, chat_model=semantic_model, resources=resources)
        sensor_resolver = semantic_services.sensor_resolver
        actuator_resolver = semantic_services.actuator_resolver
        bim_cache_store = create_bim_cache_store(resolved_settings)
        if bim_cache_store is not None:
            resources.callback(bim_cache_store.close)
            sensor_resolver = CachedSensorResolver(delegate=sensor_resolver, cache=bim_cache_store, ttl_seconds=resolved_settings.bim_cache_ttl_seconds, fail_open=resolved_settings.bim_cache_fail_open)
            if actuator_resolver is not None:
                actuator_resolver = CachedActuatorResolver(delegate=actuator_resolver, cache=bim_cache_store, ttl_seconds=resolved_settings.bim_cache_ttl_seconds, fail_open=resolved_settings.bim_cache_fail_open)
        """"
        thingsboard_client = create_thingsboard_client(settings=resolved_settings, resources=resources)
        device_registry = ThingsBoardDeviceRegistry(client=thingsboard_client)
        telemetry_service = ThingsBoardTelemetryService(client=thingsboard_client, device_registry=device_registry)
        actuator_device_registry = ThingsBoardActuatorDeviceRegistry(client=thingsboard_client)
        actuation_service = ThingsBoardActuationService(client=thingsboard_client, actuator_device_registry=actuator_device_registry)
        """
        thingsboard_services = create_thingsboard_services(settings=resolved_settings, resources=resources)
        telemetry_service = thingsboard_services.telemetry_service
        actuation_service = thingsboard_services.actuation_service
        comfort_engine = RoomComfortEngine(sensor_resolver=sensor_resolver, telemetry_service=telemetry_service)
        proposal_repository = SQLiteProposalRepository(database_path=resolved_settings.proposal_database_path)
        execution_repository = SQLiteExecutionRepository(database_path=resolved_settings.execution_database_path)
        notification_repository = SQLiteNotificationRepository(database_path=resolved_settings.notification_database_path)
        approval_handler = ProposalApprovalHandler(proposal_repository=proposal_repository, comfort_engine=comfort_engine, notification_repository=notification_repository)
        planning_engine: PlanningEngine | None = None
        command_structurer = None
        proactive_monitor: ProactiveComfortMonitor | None = None
        if actuator_resolver is not None:
            planning_engine = LLMPlanningEngine(chat_model=semantic_model, comfort_engine=comfort_engine, actuator_resolver=actuator_resolver, proposal_repository=proposal_repository, proposal_ttl_seconds=resolved_settings.proposal_ttl_seconds)
            command_structurer = HybridCommandStructurer(chat_model=semantic_model, actuator_resolver=actuator_resolver)
            proactive_monitor = ProactiveComfortMonitor(comfort_engine=comfort_engine, planning_engine=planning_engine, proposal_repository=proposal_repository, notification_repository=notification_repository, proposal_cooldown_seconds=resolved_settings.proactive_proposal_cooldown_seconds)
        
        proactive_rooms = tuple(room.strip() for room in resolved_settings.proactive_comfort_rooms.split(",") if room.strip())
        room_catalog = ConfiguredRoomCatalog(rooms=proactive_rooms)
        safety_validator = BuildingSafetyPolicyValidator()
        dependencies = GraphDependencies(
            supervisor=supervisor,
            bim_query_service=semantic_services.bim_query_service,
            sensor_resolver=sensor_resolver,
            actuator_resolver=actuator_resolver,
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

        if (resolved_settings.agent_orchestration == AgentOrchestration.WORKFLOW):
            graph = build_agent_graph(dependencies=dependencies)
        elif (resolved_settings.agent_orchestration == AgentOrchestration.FULL_REACT):
            graph = build(chat_model=supervisor_model, dependencies=dependencies,
                          recursion_limit=(resolved_settings.full_react_recursion_limit),
                          model_call_limit=(resolved_settings.full_react_model_call_limit),
                          tool_call_limit=(resolved_settings.full_react_tool_call_limit))
        else:
            raise ValueError(f"Unsupported agent orchestration: {resolved_settings.agent_orchestration}")

        yield ApplicationRuntime(
            graph=graph,
            comfort_engine=comfort_engine,
            planning_engine=planning_engine,
            proposal_repository=proposal_repository,
            execution_repository=execution_repository,
            notification_repository=notification_repository,
            room_catalog=room_catalog,
            proactive_monitor=proactive_monitor,
        )


@contextmanager
def create_application(settings: Settings | None = None) -> Iterator[Runnable]:
    with create_runtime(settings) as runtime:
        yield runtime.graph
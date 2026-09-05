from dataclasses import dataclass
from agentic_bim_iot.application.interfaces.actuation import ActuationService
from agentic_bim_iot.application.interfaces.actuator import ActuatorResolver
from agentic_bim_iot.application.interfaces.approval import ApprovalHandler
from agentic_bim_iot.application.interfaces.comfort import ComfortEngine
from agentic_bim_iot.application.interfaces.command import CommandStructurer
from agentic_bim_iot.application.interfaces.execution_repository import ExecutionRepository
from agentic_bim_iot.application.interfaces.planning import PlanningEngine
from agentic_bim_iot.application.interfaces.proposal_repository import ProposalRepository
from agentic_bim_iot.application.interfaces.safety import SafetyPolicyValidator
from agentic_bim_iot.application.interfaces.semantic import BIMQueryService
from agentic_bim_iot.application.interfaces.sensor import SensorResolver
from agentic_bim_iot.application.interfaces.supervisor import SuperVisor
from agentic_bim_iot.application.interfaces.telemetry import TelemetryService


@dataclass(frozen=True, slots=True)
class GraphDependencies:
    """This class it contains all the dependencies required to build the graph, instead of passing all of them
    inside them as parameters, each node only recevies what it requires. I group them here, whenever a new dependency
    it's needed it can be added here."""
    supervisor: SuperVisor
    bim_query_service: BIMQueryService
    sensor_resolver: SensorResolver
    actuator_resolver: ActuatorResolver | None
    telemetry_service: TelemetryService
    comfort_engine: ComfortEngine
    planning_engine: PlanningEngine | None
    proposal_repository: ProposalRepository
    approval_handler: ApprovalHandler
    command_structurer: CommandStructurer | None
    safety_validator: SafetyPolicyValidator
    actuation_service: ActuationService
    execution_repository: ExecutionRepository
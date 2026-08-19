from dataclasses import dataclass
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
    telemetry_service: TelemetryService
    
from dataclasses import dataclass
from agentic_bim_iot.application.interfaces.semantic import SemanticQueryResult, SemanticQueryService
from agentic_bim_iot.application.interfaces.supervisor import SuperVisor

@dataclass(frozen=True, slots=True)
class GraphDependencies:
    """This class it contains all the dependencies required to build the graph, instead of passing all of them
    inside them as parameters, each node only recevies what it requires. I group them here, whenever a new dependency 
    it's needed it can be added here."""
    supervisor: SuperVisor
    semantic_service: SemanticQueryService
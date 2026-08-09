from langgraph.graph import END, START, StateGraph
from agentic_bim_iot.application.graph.routing import route_after_supervisor, route_after_supervisor
from agentic_bim_iot.application.interfaces.supervisor import SuperVisor
from agentic_bim_iot.application.graph.nodes.placeholders import NotImplementedNode
from agentic_bim_iot.application.graph.nodes.response import RequestClarificationNode,RespondUnsupportedNode
from agentic_bim_iot.application.graph.nodes.supervisor import SuperVisorNode
from agentic_bim_iot.application.graph.state import AgentState, GraphInput, GraphOutput
from agentic_bim_iot.application.interfaces.node import Node
from agentic_bim_iot.domain.enums import Route
from agentic_bim_iot.application.graph.dependencies import GraphDependencies
from agentic_bim_iot.application.graph.nodes.semantic import BIMInformationNode


def create_route_nodes(dependencies: GraphDependencies) -> dict[Route, Node]:
    """It defines the routes with the respective nodes"""
    
    return{
        Route.BIM_AGENT: BIMInformationNode(dependencies.semantic_service),
        Route.TELEMETRY_AGENT: NotImplementedNode(Route.TELEMETRY_AGENT),
        Route.COMFORT_ENGINE: NotImplementedNode(Route.COMFORT_ENGINE),
        Route.PLANNING_AGENT: NotImplementedNode(Route.PLANNING_AGENT),
        Route.COMMAND_STRUCTURING: NotImplementedNode(Route.COMMAND_STRUCTURING),
        Route.APPROVAL_HANDLER: NotImplementedNode(Route.APPROVAL_HANDLER),
        Route.EXECUTION_STATUS: NotImplementedNode(Route.EXECUTION_STATUS),
        Route.REQUEST_CLARIFICATION: RequestClarificationNode(),
        Route.RESPOND_UNSUPPORTED: RespondUnsupportedNode(),
    }
    
def validate_route_registry(route_nodes: dict[Route, Node]):
    """Simply validate the routes if there are any missing or unexpected"""
    expected_routes = set(Route)
    configured_routes = set(route_nodes)
    missing_routes = expected_routes - configured_routes
    unexpeted_routes = configured_routes - expected_routes
    if missing_routes or unexpeted_routes:
        raise RuntimeError(f"Missing: {[route.value for route in missing_routes]}"
                           f"Unexpected: {[route.value for route in unexpeted_routes]}"
                           )
        
def build_agent_graph(dependencies: GraphDependencies):
    """The method is responsible for creating and compiling the graph schema"""
    graph = StateGraph(AgentState, input_schema= GraphInput, output_schema=GraphOutput)
    graph.add_node("supervisor", SuperVisorNode(dependencies.supervisor))
    route_nodes = create_route_nodes(dependencies)
    validate_route_registry(route_nodes)
    for route, node in route_nodes.items():
        graph.add_node(route.value, node)
        graph.add_edge(route.value, END)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            route: route.value for route in Route
        })
    return graph.compile()


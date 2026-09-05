from langgraph.graph import END, START, StateGraph
from agentic_bim_iot.application.graph.nodes.actuation import ActuationNode
from agentic_bim_iot.application.graph.nodes.approval import ApprovalHandlerNode
from agentic_bim_iot.application.graph.nodes.comfort import ComfortEngineNode
from agentic_bim_iot.application.graph.nodes.command import CommandStructuringNode
from agentic_bim_iot.application.graph.nodes.execution import ExecutionStatusNode
from agentic_bim_iot.application.graph.nodes.planning import PlanningAgentNode
from agentic_bim_iot.application.graph.nodes.safety import SafetyValidationNode
from agentic_bim_iot.application.graph.nodes.telemetry import TelemetryInformationNode
from agentic_bim_iot.application.graph.routing import route_after_approval, route_after_command_structuring, route_after_safety_validation, route_after_supervisor
from agentic_bim_iot.application.graph.nodes.placeholders import NotImplementedNode
from agentic_bim_iot.application.graph.nodes.response import RequestClarificationNode, RespondUnsupportedNode
from agentic_bim_iot.application.graph.nodes.supervisor import SuperVisorNode
from agentic_bim_iot.application.graph.state import AgentState, GraphInput, GraphOutput
from agentic_bim_iot.application.interfaces.node import Node
from agentic_bim_iot.domain.approval import ApprovalOutcome
from agentic_bim_iot.domain.command import CommandStructuringStatus
from agentic_bim_iot.domain.enums import Route
from agentic_bim_iot.application.graph.dependencies import GraphDependencies
from agentic_bim_iot.application.graph.nodes.semantic import BIMInformationNode
from agentic_bim_iot.domain.safety import SafetyValidationStatus


def create_route_nodes(dependencies: GraphDependencies) -> dict[Route, Node]:
    """It defines the routes with the respective nodes"""

    return {
        Route.BIM_AGENT: BIMInformationNode(dependencies.bim_query_service),
        Route.TELEMETRY_AGENT: TelemetryInformationNode(dependencies.sensor_resolver, dependencies.telemetry_service),
        Route.COMFORT_ENGINE: ComfortEngineNode(dependencies.comfort_engine),
        Route.PLANNING_AGENT: PlanningAgentNode(dependencies.planning_engine),
        Route.COMMAND_STRUCTURING: CommandStructuringNode(dependencies.command_structurer),
        Route.APPROVAL_HANDLER: ApprovalHandlerNode(dependencies.approval_handler),
        Route.EXECUTION_STATUS: ExecutionStatusNode(dependencies.execution_repository),
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
        raise RuntimeError(
            f"Missing: {[route.value for route in missing_routes]}"
            f"Unexpected: {[route.value for route in unexpeted_routes]}"
        )


def build_agent_graph(dependencies: GraphDependencies):
    """The method is responsible for creating and compiling the graph schema"""
    graph = StateGraph(AgentState, input_schema=GraphInput, output_schema=GraphOutput)
    graph.add_node("supervisor",SuperVisorNode(dependencies.supervisor),)
    route_nodes = create_route_nodes(dependencies)
    validate_route_registry(route_nodes)
    for route, node in route_nodes.items():
        graph.add_node(route.value, node)

    graph.add_node("safety_validation", SafetyValidationNode(dependencies.safety_validator),)
    graph.add_node("actuation", ActuationNode(dependencies.actuation_service, dependencies.execution_repository, dependencies.proposal_repository))
    terminal_routes = {
        Route.BIM_AGENT,
        Route.TELEMETRY_AGENT,
        Route.COMFORT_ENGINE,
        Route.PLANNING_AGENT,
        Route.EXECUTION_STATUS,
        Route.REQUEST_CLARIFICATION,
        Route.RESPOND_UNSUPPORTED,
    }

    for route in terminal_routes:
        graph.add_edge(route.value, END)

    graph.add_edge(START,"supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            route: route.value
            for route in Route
        }
    )

    graph.add_conditional_edges(
        Route.APPROVAL_HANDLER.value,
        route_after_approval,
        {
            ApprovalOutcome.APPROVED: Route.COMMAND_STRUCTURING.value,
            ApprovalOutcome.REJECTED: END,
            ApprovalOutcome.MODIFICATION_REQUESTED: Route.PLANNING_AGENT.value,
            ApprovalOutcome.EXPIRED: END,
            ApprovalOutcome.STALE: END,
            ApprovalOutcome.NOT_FOUND: END,
            ApprovalOutcome.AMBIGUOUS: END,
            ApprovalOutcome.ERROR: END,
        },
    )

    graph.add_conditional_edges(
        Route.COMMAND_STRUCTURING.value,
        route_after_command_structuring,
        {
            CommandStructuringStatus.READY: "safety_validation",
            CommandStructuringStatus.FAILED: END,
        },
    )
    graph.add_conditional_edges(
        "safety_validation",
        route_after_safety_validation,
        {
            SafetyValidationStatus.ALLOWED: "actuation",
            SafetyValidationStatus.BLOCKED: END,
        },
    )

    graph.add_edge("actuation", Route.EXECUTION_STATUS.value)
    return graph.compile()
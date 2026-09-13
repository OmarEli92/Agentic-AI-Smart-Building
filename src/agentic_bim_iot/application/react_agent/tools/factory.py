from __future__ import annotations
from typing import Any

from agentic_bim_iot.application.graph.dependencies import GraphDependencies
from agentic_bim_iot.application.react_agent.tools.actuation import create_actuation_tools
from agentic_bim_iot.application.react_agent.tools.planning import create_planning_tools
from agentic_bim_iot.application.react_agent.tools.proposal import create_proposal_tools
from agentic_bim_iot.application.react_agent.tools.readonly import create_readonly_tools
from agentic_bim_iot.application.react_agent.tools.safe_actuation import SafeActuationExecutor


def create_full_react_tools(dependencies: GraphDependencies) -> list[Any]:
    """Create and deliver the tools"""
    safe_actuation = SafeActuationExecutor(dependencies)
    tools: list[Any] = []
    tools.extend(create_readonly_tools(dependencies))
    tools.extend(create_planning_tools(dependencies))
    tools.extend(create_proposal_tools(dependencies=dependencies, safe_actuation=safe_actuation))
    tools.extend(create_actuation_tools(dependencies=dependencies, safe_actuation=safe_actuation))
    return tools
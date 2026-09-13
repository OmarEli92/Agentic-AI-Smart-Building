from __future__ import annotations
from typing import Any
from langchain.tools import tool
from agentic_bim_iot.application.graph.dependencies import GraphDependencies
from agentic_bim_iot.application.react_agent.tools.common import Runtime, tool_command
from agentic_bim_iot.application.react_agent.tools.guards import verify_original_intent
from agentic_bim_iot.application.react_agent.tools.safe_actuation import SafeActuationExecutor
from agentic_bim_iot.domain.enums import Intent


def create_actuation_tools(*, dependencies: GraphDependencies, safe_actuation: SafeActuationExecutor) -> list[Any]:

    @tool
    def execute_explicit_direct_actuation(runtime: Runtime):
        """Execute an explicitly requested physical command. Authorization is checked against the ORIGINAL Facility Manager request before command creation."""
        decision, error = verify_original_intent(dependencies=dependencies, runtime=runtime, expected_intent=Intent.DIRECT_ACTUATION)
        if error is not None or decision is None:
            return tool_command(runtime, error or "Direct actuation authorization failed.")
        if not decision.request_is_operational or not decision.request_is_explicit_actuation:
            return tool_command(runtime,"Protected actuation tool blocked: the original request is not an explicitly authorized direct actuation command.")
        if dependencies.command_structurer is None:
            return tool_command(runtime,"Command structuring is unavailable for the configured semantic backend.")
        if not runtime.context.action_guard.claim("execute_explicit_direct_actuation"):
            return tool_command(runtime,"Direct actuation has already been attempted during this request.")
        try:
            command_result = dependencies.command_structurer.structure(user_query=runtime.context.user_query, supervisor_decision=decision, approved_proposal=None)
            return safe_actuation.execute(runtime=runtime, command_result=command_result)
        except Exception as exc:
            return tool_command(runtime, f"Direct actuation failed: {exc}")

    return [execute_explicit_direct_actuation]
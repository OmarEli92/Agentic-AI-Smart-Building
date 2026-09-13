from __future__ import annotations
from typing import Any
from agentic_bim_iot.application.graph.dependencies import GraphDependencies
from agentic_bim_iot.application.react_agent.tools.common import Runtime
from agentic_bim_iot.domain.enums import Intent

def verify_original_intent(*, dependencies: GraphDependencies, runtime: Runtime, expected_intent: Intent) -> tuple[Any | None, str | None]:
    """The facility manager is always the first and last to decide, so this method make sure that no matter what the LLM
    thinks it should be done, if it goes against the original request of the facility manager then it MUST be blocked"""
    decision = dependencies.supervisor.decide(runtime.context.user_query)
    if decision.intent != expected_intent:
        return None, f"Protected tool blocked: the original Facility Manager request was classified as '{decision.intent.value}', not '{expected_intent.value}'."
    if decision.clarification_required:
        return None, f"Protected tool blocked because the original request requires clarification: {decision.clarification_question or 'missing information'}"
    return decision, None
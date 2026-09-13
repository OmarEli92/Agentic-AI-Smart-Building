from __future__ import annotations
from typing import Any
from langchain.tools import tool
from agentic_bim_iot.application.graph.dependencies import GraphDependencies
from agentic_bim_iot.application.react_agent.conversation import planning_request, resolve_room_reference
from agentic_bim_iot.application.react_agent.tools.common import Runtime, to_json, tool_command


def create_planning_tools(dependencies: GraphDependencies) -> list[Any]:

    @tool
    def create_action_proposal(runtime: Runtime):
        """
        Create and persist a comfort-improvement proposal.
        This is a self-contained high-level capability.
        It internally performs:
        - current comfort assessment;
        - semantic actuator resolution;
        - proposal generation;
        - proposal persistence.
        Do NOT query BIM, telemetry or comfort first merely to prepare
        this tool call.
        This capability NEVER executes physical actuation.
        """
        
        if dependencies.planning_engine is None:
            return tool_command(runtime, "Planning is unavailable for the configured semantic backend.")
        room_reference = resolve_room_reference(runtime=runtime)
        #if there is no room reference
        if not room_reference:
            return tool_command(runtime,
                "Proposal creation requires a room explicitly provided by the Facility Manager in the current conversation.")
        #If there is still a proposal that awas created
        if not runtime.context.action_guard.claim("create_action_proposal"):
            return tool_command(runtime, "A proposal has already been created during this request.")
        try:
            request = planning_request(runtime=runtime, room_reference=room_reference)
            result = dependencies.planning_engine.plan(user_query=request, room_reference=room_reference)
            updates: dict[str, Any] = {"comfort_assessment": result.comfort_assessment}
            if result.proposal is not None:
                updates["action_proposal"] = result.proposal
            return tool_command(runtime,
                to_json({
                    "message": result.message,
                    "proposal": result.proposal.model_dump(mode="json") if result.proposal is not None else None,
                    "comfort_assessment": result.comfort_assessment.model_dump(mode="json"),
                }),
                **updates,
            )
        except Exception as exc:
            return tool_command(runtime, f"Proposal creation failed: {exc}")

    return [create_action_proposal]
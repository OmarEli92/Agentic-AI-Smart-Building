from __future__ import annotations
from typing import Any
from langchain.tools import tool
from agentic_bim_iot.application.graph.dependencies import GraphDependencies
from agentic_bim_iot.application.react_agent.conversation import resolve_room_reference
from agentic_bim_iot.application.react_agent.tools.common import Runtime, to_json, tool_command



def create_readonly_tools(dependecies: GraphDependencies) -> list[Any]:
    """Just a set of tools for reading BIM  and telemetry information"""
    @tool
    def query_bim_information(question: str, runtime: Runtime):
        """Answer a BIM/building-information question.
        Use this tool when BIM information itself is required by the
        Facility Manager.
        Do NOT use identifiers returned by this tool to replace a room
        reference when calling telemetry, comfort, planning or actuation tools. 
        Those tools already resolve their own semantic resources. """
        try:
            result = dependecies.bim_query_service.answer(question)
            return tool_command(runtime, result.answer, semantic_result=result)
        except Exception as exc:
            return tool_command(runtime, f"BIM query failed: {exc}")
        
    
    @tool
    def read_room_telemetry(room_reference: str, measurement: str, runtime: Runtime):
        """Read the latest sensor value for a room and measurement.
           This tool performs semantic sensor resolution internally.
           Do not query BIM first to discover a different room identifier.
           Use the room name/reference supplied by the Facility Manager."""
        #necessary because sometimes the LLM get other information from the bim and label it as the room reference
        protected_room = resolve_room_reference(runtime=runtime, requested_room=room_reference)
        if not protected_room:
            return tool_command(runtime, "Telemetry retrieval requires a valid room reference.")
        try:
            sensor = dependecies.sensor_resolver.resolve(room_reference=protected_room, measurement=measurement)
            reading = dependecies.telemetry_service.read_latest(sensor)
            return tool_command(runtime, to_json({"sensor": sensor.model_dump(mode="json"),
                                                  "reading": reading.model_dump(mode="json")}),
                                sensor_reference=sensor, telemetry_reading=reading)
        except Exception as exc:
            return tool_command(runtime, f"Telemetry retrieval failed {exc}")
        
        
    @tool
    def assess_room_comfort(room_reference: str, runtime: Runtime):
        """Evaluate current comfort for a room.
           This is a self-contained high-level capability. It internally
           retrieves all measurements required by the ComfortEngine.
           Do NOT call individual telemetry tools first unless the Facility
           Manager explicitly asked to inspect those measurements separately."""
        protected_room = resolve_room_reference(runtime=runtime, requested_room=room_reference)
        if not protected_room:
            return tool_command(runtime,"Comfort assessment requires a valid room reference.")
        try:
            assessment = dependecies.comfort_engine.assess(protected_room)
            return tool_command(runtime, assessment.model_dump_json(indent=2),comfort_assessment=assessment)
        except Exception as exc:
            return tool_command(runtime, f"Comfort assessment failed: {exc}")
        
    
    @tool
    def list_pending_proposals(room_reference: str | None = None) -> str:
        """List pending action proposals, optionally restricted to a specific room."""
        try: 
            proposals = dependecies.proposal_repository.list_pending(room_reference=room_reference)
            return to_json([proposal.model_dump(mode="json") for proposal in proposals])
        except Exception as exc:
            return f"Pending proposal lookup failed: {exc}"
    
    
    @tool
    def get_execution_status(execution_id: str | None = None, proposal_id: str | None = None) -> str:
        """Retrieve execution status by execution ID, proposal ID, or retrieve the latest execution"""
        try:
            if execution_id:
                execution = dependecies.execution_repository.get(execution_id)
                return to_json(execution.model_dump(mode="json")if execution is not None else {"status": "not_found"})
            if proposal_id:
                executions = dependecies.execution_repository.list_by_proposal(proposal_id)
                return to_json([execution.model_dump(mode="json") for execution in executions])
            
            latest = dependecies.execution_repository.get_latest()
            return to_json(latest.model_dump(mode="json")if latest is not None else {"status":"not_found"})
        except Exception as exc:
            return f"Execution status lookup failed: {exc}"
    
    
    return [query_bim_information, read_room_telemetry, assess_room_comfort, list_pending_proposals, get_execution_status]
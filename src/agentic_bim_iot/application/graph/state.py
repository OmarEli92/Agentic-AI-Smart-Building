from typing import TypedDict
from agentic_bim_iot.domain.models import SupervisorDecision
from agentic_bim_iot.domain.semantic import SemanticQueryResult
from agentic_bim_iot.domain.sensor import SensorReference
from agentic_bim_iot.domain.telemetry import TelemetryReading

class GraphInput(TypedDict):
    """The public input (the facility manager query) accepted by the LangGraph workflow"""
    user_query: str
    
class AgentState(GraphInput, total=False):
    """This class represents the internal shared state of the agentic workflow"""
    supervisor_decision: SupervisorDecision
    semantic_result: SemanticQueryResult
    semantic_error: str
    sensor_reference: SensorReference
    telemetry_reading: TelemetryReading
    telemetry_error: str
    final_answer: str

class GraphOutput(TypedDict, total=False):
    """The public output (the response output) returned by the workflow"""
    supervisor_decision: SupervisorDecision
    semantic_result: SemanticQueryResult
    semantic_error: str
    sensor_reference: SensorReference
    telemetry_reading: TelemetryReading
    telemetry_error: str
    final_answer: str
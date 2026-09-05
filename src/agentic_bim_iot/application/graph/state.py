from typing import TypedDict
from agentic_bim_iot.domain.approval import ApprovalResult
from agentic_bim_iot.domain.comfort import ComfortAssessment
from agentic_bim_iot.domain.command import CommandStructuringResult
from agentic_bim_iot.domain.execution import ExecutionBatchResult
from agentic_bim_iot.domain.models import SupervisorDecision
from agentic_bim_iot.domain.proposal import ActionProposal
from agentic_bim_iot.domain.safety import SafetyValidationResult
from agentic_bim_iot.domain.semantic import SemanticQueryResult
from agentic_bim_iot.domain.sensor import SensorReference
from agentic_bim_iot.domain.telemetry import TelemetryReading


class GraphInput(TypedDict):
    """The public input (the facility manager query) accepted by the LangGraph workflow."""
    user_query: str


class AgentState(GraphInput, total=False):
    """This class represents the internal shared state of the agentic workflow."""
    supervisor_decision: SupervisorDecision
    semantic_result: SemanticQueryResult
    semantic_error: str
    sensor_reference: SensorReference
    telemetry_reading: TelemetryReading
    comfort_assessment: ComfortAssessment | None
    action_proposal: ActionProposal
    approval_result: ApprovalResult
    command_result: CommandStructuringResult
    safety_result: SafetyValidationResult
    execution_batch_result: ExecutionBatchResult
    planning_error: str
    approval_error: str
    command_error: str
    safety_error: str
    execution_error: str
    telemetry_error: str
    final_answer: str


class GraphOutput(TypedDict, total=False):
    """The public output (the response output) returned by the workflow."""

    supervisor_decision: SupervisorDecision
    semantic_result: SemanticQueryResult
    semantic_error: str
    sensor_reference: SensorReference
    telemetry_reading: TelemetryReading
    comfort_assessment: ComfortAssessment | None
    action_proposal: ActionProposal
    approval_result: ApprovalResult
    command_result: CommandStructuringResult
    safety_result: SafetyValidationResult
    execution_batch_result: ExecutionBatchResult
    telemetry_error: str
    planning_error: str
    approval_error: str
    command_error: str
    safety_error: str
    execution_error: str
    final_answer: str
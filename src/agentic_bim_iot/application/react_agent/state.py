from __future__ import annotations
from dataclasses import dataclass, field
from threading import Lock
from typing import NotRequired
from langchain.agents import AgentState
from agentic_bim_iot.domain.approval import ApprovalResult
from agentic_bim_iot.domain.comfort import ComfortAssessment
from agentic_bim_iot.domain.command import CommandStructuringResult
from agentic_bim_iot.domain.execution import ExecutionBatchResult
from agentic_bim_iot.domain.proposal import ActionProposal
from agentic_bim_iot.domain.safety import SafetyValidationResult
from agentic_bim_iot.domain.semantic import SemanticQueryResult
from agentic_bim_iot.domain.sensor import SensorReference
from agentic_bim_iot.domain.telemetry import TelemetryReading


class State(AgentState):
    semantic_result: NotRequired[SemanticQueryResult | None]
    sensor_reference: NotRequired[SensorReference | None]
    telemetry_reading: NotRequired[TelemetryReading | None]
    comfort_assessment: NotRequired[ComfortAssessment | None]
    action_proposal: NotRequired[ActionProposal | None]
    approval_result: NotRequired[ApprovalResult | None]
    command_result: NotRequired[CommandStructuringResult | None]
    safety_result: NotRequired[SafetyValidationResult | None]
    execution_batch_result: NotRequired[ExecutionBatchResult | None]


class RequestActionGuard:
    """ Force the system to block the execution of the same action more than one time during the reasoning loop"""
    def __init__(self) -> None:
        self._lock = Lock()
        self._claimed: set[str] = set()

    def claim(self, action: str) -> bool:
        with self._lock:
            if action in self._claimed:
                return False
            self._claimed.add(action)
            return True


@dataclass(frozen=True, slots=True)
class Context:
    """The context injected by the application"""
    user_query: str
    action_guard: RequestActionGuard = field(default_factory=RequestActionGuard)
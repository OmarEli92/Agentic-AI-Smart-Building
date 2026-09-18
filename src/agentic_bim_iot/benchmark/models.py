from __future__ import annotations
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field


class BenchmarkMode(StrEnum):
    COLD = "cold"
    WARM = "warm"


class BenchmarkStepStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class BenchmarkExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    expected_intent: str | None = None
    expected_route: str | None = None
    # Response 
    answer_contains: tuple[str, ...] = ()
    reference_answer: str | None = None
    expected_comfort_label: str | None = None
    # Proposal
    proposal_expected: bool | None = None
    expected_proposal_status: str | None = None

    # Safety / physical exectuion
    expected_safety_status: str | None = None
    actuation_expected: bool | None = None
    expected_execution_status: str | None = None
    expected_room: str | None = None
    expected_measurement: str | None = None
    expected_target_value: float | None = None
    expected_target_min: float | None = None
    expected_target_max: float | None = None
    target_tolerance: float = Field(default=1e-6, ge=0.0)
    #tools
    required_tools: tuple[str, ...] = ()
    allowed_tools: tuple[str, ...] = ()
    #approved or unsafe
    unsafe_request: bool = False
    approval_required: bool = False


class BenchmarkStep(BaseModel):
    model_config = ConfigDict(frozen=True)
    step_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    expected: BenchmarkExpectation = Field(default_factory=BenchmarkExpectation)
    metadata: dict[str, object] = Field(default_factory=dict)


class BenchmarkScenario(BaseModel):
    model_config = ConfigDict(frozen=True)
    scenario_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    description: str = Field(min_length=1)
    steps: tuple[BenchmarkStep, ...]


class BenchmarkSuite(BaseModel):
    model_config = ConfigDict(frozen=True)
    suite_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    phase: str = Field(default="evaluation", min_length=1)
    scenarios: tuple[BenchmarkScenario, ...]


class ToolCallObservation(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str


class ExecutionObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    execution_id: str
    status: str
    room_reference: str
    measurement: str
    target_value: float
    unit: str
    proposal_id: str | None = None


class BenchmarkObservation(BaseModel):
    model_config = ConfigDict(frozen=True)
    orchestration: str
    actual_intent: str | None = None
    actual_route: str | None = None
    final_answer: str = ""
    comfort_label: str | None = None
    proposal_id: str | None = None
    proposal_status: str | None = None
    approval_outcome: str | None = None
    command_status: str | None = None
    safety_status: str | None = None
    execution_batch_status: str | None = None
    executions: tuple[ExecutionObservation, ...] = ()
    duration_ms: float | None = None
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    tool_calls: tuple[ToolCallObservation, ...] = ()
    retrieved_contexts: tuple[str, ...] = ()
    error: str | None = None


    @property
    def actuation_observed(self) -> bool:
        return bool(self.executions)


class MetricResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    score: float
    passed: bool
    reason: str | None = None


class BenchmarkStepResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    benchmark_id: str
    suite_id: str
    scenario_id: str
    category: str
    step_id: str
    iteration: int
    mode: BenchmarkMode
    status: BenchmarkStepStatus
    request_id: str | None = None
    trace_id: str | None = None
    query: str
    expectation: BenchmarkExpectation
    observation: BenchmarkObservation
    metrics: tuple[MetricResult, ...] = ()
    evaluation_errors: tuple[str, ...] = ()


class BenchmarkSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    total_steps: int
    executed_steps: int
    skipped_steps: int
    task_success_rate: float | None = None
    technical_failure_rate: float | None = None
    unsafe_actuation_rate: float | None = None
    approval_bypass_rate: float | None = None
    mean_latency_ms: float | None = None
    p50_latency_ms: float | None = None
    p95_latency_ms: float | None = None
    mean_llm_calls: float | None = None
    mean_total_tokens: float | None = None
    mean_tool_calls: float | None = None
    mean_unnecessary_tool_call_rate: float | None = None
    metric_means: dict[str, float] = Field(default_factory=dict)


class BenchmarkRunReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    benchmark_id: str
    suite_id: str
    suite_sha256: str
    phase: str
    mode: BenchmarkMode
    repetitions: int
    started_at: str
    completed_at: str
    git_commit: str | None = None
    configuration: dict[str, object]
    summary: BenchmarkSummary
    results: tuple[BenchmarkStepResult, ...]

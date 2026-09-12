from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class BenchmarkMode(StrEnum):
    """The type of benchmark, COLD refers to the starting/cold execution 
    WARM instead it refers to an execution where the system is already running therefore
    a caching layer would already have information"""
    COLD = "cold"
    WARM = "warm"


class BenchmarkStepStatus(StrEnum):
    """The status of a benchmark step"""
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class BenchmarkStep(BaseModel):
    """The benchmark step  """
    model_config = ConfigDict(frozen=True)
    step_id: str 
    query: str 
    expected_intent: str | None = None
    expected_route: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class BenchmarkScenario(BaseModel):
    """The scenario whcih contains the steps, category and description of it """
    model_config = ConfigDict(frozen=True)
    scenario_id: str 
    category: str 
    description: str 
    steps: tuple[BenchmarkStep, ...]


class BenchmarkSuite(BaseModel):
    """The suite aka the pipeline that contains the scenarios and the phase"""
    model_config = ConfigDict(frozen=True)
    suite_id: str 
    description: str 
    phase: str = Field(default="baseline", min_length=1)
    scenarios: tuple[BenchmarkScenario, ...]


class BenchmarkStepResult(BaseModel):
    """THe benchmark step result"""
    model_config = ConfigDict(frozen=True)
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
    expected_intent: str | None = None
    expected_route: str | None = None
    actual_intent: str | None = None
    actual_route: str | None = None
    final_answer: str | None = None
    duration_ms: float | None = None
    error: str | None = None


class BenchmarkRunReport(BaseModel):
    """The report that contains theresults of the steps """
    model_config = ConfigDict(frozen=True)
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
    results: tuple[BenchmarkStepResult, ...]
from pydantic import BaseModel, ConfigDict, Field


class EvaluationCase(BaseModel):
    """The base model for the evaluation case"""
    model_config = ConfigDict(extra="forbid", frozen=True)
    case_id: str = Field(min_length=1)
    input_query: str = Field(min_length=1)
    expected_output: str | None = None
    expected_route: str | None = None
    expected_intent: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class EvaluationSample(BaseModel):
    """The evalutaiton sample actually produced"""
    model_config = ConfigDict(extra="forbid", frozen=True)
    case: EvaluationCase
    actual_output: str
    actual_route: str | None = None
    actual_intent: str | None = None
    trace_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class EvaluationScore(BaseModel):
    """The base model for the score of the valuation, it contains the metric, the score and the reason"""
    model_config = ConfigDict(extra="forbid", frozen=True)
    metric: str = Field(min_length=1)
    score: float
    reason: str | None = None


class EvaluationCaseResult(BaseModel):
    """The result it actually contains the output and the different registered scores"""
    model_config = ConfigDict(extra="forbid", frozen=True)
    case_id: str
    actual_output: str
    scores: tuple[EvaluationScore, ...]


class EvaluationReport(BaseModel):
    """The base model fora basic report with the name of the framework used, the name of the exèeriment 
    and all the registered results"""
    model_config = ConfigDict(extra="forbid", frozen=True)
    framework: str
    experiment_name: str
    results: tuple[EvaluationCaseResult, ...]
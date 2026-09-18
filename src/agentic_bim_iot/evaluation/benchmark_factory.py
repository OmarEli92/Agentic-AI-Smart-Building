from __future__ import annotations

from agentic_bim_iot.config.settings import Settings
from agentic_bim_iot.evaluation.judge_model import create_evaluation_chat_model
from agentic_bim_iot.evaluation.protocols import BenchmarkMetricEvaluator, BenchmarkScorePublisher


def create_benchmark_evaluators(*, settings: Settings, enabled: set[str]) -> tuple[BenchmarkMetricEvaluator, ...]:
    evaluators: list[BenchmarkMetricEvaluator] = []
    if "deepeval" in enabled:
        from agentic_bim_iot.evaluation.deepeval_evaluator import DeepEvalBenchmarkEvaluator
        evaluators.append(DeepEvalBenchmarkEvaluator(create_evaluation_chat_model(settings)))
    if "ragas" in enabled:
        from agentic_bim_iot.evaluation.ragas_evaluator import RagasBenchmarkEvaluator
        evaluators.append(RagasBenchmarkEvaluator(settings))
    unknown = enabled - {"deepeval", "ragas"}
    if unknown:
        raise ValueError("Unsupported benchmark evaluator(s): " + ", ".join(sorted(unknown)))
    return tuple(evaluators)


def create_score_publisher(*, publish_langfuse_scores: bool) -> BenchmarkScorePublisher | None:
    if not publish_langfuse_scores:
        return None
    from agentic_bim_iot.evaluation.langfuse_scores import LangfuseBenchmarkScorePublisher
    return LangfuseBenchmarkScorePublisher()
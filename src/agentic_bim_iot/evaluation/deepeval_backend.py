from collections.abc import Sequence
from deepeval.metrics import ExactMatchMetric
from deepeval.test_case import LLMTestCase
from agentic_bim_iot.evaluation.models import EvaluationCaseResult, EvaluationReport, EvaluationSample, EvaluationScore


class DeepEvalEvaluationBackend:
    @property
    def name(self) -> str:
        return "deepeval"

    def evaluate(self, experiment_name: str, samples: Sequence[EvaluationSample]) -> EvaluationReport:
        results = []
        for sample in samples:
            scores = []
            if sample.case.expected_output is not None:
                metric = ExactMatchMetric(threshold=1.0, verbose_mode=False)
                test_case = LLMTestCase(input=sample.case.input_query, actual_output=sample.actual_output, expected_output=sample.case.expected_output)
                metric.measure(test_case)
                scores.append(EvaluationScore(metric="exact_match", score=float(metric.score or 0.0), reason=getattr(metric, "reason", None)))
            if sample.case.expected_route is not None:
                scores.append(EvaluationScore(metric="route_accuracy", score=1.0 if sample.actual_route == sample.case.expected_route else 0.0,))
            if sample.case.expected_intent is not None:
                scores.append(EvaluationScore(metric="intent_accuracy", score=1.0 if sample.actual_intent == sample.case.expected_intent else 0.0))
            results.append(EvaluationCaseResult(case_id=sample.case.case_id, actual_output=sample.actual_output, scores=tuple(scores)))

        return EvaluationReport(framework=self.name, experiment_name=experiment_name, results=tuple(results))
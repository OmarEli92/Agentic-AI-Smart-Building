from collections.abc import Sequence

from ragas.metrics.collections import DistanceMeasure, NonLLMStringSimilarity
from agentic_bim_iot.evaluation.models import EvaluationCaseResult, EvaluationReport, EvaluationSample, EvaluationScore


class RagasEvaluationBackend:
    def __init__(self) -> None:
        self._string_similarity = NonLLMStringSimilarity(distance_measure=DistanceMeasure.LEVENSHTEIN)

    @property
    def name(self) -> str:
        return "ragas"

    def evaluate(self, experiment_name: str, samples: Sequence[EvaluationSample]) -> EvaluationReport:
        results = []
        for sample in samples:
            scores = []
            if sample.case.expected_output is not None:
                result = self._string_similarity.score(reference=sample.case.expected_output, response=sample.actual_output)
                scores.append(EvaluationScore(metric="string_similarity", score=float(result.value), reason=getattr(result, "reason", None)))
            if sample.case.expected_route is not None:
                scores.append(EvaluationScore(metric="route_accuracy", score=1.0 if sample.actual_route == sample.case.expected_route else 0.0))
            if sample.case.expected_intent is not None:
                scores.append(EvaluationScore(metric="intent_accuracy",score=1.0 if sample.actual_intent == sample.case.expected_intent else 0.0))
            results.append(EvaluationCaseResult(case_id=sample.case.case_id, actual_output=sample.actual_output, scores=tuple(scores)))

        return EvaluationReport(framework=self.name, experiment_name=experiment_name, results=tuple(results))
from collections.abc import Sequence
from agentic_bim_iot.evaluation.models import EvaluationReport, EvaluationSample


class EvaluationDisabledError(RuntimeError):
    pass


class DisabledEvaluationBackend:
    """Just an empty implementation of the system without the evaluation layer"""
    @property
    def name(self) -> str:
        return "none"

    def evaluate(self, experiment_name: str, samples: Sequence[EvaluationSample]) -> EvaluationReport:
        raise EvaluationDisabledError("Evaluation is disabled. Configure EVALUATION_FRAMEWORK before running an evaluation experiment.")
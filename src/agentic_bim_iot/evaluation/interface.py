from collections.abc import Sequence
from typing import Protocol
from agentic_bim_iot.evaluation.models import EvaluationSample, EvaluationReport


class EvaluationBackend(Protocol):
    """The contract for the Evaluation backend that will be used for all the evaluation process"""
    
    @property
    def name(self) -> str:
        ...

    def evaluate(self, experiment_name: str, cases: Sequence[EvaluationSample]) -> EvaluationReport:
        ...
from agentic_bim_iot.config.settings import EvaluationFramework, Settings
from agentic_bim_iot.evaluation.interface import EvaluationBackend
from agentic_bim_iot.evaluation.none_backend import DisabledEvaluationBackend


class EvaluationBackendUnavailableError(RuntimeError):
    pass


def create_evaluation_backend(settings: Settings) -> EvaluationBackend:
    """Factory to create the selected evaluation backend.
    For now I have implemented langfuse, ragas, and deepeval as backend evaluation tools"""
    if settings.evaluation_framework == EvaluationFramework.NONE:
        return DisabledEvaluationBackend()
    ## LAANGFUSE
    if settings.evaluation_framework == EvaluationFramework.LANGFUSE:
        try:
            from agentic_bim_iot.evaluation.langfuse_backend import LangfuseEvaluationBackend
        except ModuleNotFoundError as exc:
            raise EvaluationBackendUnavailableError("Langfuse evaluation is selected but the Langfuse package is not installed.") from exc
        return LangfuseEvaluationBackend()
    ##DEEPEVAL
    if settings.evaluation_framework == EvaluationFramework.DEEPEVAL:
        try:
            from agentic_bim_iot.evaluation.deepeval_backend import DeepEvalEvaluationBackend
        except ModuleNotFoundError as exc:
            raise EvaluationBackendUnavailableError("DeepEval evaluation is selected but the DeepEval package is not installed.") from exc
        return DeepEvalEvaluationBackend()
    ##RAGAS
    if settings.evaluation_framework == EvaluationFramework.RAGAS:
        try:
            from agentic_bim_iot.evaluation.ragas_backend import RagasEvaluationBackend
        except ModuleNotFoundError as exc:
            raise EvaluationBackendUnavailableError("RAGAS evaluation is selected but the RAGAS package is not installed.") from exc
        return RagasEvaluationBackend()

    raise EvaluationBackendUnavailableError(f"Unsupported evaluation framework: {settings.evaluation_framework}")
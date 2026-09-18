from __future__ import annotations
from typing import Any
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel
from agentic_bim_iot.benchmark.models import BenchmarkExpectation, BenchmarkObservation, MetricResult


class DeepEvalBenchmarkEvaluator:

    def __init__(self, chat_model: BaseChatModel) -> None:
        try:
            from deepeval.models import DeepEvalBaseLLM
        except ModuleNotFoundError as exc:
            raise RuntimeError("DeepEval evaluation was requested but the 'deepeval' package is not installed.") from exc

        class LangChainDeepEvalModel(DeepEvalBaseLLM):
            def __init__(self, model: BaseChatModel) -> None:
                self._model = model


            def load_model(self) -> BaseChatModel:
                return self._model


            def generate(self, prompt: str, schema: type[BaseModel] | None = None) -> Any:
                model = self.load_model()
                if schema is not None:
                    return model.with_structured_output(schema).invoke(prompt)
                return _message_text(model.invoke(prompt))

            async def a_generate(self, prompt: str, schema: type[BaseModel] | None = None) -> Any:
                model = self.load_model()
                if schema is not None:
                    return await model.with_structured_output(schema).ainvoke(prompt)
                return _message_text(await model.ainvoke(prompt))


            def get_model_name(self) -> str:
                model_name = getattr(self._model, "model_name", None) or getattr(self._model, "model", None) or self._model.__class__.__name__
                return f"langchain:{model_name}"

        self._judge = LangChainDeepEvalModel(chat_model)

    @property
    def name(self) -> str:
        return "deepeval"

    def evaluate(self, *, query: str, expectation: BenchmarkExpectation, observation: BenchmarkObservation) -> tuple[MetricResult, ...]:
        if observation.error is not None or not observation.final_answer.strip():
            return ()

        try:
            from deepeval.metrics import AnswerRelevancyMetric, GEval, ToolCorrectnessMetric
            from deepeval.test_case import LLMTestCase, ToolCall
            try:
                from deepeval.test_case import SingleTurnParams
            except ImportError:
                from deepeval.test_case import LLMTestCaseParams as SingleTurnParams
        except ModuleNotFoundError as exc:
            raise RuntimeError("DeepEval evaluation was requested but the 'deepeval' package is not installed.") from exc

        results: list[MetricResult] = []
        base_case = LLMTestCase(input=query, actual_output=observation.final_answer)
        relevancy = AnswerRelevancyMetric(threshold=None, model=self._judge, include_reason=True, async_mode=False, verbose_mode=False)
        relevancy.measure(base_case)
        results.append(_metric_result(name="deepeval_answer_relevancy", score=relevancy.score, reason=relevancy.reason))
        if expectation.reference_answer:
            correctness_case = LLMTestCase(input=query, actual_output=observation.final_answer, expected_output=expectation.reference_answer,context=list(observation.retrieved_contexts))
            correctness =GEval(name="Smart Building Answer Correctness",
                criteria=(
                    "Evaluate whether the actual output is factually and "
                    "semantically correct relative to the expected output "
                    "and the provided context. "
                    "Equivalent wording is fully acceptable. "
                    "The expected output defines the essential facts that "
                    "should be present. "
                    "Do not penalize additional information when it is "
                    "factually supported by the provided context and does "
                    "not contradict the expected output. "
                    "Do not penalize harmless conversational text such as "
                    "an offer to help further. "
                    "Penalize missing essential facts, factual "
                    "contradictions, or claims unsupported by both the "
                    "expected output and the context."
                ),
                evaluation_params=[
                    SingleTurnParams.ACTUAL_OUTPUT,
                    SingleTurnParams.EXPECTED_OUTPUT,
                    SingleTurnParams.CONTEXT
                ],
                threshold=None,
                model=self._judge,
                async_mode=False,
                verbose_mode=False
            )
            correctness.measure(correctness_case)
            results.append(_metric_result(name="deepeval_answer_correctness", score=correctness.score, reason=correctness.reason))

        if observation.orchestration == "full_react" and expectation.required_tools:
            actual_tools = [ToolCall(name=tool.name) for tool in observation.tool_calls]
            expected_tools = [ToolCall(name=name) for name in expectation.required_tools]
            tool_case = LLMTestCase(input=query, actual_output=observation.final_answer, tools_called=actual_tools, expected_tools=expected_tools)
            tool_metric = ToolCorrectnessMetric(
                threshold=None, model=self._judge, include_reason=True, 
                strict_mode=False, should_exact_match=False, should_consider_ordering=False, verbose_mode=False
            )
            tool_metric.measure(tool_case)
            results.append(_metric_result(name="deepeval_tool_correctness", score=tool_metric.score, reason=tool_metric.reason))

        return tuple(results)


def _metric_result(*, name: str, score: Any, reason: str | None) -> MetricResult:
    return MetricResult(name=name, score=float(score or 0.0), passed=True, reason=reason)


def _message_text(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "\n".join(parts).strip()
    return str(content)
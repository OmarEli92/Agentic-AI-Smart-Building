from __future__ import annotations
import asyncio
from typing import Any

from agentic_bim_iot.benchmark.models import BenchmarkExpectation, BenchmarkObservation, MetricResult
from agentic_bim_iot.config.settings import LLMProvider, Settings
from agentic_bim_iot.evaluation.judge_model import resolve_evaluation_llm_config


class RagasBenchmarkEvaluator:
    name: str = "ragas"
    def __init__(self, settings: Settings) -> None:
        try:
            from openai import AsyncOpenAI
            from ragas.llms import llm_factory
            from ragas.metrics.collections import Faithfulness
        except ModuleNotFoundError as exc:
            raise RuntimeError("RAGAS evaluation was requested but 'ragas' and its OpenAI client dependency are not installed.") from exc

        config = resolve_evaluation_llm_config(settings)
        api_key = config.api_key.get_secret_value() if hasattr(config.api_key, "get_secret_value") else str(config.api_key)
        base_url = _openai_compatible_base_url(config.provider)
        client = AsyncOpenAI(api_key=api_key, base_url=base_url) if base_url else AsyncOpenAI(api_key=api_key)
        llm = llm_factory(config.model, provider="openai", client=client)
        self._faithfulness = Faithfulness(llm=llm)

   
    def evaluate(self, *, query: str, expectation: BenchmarkExpectation, observation: BenchmarkObservation) -> tuple[MetricResult, ...]:
        del expectation
        if observation.error is not None or not observation.final_answer.strip() or not observation.retrieved_contexts:
            return ()
        result = asyncio.run(self._faithfulness.ascore(
            user_input=query, response=observation.final_answer, retrieved_contexts=list(observation.retrieved_contexts)
        ))
        score = float(getattr(result, "value", result))
        return (MetricResult(name="ragas_faithfulness", score=score, passed=score >= 0.5, reason=getattr(result, "reason", None)),)


def _openai_compatible_base_url(provider: Any) -> str | None:
    value = getattr(provider, "value", provider)
    if value == LLMProvider.GROQ.value: return "https://api.groq.com/openai/v1"
    if value == LLMProvider.OPENROUTER.value: return "https://openrouter.ai/api/v1"
    return None
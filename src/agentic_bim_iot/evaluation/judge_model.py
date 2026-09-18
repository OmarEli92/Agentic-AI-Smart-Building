from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from langchain_core.language_models.chat_models import BaseChatModel
from agentic_bim_iot.config.settings import Settings
from agentic_bim_iot.infrastructure.llm.factory import create_chat_model


@dataclass(frozen=True, slots=True)
class EvaluationLLMConfig:
    provider: Any
    model: str
    api_key: Any


def create_evaluation_chat_model(settings: Settings) -> BaseChatModel:
    provider = getattr(settings, "evaluation_llm_provider", None) or settings.llm_provider
    model = getattr(settings, "evaluation_llm_model", None) or settings.llm_model
    api_key = getattr(settings, "evaluation_llm_api_key", None) or settings.llm_api_key
    evaluator_settings = settings.model_copy(
        update={
            "llm_provider": provider,
            "llm_model": model,
            "llm_api_key": api_key,
            "llm_temperature": 0.0,
        }
    )
    return create_chat_model(evaluator_settings)


def resolve_evaluation_llm_config(settings: Settings) -> EvaluationLLMConfig:
    return EvaluationLLMConfig(
        provider=getattr(settings, "evaluation_llm_provider", None) or settings.llm_provider,
        model=getattr(settings, "evaluation_llm_model", None) or settings.llm_model,
        api_key=getattr(settings, "evaluation_llm_api_key", None) or settings.llm_api_key,
    )

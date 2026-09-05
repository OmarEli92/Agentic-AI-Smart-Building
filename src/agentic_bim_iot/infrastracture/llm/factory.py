"""For managing the different LLM providers , i decided to opt for the Factory Design Pattern instead of
using classic interfaces, the reason is that langgraph already offer BaseChatModel which is a polymorfic abstraction that already manages the implementation
With the factory we have a linear representation of the provider that can we use (OpenROuter, GROQ, OpenaAI) with lighter codebase distraction aka less almost empty classes"""

from typing import Literal
from langchain_core.language_models.chat_models import BaseChatModel
from agentic_bim_iot.config.settings import LLMProvider, Settings


OpenRouterReasoningEffort = Literal[
    "xhigh",
    "high",
    "medium",
    "low",
    "minimal",
    "none",
]


def create_chat_model(settings: Settings,*,reasoning_effort: OpenRouterReasoningEffort | None = None) -> BaseChatModel:
    """The method is used to create the chat model based on
    the selected configuration. So the core is BaseChatModel."""
    match settings.llm_provider:
        case LLMProvider.GROQ:
            return _create_groq_model(settings)
        case LLMProvider.OPENAI:
            return _create_openai_model(settings)
        case LLMProvider.OPENROUTER:
            return _create_openrouter_model(
                settings,
                reasoning_effort=reasoning_effort
            )

    raise ValueError(f"The LLM provider: {settings.llm_provider} is not supported")


def _create_groq_model(settings: Settings) -> BaseChatModel:
    """Create an instance of the Chat GROQ model"""
    from langchain_groq import ChatGroq
    assert settings.llm_api_key is not None
    return ChatGroq(
        model=settings.llm_model,
        api_key=settings.llm_api_key.get_secret_value(),
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        max_retries=settings.llm_max_retries,
        timeout=settings.llm_timeout_seconds
    )


def _create_openai_model(settings: Settings) -> BaseChatModel:
    """Create an instance of the Chat OpenAI model"""
    from langchain_openai import ChatOpenAI
    assert settings.llm_api_key is not None
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key.get_secret_value(),
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        max_retries=settings.llm_max_retries,
        timeout=settings.llm_timeout_seconds
    )


def _create_openrouter_model(settings: Settings,*,reasoning_effort: OpenRouterReasoningEffort | None,) -> BaseChatModel:
    """Create an instance of the Chat OpenRouter model"""
    from langchain_openrouter import ChatOpenRouter
    assert settings.llm_api_key is not None
    reasoning = (
        {"effort": reasoning_effort}
        if reasoning_effort is not None
        else None
    )
    return ChatOpenRouter(
        model=settings.llm_model,
        api_key=settings.llm_api_key.get_secret_value(),
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        max_retries=settings.llm_max_retries,
        timeout=settings.llm_timeout_seconds * 1000,
        reasoning=reasoning,
        openrouter_provider={"require_parameters": True}
    )
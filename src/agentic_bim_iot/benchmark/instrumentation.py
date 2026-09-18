from __future__ import annotations
from threading import Lock
from typing import Any
from langchain_core.callbacks import BaseCallbackHandler


class BenchmarkCallbackHandler(BaseCallbackHandler):

    def __init__(self) -> None:
        self._lock = Lock()
        self.llm_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.tool_calls: list[str] = []


    def on_chat_model_start(self, serialized: dict[str, Any], messages: list[list[Any]], **kwargs: Any) -> None:
        del serialized, messages, kwargs
        with self._lock:
            self.llm_calls += 1


    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any) -> None:
        del serialized, prompts, kwargs
        with self._lock:
            self.llm_calls += 1


    def on_tool_start(self, serialized: dict[str, Any], input_str: str, **kwargs: Any) -> None:
        del input_str, kwargs
        name = str(serialized.get("name") or "unknown_tool")
        with self._lock:
            self.tool_calls.append(name)


    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        del kwargs
        usage = self._extract_usage(response)
        if usage is None:
            return
        input_tokens, output_tokens, total_tokens = usage
        with self._lock:
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.total_tokens += total_tokens


    @classmethod
    def _extract_usage(cls, response: Any) -> tuple[int, int, int] | None:
        llm_output = getattr(response, "llm_output", None)
        if isinstance(llm_output, dict):
            for key in ("token_usage", "usage", "usage_metadata"):
                raw = llm_output.get(key)
                parsed = cls._parse_usage_dict(raw)
                if parsed is not None:
                    return parsed
        generations = getattr(response, "generations", None)
        if isinstance(generations, list):
            for generation_group in generations:
                if not isinstance(generation_group, list):
                    continue
                for generation in generation_group:
                    message = getattr(generation, "message", None)
                    raw = getattr(message, "usage_metadata", None)
                    parsed = cls._parse_usage_dict(raw)
                    if parsed is not None:
                        return parsed
        return None


    @staticmethod
    def _parse_usage_dict(raw: Any) -> tuple[int, int, int] | None:
        if not isinstance(raw, dict):
            return None
        input_tokens = int(raw.get("input_tokens") or raw.get("prompt_tokens") or 0)
        output_tokens = int(raw.get("output_tokens") or raw.get("completion_tokens") or 0)
        total_tokens = int(raw.get("total_tokens") or input_tokens + output_tokens)
        if input_tokens == 0 and output_tokens == 0 and total_tokens == 0:
            return None
        return input_tokens, output_tokens, total_tokens

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any
from agentic_bim_iot.config.settings import ObservabilityBackend, Settings


@dataclass(slots=True)
class RequestTrace:
    callbacks: list[Any]
    observation: Any | None = None

    @property
    def trace_id(self) -> str | None:
        if self.observation is None:
            return None
        return getattr(self.observation, "trace_id", None)

    def set_output(self, output: object) -> None:
        if self.observation is not None:
            self.observation.update(output=output)


class ObservabilityRuntime:
    """The observability runtime used for tracking all the graph invocations, LLM calls, metadata and so on.
    The main objective is to wrap each User's interaction and create a LangFUse trace .
    IMPORTANT: The system can still run without any Observation Runtime at all, the configuration can be set directly
    from the settings file"""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None
        self._handler = None
        self._propagate_attributes = None
        if settings.observability_backend == ObservabilityBackend.LANGFUSE:
            from langfuse import get_client, propagate_attributes
            from langfuse.langchain import CallbackHandler

            self._client = get_client()
            self._handler = CallbackHandler()
            self._propagate_attributes = propagate_attributes

    @contextmanager
    def trace_request(self, *, request_id: str, session_id: str, user_query: str, trace_name: str = "agentic-smart-building-request", root_observation_name: str = "facility-manager-request", tags: list[str] | None = None, metadata: dict[str, object] | None = None) -> Iterator[RequestTrace]:
        if self._settings.observability_backend == ObservabilityBackend.NONE:
            yield RequestTrace(callbacks=[])
            return

        if self._client is None or self._handler is None or self._propagate_attributes is None:
            raise RuntimeError("Langfuse observability was selected but the Langfuse runtime was not initialized.")

        resolved_tags = ["agentic-smart-building", "langgraph", f"semantic-backend:{self._settings.semantic_backend.value}", f"actuator-strategy:{self._settings.actuator_resolution_strategy.value}", f"bim-cache:{self._settings.bim_cache_backend.value}"]
        if tags:
            resolved_tags.extend(tags)

        resolved_metadata: dict[str, str] = {
            "request_id": request_id,
            "app_env": self._settings.app_env,
            "semantic_backend": self._settings.semantic_backend.value,
            "actuator_resolution_strategy": self._settings.actuator_resolution_strategy.value,
            "bim_cache_backend": self._settings.bim_cache_backend.value,
        }
        if metadata:
            resolved_metadata.update({str(key): str(value) for key, value in metadata.items() if value is not None})
        with self._client.start_as_current_observation(as_type="span", name=root_observation_name, input={"user_query": user_query}) as observation:
            with self._propagate_attributes(trace_name=trace_name, session_id=session_id, tags=resolved_tags, metadata=resolved_metadata, environment=self._settings.app_env):
                yield RequestTrace(callbacks=[self._handler], observation=observation)

    def flush(self) -> None:
        if self._client is not None:
            self._client.flush()

    def shutdown(self) -> None:
        if self._client is not None:
            self._client.shutdown()
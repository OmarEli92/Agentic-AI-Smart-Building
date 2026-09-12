import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from langchain_core.runnables import RunnableConfig


class NoneObservation:
    def update(self, **kwargs: object) -> None:
        return None


def llm_run_config(component: str, operation: str, *, repair_attempt: bool = False, cache_hit: bool = False) -> RunnableConfig:
    tags = ["llm", f"component:{component}", f"operation:{operation}"]
    if repair_attempt:
        tags.append("repair")
    if cache_hit:
        tags.append("cache-hit")
    else:
        tags.append("cache-miss")

    return {
        "run_name": f"{component}.{operation}",
        "tags": tags,
        "metadata": {
            "component": component,
            "operation": operation,
            "repair_attempt": repair_attempt,
            "cache_hit": cache_hit,
        },
    }


@contextmanager
def trace_observation(name: str, *, as_type: str = "span", input_payload: object | None = None, metadata: dict[str, object] | None = None) -> Iterator[Any]:
    backend = os.getenv("OBSERVABILITY_BACKEND", "none").strip().casefold()
    if backend != "langfuse":
        yield NoneObservation()
        return
    from langfuse import get_client
    langfuse = get_client()
    with langfuse.start_as_current_observation(as_type=as_type, name=name,input=input_payload, metadata=metadata) as observation:
        try:
            yield observation
        except Exception as exc:
            observation.update( level="ERROR", status_message=str(exc))
            raise
from __future__ import annotations
from agentic_bim_iot.benchmark.models import MetricResult


class LangfuseBenchmarkScorePublisher:
    
    def __init__(self) -> None:
        try:
            from langfuse import get_client
        except ModuleNotFoundError as exc:
            raise RuntimeError("the langfuse package is not installed.") from exc
        self._client = get_client()

    def publish(self, *, trace_id: str | None, metrics: tuple[MetricResult, ...]) -> None:
        if not trace_id:
            return
        for metric in metrics:
            self._client.create_score(
                trace_id=trace_id,
                name=metric.name,
                value=float(metric.score),
                data_type="NUMERIC",
                comment=metric.reason
            )

        self._client.flush()
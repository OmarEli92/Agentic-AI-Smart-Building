from __future__ import annotations
from typing import Protocol
from agentic_bim_iot.benchmark.models import  BenchmarkExpectation, BenchmarkObservation, MetricResult


class BenchmarkMetricEvaluator(Protocol):

    @property
    def name(self) -> str:
        ...

    def evaluate(self, *, query: str, expectation: BenchmarkExpectation, observation: BenchmarkObservation) -> tuple[MetricResult, ...]:
        ...


class BenchmarkScorePublisher(Protocol):

    def publish(self, *, trace_id: str | None, metrics: tuple[MetricResult, ...]) -> None:
        ...

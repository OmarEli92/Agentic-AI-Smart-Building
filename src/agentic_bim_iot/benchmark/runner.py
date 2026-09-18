from __future__ import annotations
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
import traceback
from uuid import uuid4
from agentic_bim_iot.benchmark.inspection import BenchmarkResultInspector
from agentic_bim_iot.benchmark.instrumentation import BenchmarkCallbackHandler
from agentic_bim_iot.benchmark.models import BenchmarkMode, BenchmarkObservation, BenchmarkRunReport, BenchmarkScenario, BenchmarkStep, BenchmarkStepResult, BenchmarkStepStatus, BenchmarkSuite
from agentic_bim_iot.bootstrap import create_runtime
from agentic_bim_iot.config.settings import Settings
from agentic_bim_iot.evaluation.aggregate import build_benchmark_summary
from agentic_bim_iot.evaluation.metrics import DeterministicEvaluator
from agentic_bim_iot.evaluation.protocols import  BenchmarkMetricEvaluator, BenchmarkScorePublisher
from agentic_bim_iot.infrastructure.observability.runtime import ObservabilityRuntime


class BenchmarkRunner:

    def __init__(self, settings: Settings, observability: ObservabilityRuntime, *, optional_evaluators: tuple[BenchmarkMetricEvaluator, ...] = (),
                 score_publisher: BenchmarkScorePublisher | None = None) -> None:
        self._settings = settings
        self._observability = observability
        self._inspector = BenchmarkResultInspector()
        self._evaluator = DeterministicEvaluator()
        self._optional_evaluators = optional_evaluators
        self._score_publisher = score_publisher


    def run(self, *, suite: BenchmarkSuite, suite_sha256: str, mode: BenchmarkMode, repetitions: int = 1,
        selected_scenarios: set[str] | None = None, output_directory: str = "benchmarks_result") -> BenchmarkRunReport:
        if repetitions < 1:
            raise ValueError("Benchmark repetitions must be at least 1.")
        benchmark_id = self._create_benchmark_id(suite.suite_id)
        started_at = datetime.now(timezone.utc)
        runtime_settings = self._create_isolated_settings(benchmark_id=benchmark_id, output_directory=output_directory)
        scenarios = [scenario for scenario in suite.scenarios if selected_scenarios is None or scenario.scenario_id in selected_scenarios]
        if not scenarios:
            raise ValueError("No benchmark scenarios were selected.")
        results: list[BenchmarkStepResult] = []
        for iteration in range(1, repetitions + 1):
            #The warm mode(sistema già avviato) 
            if mode == BenchmarkMode.WARM:
                with create_runtime(runtime_settings) as runtime:
                    for scenario in scenarios:
                        results.extend(
                            self._run_scenario(
                                runtime=runtime,
                                benchmark_id=benchmark_id,
                                suite=suite,
                                scenario=scenario,
                                iteration=iteration,
                                mode=mode,
                                orchestration=self._orchestration_name(runtime_settings)
                            )
                        )
            else:
                #Cold mode(sistema appena avviato) isolated cases
                for scenario in scenarios:
                    with create_runtime(runtime_settings) as runtime:
                        results.extend(
                            self._run_scenario(
                                runtime=runtime,
                                benchmark_id=benchmark_id,
                                suite=suite,
                                scenario=scenario,
                                iteration=iteration,
                                mode=mode,
                                orchestration=self._orchestration_name(runtime_settings)
                            )
                        )
        completed_at = datetime.now(timezone.utc)
        summary = build_benchmark_summary(results)
        report = BenchmarkRunReport(
            benchmark_id=benchmark_id,
            suite_id=suite.suite_id,
            suite_sha256=suite_sha256,
            phase=suite.phase,
            mode=mode,
            repetitions=repetitions,
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            git_commit=self._resolve_git_commit(),
            configuration=self._configuration(runtime_settings),
            summary=summary,
            results=tuple(results)
        )
        self._save_report(report=report, output_directory=output_directory)
        return report

    def _run_scenario(self, *, runtime, benchmark_id: str, suite: BenchmarkSuite, scenario: BenchmarkScenario,
                      iteration: int, mode: BenchmarkMode, orchestration: str) -> list[BenchmarkStepResult]:
        results: list[BenchmarkStepResult] = []
        previous_step_failed = False
        session_id = f"{benchmark_id}:{iteration}:{scenario.scenario_id}"
        for step in scenario.steps:
            if previous_step_failed:
                results.append(
                    self._build_skipped_result(
                        benchmark_id=benchmark_id,
                        suite=suite,
                        scenario=scenario,
                        step=step,
                        iteration=iteration,
                        mode=mode,
                        orchestration=orchestration
                    )
                )
                continue
            result = self._run_step(
                runtime=runtime,
                benchmark_id=benchmark_id,
                suite=suite,
                scenario=scenario,
                step=step,
                iteration=iteration,
                mode=mode,
                session_id=session_id,
                orchestration=orchestration
            )
            results.append(result)
            if result.status == BenchmarkStepStatus.FAILED:
                previous_step_failed = True
        return results



    def _run_step(self, *, runtime, benchmark_id: str, suite: BenchmarkSuite, scenario: BenchmarkScenario, step: BenchmarkStep, iteration: int, mode: BenchmarkMode, session_id: str, orchestration: str) -> BenchmarkStepResult:
        request_id = str(uuid4())
        started_at_ns = time.perf_counter_ns()
        trace_id: str | None = None
        callback = BenchmarkCallbackHandler()
        try:
            with self._observability.trace_request(
                request_id=request_id, session_id=session_id, user_query=step.query, trace_name="agentic-smart-building-benchmark",
                tags=["benchmark", f"benchmark:{benchmark_id}", f"suite:{suite.suite_id}", f"scenario:{scenario.scenario_id}", f"category:{scenario.category}", f"mode:{mode.value}", f"phase:{suite.phase}", f"orchestration:{orchestration}"],
                metadata={"benchmark_id": benchmark_id, "benchmark_suite": suite.suite_id, "benchmark_phase": suite.phase, "benchmark_mode": mode.value, "benchmark_scenario": scenario.scenario_id, "benchmark_category": scenario.category, "benchmark_step": step.step_id, "benchmark_iteration": iteration, **step.metadata},
            ) as trace:  
                trace_id = trace.trace_id
                result = runtime.graph.invoke(
                    {"user_query": step.query},
                    config={
                        "callbacks": [*trace.callbacks, callback],
                        "run_name": "agentic-smart-building-benchmark-run",
                        "configurable": {"thread_id": session_id},
                        "metadata": {"request_id": request_id, "benchmark_id": benchmark_id, "scenario_id": scenario.scenario_id, "step_id": step.step_id, "iteration": iteration, "orchestration": orchestration}
                    }
                )
                duration_ms = (time.perf_counter_ns() - started_at_ns) / 1_000_000
                observation = self._inspector.inspect(result=result, runtime=runtime, orchestration=orchestration, duration_ms=duration_ms, callback=callback)
                metrics, evaluation_errors = self._evaluate_step(query=step.query, expectation=step.expected, observation=observation)
                if self._score_publisher is not None:
                    try:
                        self._score_publisher.publish(trace_id=trace_id, metrics=metrics)
                    except Exception as exc:
                        evaluation_errors = (*evaluation_errors, f"langfuse-score-publisher: {exc}")

                trace.set_output({
                    "final_answer": observation.final_answer,
                    "task_success": self._metric_score(metrics, "task_success"),
                    "duration_ms": duration_ms,
                    "llm_calls": observation.llm_calls,
                    "total_tokens": observation.total_tokens,
                    "tool_calls": [tool.name for tool in observation.tool_calls],
                    "retrieved_contexts": list(observation.retrieved_contexts),
                    "evaluation_errors": list(evaluation_errors)
                })

            return BenchmarkStepResult(
                benchmark_id=benchmark_id, suite_id=suite.suite_id, scenario_id=scenario.scenario_id, category=scenario.category,
                step_id=step.step_id, iteration=iteration, mode=mode, status=BenchmarkStepStatus.SUCCEEDED, request_id=request_id,
                trace_id=trace_id, query=step.query, expectation=step.expected, observation=observation, metrics=metrics, evaluation_errors=evaluation_errors
            )

        except Exception as exc:
            duration_ms = (time.perf_counter_ns() - started_at_ns) / 1_000_000
            traceback_text = traceback.format_exc()
            print(f"\n{'=' * 80}\nBENCHMARK STEP FAILED\n{'=' * 80}")
            print(f"Scenario: {scenario.scenario_id}\nStep:     {step.step_id}\nQuery:    {step.query}\n\n{traceback_text}\n{'=' * 80}\n")
            observation = self._inspector.failed(orchestration=orchestration, duration_ms=duration_ms, callback=callback, error=RuntimeError(traceback_text))
            metrics = self._evaluator.evaluate(expectation=step.expected, observation=observation)
            return BenchmarkStepResult(
                benchmark_id=benchmark_id, suite_id=suite.suite_id, scenario_id=scenario.scenario_id, category=scenario.category,
                step_id=step.step_id, iteration=iteration, mode=mode, status=BenchmarkStepStatus.FAILED, request_id=request_id,
                trace_id=trace_id, query=step.query, expectation=step.expected, observation=observation, metrics=metrics,
            )
        finally:
            self._observability.flush()



    def _evaluate_step(self, *, query: str, expectation, observation: BenchmarkObservation) -> tuple[tuple, tuple[str, ...]]:
        metrics = list(self._evaluator.evaluate(expectation=expectation, observation=observation))
        errors: list[str] = []
        for evaluator in self._optional_evaluators:
            try:
                metrics.extend(evaluator.evaluate(query=query, expectation=expectation, observation=observation))
            except Exception as exc:
                errors.append(f"{evaluator.name}: {exc}")
        return tuple(metrics), tuple(errors)



    def _create_isolated_settings(self, *, benchmark_id: str, output_directory: str) -> Settings:
        runtime_directory = Path(output_directory) / "runtime" / benchmark_id
        runtime_directory.mkdir(parents=True, exist_ok=True)
        return self._settings.model_copy(
            update={
                "proposal_database_path": str(runtime_directory / "proposals.db"),
                "execution_database_path": str(runtime_directory / "executions.db"),
                "notification_database_path": str(runtime_directory / "notifications.db"),
            }
        )



    @staticmethod
    def _build_skipped_result(*, benchmark_id: str, suite: BenchmarkSuite, scenario: BenchmarkScenario,
                              step: BenchmarkStep, iteration: int, mode: BenchmarkMode, orchestration: str) -> BenchmarkStepResult:
        observation = BenchmarkObservation(orchestration=orchestration, error="Skipped because a previous step in the same scenario failed.")
        return BenchmarkStepResult(
            benchmark_id=benchmark_id,
            suite_id=suite.suite_id,
            scenario_id=scenario.scenario_id,
            category=scenario.category,
            step_id=step.step_id,
            iteration=iteration,
            mode=mode,
            status=BenchmarkStepStatus.SKIPPED,
            query=step.query,
            expectation=step.expected,
            observation=observation,
            metrics=()
        )


    @staticmethod
    def _create_benchmark_id(suite_id: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        suffix = uuid4().hex[:8]
        return f"{suite_id}-{timestamp}-{suffix}"



    @staticmethod
    def _resolve_git_commit() -> str | None:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip() or None
        except (subprocess.SubprocessError, FileNotFoundError):
            return None



    @staticmethod
    def _save_report(*, report: BenchmarkRunReport, output_directory: str) -> None:
        directory = Path(output_directory)
        directory.mkdir(parents=True, exist_ok=True)
        output_path = directory / f"{report.benchmark_id}.json"
        output_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    @staticmethod
    def _orchestration_name(settings: Settings) -> str:
        value = getattr(settings, "agent_orchestration", "workflow")
        return str(getattr(value, "value", value))



    @staticmethod
    def _configuration(settings: Settings) -> dict[str, object]:
        def configured(name: str) -> object | None:
            value = getattr(settings, name, None)
            return getattr(value, "value", value)
        return {
            "app_env": configured("app_env"),
            "llm_provider": configured("llm_provider"),
            "llm_model": configured("llm_model"),
            "llm_temperature": configured("llm_temperature"),
            "semantic_backend": configured("semantic_backend"),
            "actuator_resolution_strategy": configured("actuator_resolution_strategy"),
            "agent_orchestration": configured("agent_orchestration") or "workflow",
            "thingsboard_integration": configured("thingsboard_integration"),
            "thingsboard_actuation_backend": configured("thingsboard_actuation_backend"),
            "bim_cache_backend": configured("bim_cache_backend"),
            "observability_backend": configured("observability_backend"),
        }


    @staticmethod
    def _metric_score(metrics, name: str) -> float | None:
        for metric in metrics:
            if metric.name == name:
                return metric.score
        return None

import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from agentic_bim_iot.benchmark.models import BenchmarkMode, BenchmarkRunReport, BenchmarkScenario, BenchmarkStep, BenchmarkStepResult, BenchmarkStepStatus, BenchmarkSuite
from agentic_bim_iot.bootstrap import create_application
from agentic_bim_iot.config.settings import Settings
from agentic_bim_iot.infrastracture.observability.runtime import ObservabilityRuntime


class BenchmarkRunner:
    """The starting point for the benchmark runs over predefined facility management scenarios.
    It handles execution (warm/cold modes) and the isolation of the state amongs different executions.
    """
    def __init__(self, settings: Settings, observability: ObservabilityRuntime) -> None:
        self._settings = settings
        self._observability = observability

    def run(self, *, suite: BenchmarkSuite, suite_sha256: str, mode: BenchmarkMode, repetitions: int = 1,
            selected_scenarios: set[str] | None = None, output_directory: str = "benchmark_results") -> BenchmarkRunReport:
        if repetitions < 1:
            raise ValueError("Benchmark repetitions must be at least 1.")
        benchmark_id = self._create_benchmark_id(suite.suite_id)
        started_at = datetime.now(timezone.utc)
        runtime_settings = self._create_isolated_settings(benchmark_id=benchmark_id, output_directory=output_directory)
        results: list[BenchmarkStepResult] = []
        scenarios = [scenario for scenario in suite.scenarios if selected_scenarios is None or scenario.scenario_id in selected_scenarios]
        if not scenarios:
            raise ValueError("No benchmark scenarios were selected.")
        for iteration in range(1, repetitions + 1):
            if mode == BenchmarkMode.WARM:
                with create_application(runtime_settings) as graph:
                    for scenario in scenarios:
                        results.extend(
                            self._run_scenario(
                                graph=graph,
                                benchmark_id=benchmark_id,
                                suite=suite,
                                scenario=scenario,
                                iteration=iteration,
                                mode=mode,
                            )
                        )
            else:
                for scenario in scenarios:
                    with create_application(runtime_settings) as graph:
                        results.extend(
                            self._run_scenario(
                                graph=graph,
                                benchmark_id=benchmark_id,
                                suite=suite,
                                scenario=scenario,
                                iteration=iteration,
                                mode=mode,
                            )
                        )
        completed_at = datetime.now(timezone.utc)
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
            configuration={
                "app_env": runtime_settings.app_env,
                "llm_provider": runtime_settings.llm_provider.value,
                "llm_model": runtime_settings.llm_model,
                "semantic_backend": runtime_settings.semantic_backend.value,
                "actuator_resolution_strategy": runtime_settings.actuator_resolution_strategy.value,
                "observability_backend": runtime_settings.observability_backend.value,
                "evaluation_framework": runtime_settings.evaluation_framework.value,
                "proposal_database_path": runtime_settings.proposal_database_path,
                "execution_database_path": runtime_settings.execution_database_path,
            },
            results=tuple(results)
        )
        self._save_report(report=report, output_directory=output_directory,)
        return report

    def _run_scenario(self, *, graph, benchmark_id: str, suite: BenchmarkSuite, scenario: BenchmarkScenario,
                     iteration: int, mode: BenchmarkMode) -> list[BenchmarkStepResult]:
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
                        mode=mode
                    )
                )
                continue
            result = self._run_step(
                graph=graph,
                benchmark_id=benchmark_id,
                suite=suite,
                scenario=scenario,
                step=step,
                iteration=iteration,
                mode=mode,
                session_id=session_id
            )
            results.append(result)
            if result.status == BenchmarkStepStatus.FAILED:
                previous_step_failed = True
        return results

    def _run_step(self, *, graph, benchmark_id: str, suite: BenchmarkSuite, scenario: BenchmarkScenario, step: BenchmarkStep, 
                  iteration: int, mode: BenchmarkMode, session_id: str) -> BenchmarkStepResult:
        request_id = str(uuid4())
        started_at_ns = time.perf_counter_ns()
        trace_id = None
        try:
            with self._observability.trace_request(
                request_id=request_id,
                session_id=session_id,
                user_query=step.query,
                trace_name="agentic-smart-building-benchmark",
                tags=[
                    "benchmark",
                    f"benchmark:{benchmark_id}",
                    f"suite:{suite.suite_id}",
                    f"scenario:{scenario.scenario_id}",
                    f"category:{scenario.category}",
                    f"mode:{mode.value}",
                    f"phase:{suite.phase}",
                ],
                metadata={
                    "benchmark_id": benchmark_id,
                    "benchmark_suite": suite.suite_id,
                    "benchmark_phase": suite.phase,
                    "benchmark_mode": mode.value,
                    "benchmark_scenario": scenario.scenario_id,
                    "benchmark_category": scenario.category,
                    "benchmark_step": step.step_id,
                    "benchmark_iteration": iteration,
                    "expected_intent": step.expected_intent,
                    "expected_route": step.expected_route,
                    **step.metadata,
                }
            ) as trace:
                trace_id = trace.trace_id
                result = graph.invoke(
                    {"user_query": step.query},
                    config={
                        "callbacks": trace.callbacks,
                        "run_name": "agentic-smart-building-graph",
                        "metadata": {
                            "request_id": request_id,
                            "benchmark_id": benchmark_id,
                            "scenario_id": scenario.scenario_id,
                            "step_id": step.step_id,
                        }
                    }
                )
                duration_ms = (time.perf_counter_ns() - started_at_ns) / 1_000_000
                decision = result.get("supervisor_decision")
                actual_intent = decision.intent.value if decision is not None else None
                actual_route = decision.route.value if decision is not None else None
                final_answer = result.get("final_answer", "")
                trace.set_output(
                    {
                        "final_answer": final_answer,
                        "actual_intent": actual_intent,
                        "actual_route": actual_route,
                    }
                )
            return BenchmarkStepResult(
                benchmark_id=benchmark_id,
                suite_id=suite.suite_id,
                scenario_id=scenario.scenario_id,
                category=scenario.category,
                step_id=step.step_id,
                iteration=iteration,
                mode=mode,
                status=BenchmarkStepStatus.SUCCEEDED,
                request_id=request_id,
                trace_id=trace_id,
                query=step.query,
                expected_intent=step.expected_intent,
                expected_route=step.expected_route,
                actual_intent=actual_intent,
                actual_route=actual_route,
                final_answer=final_answer,
                duration_ms=duration_ms,
                error=None
            )

        except Exception as exc:
            duration_ms = (time.perf_counter_ns() - started_at_ns) / 1_000_000
            return BenchmarkStepResult(
                benchmark_id=benchmark_id,
                suite_id=suite.suite_id,
                scenario_id=scenario.scenario_id,
                category=scenario.category,
                step_id=step.step_id,
                iteration=iteration,
                mode=mode,
                status=BenchmarkStepStatus.FAILED,
                request_id=request_id,
                trace_id=trace_id,
                query=step.query,
                expected_intent=step.expected_intent,
                expected_route=step.expected_route,
                actual_intent=None,
                actual_route=None,
                final_answer=None,
                duration_ms=duration_ms,
                error=str(exc)
            )
        finally:
            self._observability.flush()


    def _create_isolated_settings(self, *, benchmark_id: str, output_directory: str) -> Settings:
        """It's necessary to isolate the different executions and saves on the db"""
        runtime_directory = Path(output_directory) / "runtime" / benchmark_id
        runtime_directory.mkdir(parents=True, exist_ok=True)
        proposal_database_path = runtime_directory / "proposals.db"
        execution_database_path = runtime_directory / "executions.db"
        return self._settings.model_copy(
            update={
                "proposal_database_path": str(proposal_database_path),
                "execution_database_path": str(execution_database_path),
            }
        )

    @staticmethod
    def _build_skipped_result(*, benchmark_id: str, suite: BenchmarkSuite, scenario: BenchmarkScenario,
                             step: BenchmarkStep, iteration: int, mode: BenchmarkMode) -> BenchmarkStepResult:
        """Build a standard result for the steps that weren't executed"""
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
            expected_intent=step.expected_intent,
            expected_route=step.expected_route,
            error="Skipped because a previous step in the same scenario failed."
        )

    @staticmethod
    def _create_benchmark_id(suite_id: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        suffix = uuid4().hex[:8]
        return f"{suite_id}-{timestamp}-{suffix}"

    @staticmethod
    def _resolve_git_commit() -> str | None:
        """Just to keep the benchamark resolved linked to the version of the system, in case the system
        evolve important internal features so we keep on track also that"""
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
        output_path.write_text(report.model_dump_json(indent=2),encoding="utf-8")
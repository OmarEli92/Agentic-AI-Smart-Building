from __future__ import annotations
import argparse
from dotenv import load_dotenv
from agentic_bim_iot.benchmark.loader import load_benchmark_suite
from agentic_bim_iot.benchmark.models import BenchmarkMode
from agentic_bim_iot.benchmark.runner import BenchmarkRunner
from agentic_bim_iot.config.settings import get_settings
from agentic_bim_iot.evaluation.benchmark_factory import create_benchmark_evaluators, create_score_publisher
from agentic_bim_iot.infrastructure.observability.logging_config import configure_application_logging
from agentic_bim_iot.infrastructure.observability.runtime import ObservabilityRuntime


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run reproducible evaluations against the Agentic Smart Building application.")
    parser.add_argument(
        "--suite",
        default="benchmarks/core_evaluation_v2.json",
        help="Path to the benchmark suite JSON file.",
    )
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in BenchmarkMode],
        default=BenchmarkMode.COLD.value,
        help="Cold recreates the app per scenario; warm reuses one runtime.",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of complete benchmark repetitions.",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        dest="scenarios",
        help="Run only a selected scenario; may be provided multiple times.",
    )
    parser.add_argument(
        "--orchestration",
        choices=["workflow", "full_react"],
        default=None,
        help="Optionally override AGENT_ORCHESTRATION for this run.",
    )
    parser.add_argument(
        "--output-directory",
        default="benchmarks_result",
        help="Directory used to store evaluation reports.",
    )
    parser.add_argument(
        "--evaluator",
        action="append",
        choices=["deepeval", "ragas"],
        default=[],
        help=(
            "Optional semantic evaluator. May be repeated, e.g. "
            "--evaluator deepeval --evaluator ragas. "
            "Deterministic metrics are always enabled."
        ),
    )
    parser.add_argument(
        "--publish-langfuse-scores",
        action="store_true",
        help="Attach computed benchmark metrics to the corresponding Langfuse trace.",
    )
    args = parser.parse_args()

    settings = get_settings()
    if args.orchestration is not None:
        current = getattr(settings, "agent_orchestration", None)
        if current is None:
            raise RuntimeError(
                "--orchestration requires the AgentOrchestration setting added for the Workflow/Full-ReAct configuration."
            )
        enum_type = type(current)
        settings = settings.model_copy(
            update={"agent_orchestration": enum_type(args.orchestration)}
        )

    configure_application_logging(
        log_file_path=settings.log_file_path,
        level=settings.log_level,
    )

    suite, suite_sha256 = load_benchmark_suite(args.suite)
    observability = ObservabilityRuntime(settings=settings)
    optional_evaluators = create_benchmark_evaluators(
        settings=settings,
        enabled=set(args.evaluator),
    )
    score_publisher = create_score_publisher(
        publish_langfuse_scores=args.publish_langfuse_scores,
    )
    runner = BenchmarkRunner(
        settings=settings,
        observability=observability,
        optional_evaluators=optional_evaluators,
        score_publisher=score_publisher,
    )

    try:
        report = runner.run(
            suite=suite,
            suite_sha256=suite_sha256,
            mode=BenchmarkMode(args.mode),
            repetitions=args.repeat,
            selected_scenarios=set(args.scenarios) if args.scenarios else None,
            output_directory=args.output_directory,
        )
    finally:
        observability.shutdown()

    print()
    print("=" * 72)
    print("EVALUATION COMPLETED")
    print("=" * 72)
    print(f"Benchmark ID:           {report.benchmark_id}")
    print(f"Suite:                  {report.suite_id}")
    print(f"Mode:                   {report.mode.value}")
    print(f"Repetitions:            {report.repetitions}")
    print(f"Task success rate:      {_pct(report.summary.task_success_rate)}")
    print(f"Technical failure rate: {_pct(report.summary.technical_failure_rate)}")
    print(f"Unsafe actuation rate:  {_pct(report.summary.unsafe_actuation_rate)}")
    print(f"Approval bypass rate:   {_pct(report.summary.approval_bypass_rate)}")
    print(f"Mean latency:           {_number(report.summary.mean_latency_ms, ' ms')}")
    print(f"P95 latency:            {_number(report.summary.p95_latency_ms, ' ms')}")
    print(f"Mean LLM calls:         {_number(report.summary.mean_llm_calls)}")
    print(f"Mean tokens:            {_number(report.summary.mean_total_tokens)}")
    print(f"Mean tool calls:        {_number(report.summary.mean_tool_calls)}")
    if report.summary.metric_means:
        print("Additional metric means:")
        for name, value in report.summary.metric_means.items():
            if name.startswith("deepeval_") or name.startswith("ragas_"):
                print(f"  {name:<31} {value:.4f}")
    print(f"Suite SHA256:           {report.suite_sha256}")
    print("=" * 72)


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.2f}%"


def _number(value: float | None, suffix: str = "") -> str:
    return "n/a" if value is None else f"{value:.2f}{suffix}"


if __name__ == "__main__":
    main()

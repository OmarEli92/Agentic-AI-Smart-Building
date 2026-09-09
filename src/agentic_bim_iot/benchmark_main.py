import argparse

from dotenv import load_dotenv

from agentic_bim_iot.benchmark.loader import load_benchmark_suite
from agentic_bim_iot.benchmark.models import BenchmarkMode
from agentic_bim_iot.benchmark.runner import BenchmarkRunner
from agentic_bim_iot.config.settings import get_settings
from agentic_bim_iot.infrastracture.observability.logging_config import configure_application_logging
from agentic_bim_iot.infrastracture.observability.runtime import ObservabilityRuntime


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run reproducible benchmarks against the Agentic Smart Building application.")
    parser.add_argument("--suite", default="benchmarks/baseline.json", help="Path to the benchmark suite JSON file.")
    parser.add_argument("--mode", choices=[mode.value for mode in BenchmarkMode], default=BenchmarkMode.COLD.value, help="Benchmark cache mode.")
    parser.add_argument("--repeat", type=int, default=1, help="Number of complete benchmark repetitions.")
    parser.add_argument("--scenario", action="append", dest="scenarios", help="Run only the selected scenario. Can be specified multiple times.")
    parser.add_argument("--output-directory", default="benchmark_results", help="Directory used to store benchmark reports.")
    args = parser.parse_args()
    settings = get_settings()
    configure_application_logging(log_file_path=settings.log_file_path, level=settings.log_level)
    suite, suite_sha256 = load_benchmark_suite(args.suite)
    observability = ObservabilityRuntime(settings=settings)
    runner = BenchmarkRunner(settings=settings, observability=observability)
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

    succeeded = sum(result.status.value == "succeeded" for result in report.results)
    failed = sum(result.status.value == "failed" for result in report.results)
    skipped = sum(result.status.value == "skipped" for result in report.results)

    print()
    print("=" * 70)
    print("BENCHMARK COMPLETED")
    print("=" * 70)
    print(f"Benchmark ID: {report.benchmark_id}")
    print(f"Suite:        {report.suite_id}")
    print(f"Mode:         {report.mode.value}")
    print(f"Repetitions:  {report.repetitions}")
    print(f"Succeeded:    {succeeded}")
    print(f"Failed:       {failed}")
    print(f"Skipped:      {skipped}")
    print(f"Suite SHA256: {report.suite_sha256}")
    print("=" * 70)


if __name__ == "__main__":
    main()
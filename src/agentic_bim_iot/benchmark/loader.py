import hashlib
from pathlib import Path
from agentic_bim_iot.benchmark.models import BenchmarkSuite


def load_benchmark_suite(file_path: str) -> tuple[BenchmarkSuite, str]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Benchmark suite not found: {file_path}")
    raw_content = path.read_bytes()
    #in order to keep the traceability of the test it create a hash of the file
    suite_sha256 = hashlib.sha256(raw_content).hexdigest()
    suite = BenchmarkSuite.model_validate_json(raw_content.decode("utf-8"))
    return suite, suite_sha256
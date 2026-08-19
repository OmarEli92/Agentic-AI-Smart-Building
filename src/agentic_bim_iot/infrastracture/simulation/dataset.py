import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True,slots=True)
class TelemetrySample:
    """Single measurement contained in the original dataset."""
    original_timestamp: str
    value: float


@dataclass(frozen=True,slots=True)
class TelemetrySeries:
    """Time series associated with one room and one measurement."""
    room_reference: str
    measurement: str
    samples: tuple[TelemetrySample, ...]
    source_name: str


def load_osh_measurements(dataset_dir: Path) -> list[TelemetrySeries]:
    """
    Load indoor telemetry series from the OpenSmartHome dataset.
    It becomes lki this:
    room_reference = "Kitchen"
    measurement = "temperature"
    """

    if not dataset_dir.is_dir():
        raise FileNotFoundError(f"Telemetry dataset not found: {dataset_dir}")
    series: list[TelemetrySeries] = []
    for path in sorted(dataset_dir.glob("*.csv")):
        if path.stem.startswith("OSH_"):
            continue
        try:
            room_token, measurement_token = (path.stem.rsplit("_", 1))
        except ValueError:
            print(f"Skipping unsupported file: {path.name}")
            continue
        room_reference = (room_token.replace("_", " ").strip())
        measurement = (measurement_token.strip().casefold())
        samples = _read_samples(path)
        if not samples:
            print(f"Skipping empty telemetry file: {path.name}")
            continue
        series.append(TelemetrySeries(room_reference=room_reference,measurement=measurement,samples=tuple(samples),source_name=path.name))
    return series


def _read_samples(path: Path) -> list[TelemetrySample]:
    """
    Read the original time/value format.
    All the invalid rows and header rows are ignored.
    """
    samples: list[TelemetrySample] = []
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.reader(file, delimiter="\t",)
        for row in reader:
            if len(row) < 2:
                continue
            original_timestamp = (row[0].strip())
            raw_value = (row[-1].strip())
            try:
                value = float(raw_value)
            except ValueError:
                continue
            samples.append(TelemetrySample(original_timestamp=(original_timestamp),value=value ))
    return samples
from enum import StrEnum
from typing import Final
from pydantic import BaseModel, ConfigDict


COMFORT_MEASUREMENTS: Final[tuple[str, ...]] = (
    "temperature",
    "humidity",
    "brightness",
)

COMFORT_RANGES: Final[dict[str, tuple[float, float]]] = {
    "temperature": (20.0, 26.0),
    "humidity": (30.0, 60.0),
    "brightness": (100.0, 300.0),
}

MEASUREMENT_UNITS: Final[dict[str, str]] = {
    "temperature": "°C",
    "humidity": "%",
    "brightness": "lux",
}


class ComfortLabel(StrEnum):
    COMFORTABLE = "Comfortable"
    MODERATE = "Moderate"
    UNCOMFORTABLE = "Uncomfortable"


class ParameterComfortAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    measurement: str
    value: float | None
    unit: str
    minimum: float
    maximum: float
    score: int
    within_range: bool | None
    sensor_guid: str | None = None
    timestamp_ms: int | None = None


class ComfortAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    room_reference: str
    total_score: int
    label: ComfortLabel
    parameters: dict[str, ParameterComfortAssessment]
    data_complete: bool
    missing_measurements: tuple[str, ...]
    evaluated_at_ms: int


def score_parameter(measurement: str, value: float | None,) -> int:
    """Calculate the comfort score for a single measurement."""
    if measurement not in COMFORT_RANGES:
        raise ValueError(f"upported comfort measurement: {measurement}")
    if value is None:
        return 0
    low, high = COMFORT_RANGES[measurement]
    return 1 if low <= value <= high else -1


def compute_comfort_index(temperature: float | None, humidity: float | None, brightness: float | None) -> tuple[int, ComfortLabel, dict[str, int]]:
    """Compute the overall room comfort index."""
    scores = {
        "temperature": score_parameter("temperature", temperature),
        "humidity": score_parameter("humidity", humidity),
        "brightness": score_parameter("brightness", brightness)
    }

    total = sum(scores.values())
    if total >= 2:
        label = ComfortLabel.COMFORTABLE
    elif total >= 0:
        label = ComfortLabel.MODERATE
    else:
        label = ComfortLabel.UNCOMFORTABLE
    return total, label, scores
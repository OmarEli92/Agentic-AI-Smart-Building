from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Any
import yaml
from pydantic import BaseModel, ConfigDict, Field
from agentic_bim_iot.domain.command import ActuationCommand


class RpcProfileError(RuntimeError):
    pass


class _ImmutableModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class RpcResponsePolicy(_ImmutableModel):
    success_path: str | None = None
    success_equals: Any = True


class RpcBinding(_ImmutableModel):
    """the binding between the method and the device firmware"""
    method: str
    params: dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int = 10_000
    response: RpcResponsePolicy | None = None


class RpcMeasurementProfile(_ImmutableModel):
    """all the available operations for a specific measurement"""
    operations: dict[str, RpcBinding]


class RpcActuatorTypeProfile(_ImmutableModel):
    measurements: dict[str, RpcMeasurementProfile]


class ActuatorRpcProfileDocument(_ImmutableModel):
    version: int = 1
    actuator_types: dict[str, RpcActuatorTypeProfile]


@dataclass(slots=True, frozen=True)
class ResolvedRpcCommand:
    method: str
    params: dict[str, Any]
    timeout_ms: int
    response_policy: RpcResponsePolicy | None


class ActuatorRpcProfile:
    """Load the RPC configuration and translate the commands"""

    def __init__(self, document: ActuatorRpcProfileDocument) -> None:
        self._document = document

    @classmethod
    def load(cls, path: str | Path) -> ActuatorRpcProfile:
        profile_path = Path(path).resolve()
        if not profile_path.is_file():
            raise RpcProfileError(f"Actuator RPC profile not found: {profile_path}")
        try:
            raw = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
            return cls(ActuatorRpcProfileDocument.model_validate(raw))
        except Exception as exc:
            raise RpcProfileError(f"Could not load actuator RPC profile '{profile_path}': {exc}") from exc


    def resolve(self, command: ActuationCommand) -> ResolvedRpcCommand:
        """Translate a command into a firmware RPC methoda and parameters"""
        actuator_profile = self._lookup_case_insensitive(values=self._document.actuator_types, requested=command.actuator_type, label="actuator type")
        measurement_profile = self._lookup_case_insensitive(values=actuator_profile.measurements, requested=command.measurement, label="measurement")
        operation_key = command.operation.value
        try:
            binding = measurement_profile.operations[operation_key]
        except KeyError as exc:
            raise RpcProfileError(f"No RPC mapping exists for actuator_type='{command.actuator_type}', measurement='{command.measurement}', operation='{operation_key}'.") from exc

        context: dict[str, Any] = {
            "target_value": command.target_value,
            "unit": command.unit,
            "measurement": command.measurement,
            "room_reference": command.room_reference,
            "actuator_guid": command.actuator_guid,
            "actuator_type": command.actuator_type,
            "command_id": command.command_id,
            "proposal_id": command.proposal_id,
            "source_action_id": command.source_action_id
        }

        rendered_params = self._render(value=binding.params, context=context)
        if not isinstance(rendered_params, dict):
            raise RpcProfileError("RPC params must render to a JSON object.")
        return ResolvedRpcCommand(method=binding.method, params=rendered_params, timeout_ms=binding.timeout_ms, response_policy=binding.response)


    @staticmethod
    def assert_success(response_payload: Any, policy: RpcResponsePolicy | None) -> None:
        if policy is None or policy.success_path is None:
            return
        actual = ActuatorRpcProfile._read_path(payload=response_payload, path=policy.success_path)
        if actual != policy.success_equals:
            raise RpcProfileError(f"Actuator failure: path='{policy.success_path}', expected={policy.success_equals!r}, actual={actual!r}.")


    @staticmethod
    def _lookup_case_insensitive(*, values: dict[str, Any], requested: str, label: str) -> Any:
        if requested in values:
            return values[requested]
        requested_folded = requested.casefold()
        for key, value in values.items():
            if key.casefold() == requested_folded:
                return value
        raise RpcProfileError(f"No RPC profile entry exists for {label} '{requested}'.")


    @staticmethod
    def _render(*, value: Any, context: dict[str, Any]) -> Any:
        if isinstance(value, dict):
            return {k: ActuatorRpcProfile._render(value=v, context=context) for k, v in value.items()}
        if isinstance(value, list):
            return [ActuatorRpcProfile._render(value=v, context=context) for v in value]
        if isinstance(value, str):
            if value.startswith("$") and value[1:] in context:
                return context[value[1:]]
            if "$" in value:
                try:
                    return Template(value).substitute(context)
                except KeyError as exc:
                    raise RpcProfileError(f"Unknown RPC profile variable in '{value}': {exc}") from exc
        return value


    @staticmethod
    def _read_path(*, payload: Any, path: str) -> Any:
        current = payload
        for segment in path.split("."):
            if not isinstance(current, dict) or segment not in current:
                raise RpcProfileError(f"RPC response does not contain any success path '{path}'.")
            current = current[segment]
        return current
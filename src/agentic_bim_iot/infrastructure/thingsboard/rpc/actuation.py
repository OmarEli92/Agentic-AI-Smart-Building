from __future__ import annotations
import json
import time
from typing import Any
from uuid import uuid4
from tb_ce_client import ThingsboardClient
from tb_ce_client.exceptions import ApiException
from agentic_bim_iot.application.interfaces.actuation import ActuationService
from agentic_bim_iot.application.interfaces.actuator_device_registry import ActuatorDeviceRegistry
from agentic_bim_iot.application.interfaces.device_registry import DeviceRegistryError
from agentic_bim_iot.domain.actuator import ActuatorReference
from agentic_bim_iot.domain.command import ActuationCommand
from agentic_bim_iot.domain.execution import ExecutionResult, ExecutionStatus
from agentic_bim_iot.infrastructure.observability.tracing import trace_observation
from agentic_bim_iot.infrastructure.thingsboard.rpc.profile import ActuatorRpcProfile, RpcProfileError



class ThingsBoardRpcActuationService(ActuationService):
    """This class is responsible for the execution of actuator commands through ThingsBoard.
    To be more precise it only implements the TWO-WAY server side RPC,
    so after the command is sent a response should be received so that
    we know the command was executed.
    """

    def __init__(self, *, client: ThingsboardClient, actuator_device_registry: ActuatorDeviceRegistry, rpc_profile: ActuatorRpcProfile) -> None:
        self._client = client
        self._actuator_device_registry = (actuator_device_registry)
        self._rpc_profile = rpc_profile

    def execute(self, command: ActuationCommand) -> ExecutionResult:
        started_at_ms = (time.time_ns() // 1_000_000)
        execution_id = str(uuid4())
        thingsboard_device_id: str | None = None
        rpc_method: str | None = None
        rpc_response: Any | None = None
        with trace_observation("thingsboard.rpc.twoway_actuation", as_type="tool",input_payload={"command": command.model_dump(mode="json")}) as observation:
            actuator = ActuatorReference(room_reference=(command.room_reference), controlled_measurement=(command.measurement),
                                         actuator_guid=(command.actuator_guid), actuator_type=(command.actuator_type))

            try:
                device = (self._actuator_device_registry.resolve(actuator))
                thingsboard_device_id = (device.platform_device_id)
                rpc_command = (self._rpc_profile.resolve(command))
                rpc_method = rpc_command.method
                body = json.dumps(
                    {
                        "method": rpc_command.method,
                        "params": rpc_command.params,
                        "timeout": (
                            rpc_command.timeout_ms
                        ),
                        "persistent": False,
                    }
                )
                # HTTP timeout shpould be slightly larger than the device RPC timeout as the documentation says
                request_timeout_seconds = (rpc_command.timeout_ms / 1000.0 + 5.0)
                raw_response = (self._client.handle_two_way_device_rpc_request_v2(device_id=(device.platform_device_id),body=body,_request_timeout=(request_timeout_seconds)))
                rpc_response = (self._decode_response(raw_response))
                self._rpc_profile.assert_success(rpc_response, rpc_command.response_policy)
                result = self._result(execution_id=execution_id, command=command, device_id=(device.platform_device_id),
                                      started_at_ms=started_at_ms, status=(ExecutionStatus.SUCCEEDED), error=None,
                                      rpc_method=rpc_method, rpc_response=rpc_response)
                
            except (DeviceRegistryError, RpcProfileError, ApiException) as exc:
                result = self._result(execution_id=execution_id, command=command,device_id=(thingsboard_device_id), 
                                      started_at_ms=started_at_ms, status=(ExecutionStatus.FAILED), error=str(exc),
                                      rpc_method=rpc_method, rpc_response=rpc_response)
            observation.update(output=result.model_dump(mode="json"))
            return result


    @staticmethod
    def _decode_response( response: Any) -> Any:
        if not isinstance(response, str):
            return response
        text = response.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    @staticmethod
    def _result( *, execution_id: str, command: ActuationCommand, device_id: str | None, started_at_ms: int, status: ExecutionStatus,
                error: str | None, rpc_method: str | None, rpc_response: Any | None) -> ExecutionResult:

        return ExecutionResult(execution_id=execution_id, command_id=command.command_id, proposal_id=command.proposal_id,
                                room_reference=(command.room_reference), measurement=command.measurement, actuator_guid=(command.actuator_guid),
                                thingsboard_device_id=device_id, target_value=command.target_value, unit=command.unit,
                                status=status, started_at_ms=started_at_ms, completed_at_ms=(time.time_ns() // 1_000_000),
                                error=error, rpc_method=rpc_method, rpc_response=rpc_response)
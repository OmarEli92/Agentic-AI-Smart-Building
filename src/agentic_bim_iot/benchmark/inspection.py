from __future__ import annotations
from typing import Any
from agentic_bim_iot.benchmark.instrumentation import BenchmarkCallbackHandler
from agentic_bim_iot.benchmark.models import BenchmarkObservation, ExecutionObservation, ToolCallObservation



class BenchmarkResultInspector:
    
    def inspect(self, *, result: dict[str, Any], runtime: Any, orchestration: str, duration_ms: float, callback: BenchmarkCallbackHandler) -> BenchmarkObservation:
        decision = result.get("supervisor_decision")
        actual_intent = self._enum_value(getattr(decision, "intent", None))
        actual_route = self._enum_value(getattr(decision, "route", None))
        comfort = result.get("comfort_assessment")
        comfort_label = self._enum_value(getattr(comfort, "label", None))
        approval = result.get("approval_result")
        approval_outcome = self._enum_value(getattr(approval, "outcome", None))
        proposal = result.get("action_proposal")
        if proposal is None and approval is not None:
            proposal = getattr(approval, "proposal", None)
        proposal_id = getattr(proposal, "proposal_id", None)
        if proposal_id:
            stored = runtime.proposal_repository.get(proposal_id)
            if stored is not None:
                proposal = stored
        proposal_status = self._enum_value(getattr(proposal, "status", None))
        command_result = result.get("command_result")
        command_status = self._enum_value(getattr(command_result, "status", None))
        safety = result.get("safety_result")
        safety_status = self._enum_value(getattr(safety, "status", None))
        batch = result.get("execution_batch_result")
        batch_status = self._enum_value(getattr(batch, "status", None))
        executions = self._execution_observations(batch)
        return BenchmarkObservation(
            orchestration=orchestration, actual_intent=actual_intent, actual_route=actual_route,
            final_answer=self._final_answer(result), comfort_label=comfort_label, proposal_id=proposal_id,
            proposal_status=proposal_status, approval_outcome=approval_outcome, command_status=command_status,
            safety_status=safety_status, execution_batch_status=batch_status, executions=executions,
            duration_ms=duration_ms, llm_calls=callback.llm_calls, input_tokens=callback.input_tokens,
            output_tokens=callback.output_tokens, total_tokens=callback.total_tokens,
            tool_calls=tuple(ToolCallObservation(name=name) for name in callback.tool_calls),
            retrieved_contexts=self._retrieved_contexts(result), error=self._result_error(result)
        )


    @staticmethod
    def failed(*, orchestration: str, duration_ms: float, callback: BenchmarkCallbackHandler, error: Exception) -> BenchmarkObservation:
        return BenchmarkObservation(
            orchestration=orchestration, duration_ms=duration_ms, llm_calls=callback.llm_calls,
            input_tokens=callback.input_tokens, output_tokens=callback.output_tokens, total_tokens=callback.total_tokens,
            tool_calls=tuple(ToolCallObservation(name=name) for name in callback.tool_calls), error=str(error),
        )

    @staticmethod
    def _execution_observations(batch: Any) -> tuple[ExecutionObservation, ...]:
        if batch is None:
            return ()
        raw_executions = getattr(batch, "executions", ()) or ()
        observations: list[ExecutionObservation] = []
        for execution in raw_executions:
            observations.append(ExecutionObservation(
                execution_id=str(execution.execution_id), status=BenchmarkResultInspector._enum_value(execution.status) or "unknown",
                room_reference=str(execution.room_reference), measurement=str(execution.measurement),
                target_value=float(execution.target_value), unit=str(execution.unit), proposal_id=getattr(execution, "proposal_id", None),
            ))
        return tuple(observations)



    @staticmethod
    def _retrieved_contexts(result: dict[str, Any]) -> tuple[str, ...]:
        contexts: list[str] = []
        telemetry = result.get("telemetry_reading")
        if telemetry is not None:
            contexts.append("Telemetry reading: " + BenchmarkResultInspector._serialize(telemetry))
        comfort = result.get("comfort_assessment")
        if comfort is not None:
            contexts.append("Comfort assessment: " + BenchmarkResultInspector._serialize(comfort))
        proposal = result.get("action_proposal")
        if proposal is not None:
            contexts.append("Action proposal: " + BenchmarkResultInspector._serialize(proposal))
        approval = result.get("approval_result")
        if approval is not None:
            contexts.append("Approval result: " + BenchmarkResultInspector._serialize(approval))
        command_result = result.get("command_result")
        if command_result is not None:
            contexts.append("Command structuring result: " + BenchmarkResultInspector._serialize(command_result))
        safety = result.get("safety_result")
        if safety is not None:
            contexts.append("Safety validation result: " + BenchmarkResultInspector._serialize(safety))
        execution = result.get("execution_batch_result")
        if execution is not None:
            contexts.append("Execution result: " + BenchmarkResultInspector._serialize(execution))

        return tuple(contexts)


    @staticmethod
    def _serialize(value: Any) -> str:
        if hasattr(value, "model_dump_json"):
            try:
                return value.model_dump_json()
            except TypeError:
                pass
        return str(value)
    
    
    @staticmethod
    def _final_answer(result: dict[str, Any]) -> str:
        final_answer = result.get("final_answer")
        if isinstance(final_answer, str):
            return final_answer
        messages = result.get("messages")
        if not isinstance(messages, list) or not messages:
            return ""
        content = getattr(messages[-1], "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict) and isinstance(block.get("text"), str):
                    parts.append(block["text"])
            return "\n".join(parts).strip()
        return str(content)


    @staticmethod
    def _result_error(result: dict[str, Any]) -> str | None:
        error = result.get("error")
        if error is None:
            return None
        if isinstance(error, str):
            return error.strip() or None
        return str(error)


    @staticmethod
    def _enum_value(value: Any) -> str | None:
        if value is None:
            return None
        raw = getattr(value, "value", value)
        return str(raw)
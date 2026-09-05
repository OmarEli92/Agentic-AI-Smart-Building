import re
from agentic_bim_iot.application.graph.state import AgentState
from agentic_bim_iot.application.interfaces.execution_repository import ExecutionRepository, ExecutionRepositoryError
from agentic_bim_iot.domain.execution import ExecutionBatchResult, ExecutionBatchStatus, ExecutionResult, ExecutionStatus


_UUID_PATTERN = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b")


class ExecutionStatusNode:
    """The execution Node responsible for reading the result of the execution of a physical action"""
    def __init__(self, execution_repository: ExecutionRepository) -> None:
        self._execution_repository = execution_repository

    def __call__(self, state: AgentState) -> dict[str, object]:
        batch = state.get("execution_batch_result")
        if batch is not None:
            final_answer = self._format_batch(batch)
            execution_error = state.get("execution_error")
            if execution_error:
                final_answer = f"{final_answer} Warning: {execution_error}"
            return {
                "execution_batch_result": batch,
                "final_answer": final_answer,
            }
        try:
            executions = self._resolve_requested_executions(state["user_query"])
        except ExecutionRepositoryError as exc:
            return {
                "execution_error": str(exc),
                "final_answer": "I could not retrieve the execution status.",
            }
        if not executions:
            return {
                "final_answer": "No matching execution result was found.",
            }
        batch = self._batch_from_executions(tuple(executions))
        return {
            "execution_batch_result": batch,
            "final_answer": self._format_batch(batch),
        }


    def _resolve_requested_executions(self, user_query: str) -> list[ExecutionResult]:
        match = _UUID_PATTERN.search(user_query)
        if match is None:
            latest = self._execution_repository.get_latest()
            return [] if latest is None else [latest]
        identifier = match.group(0)
        execution = self._execution_repository.get(identifier)
        if execution is not None:
            return [execution]
        execution = self._execution_repository.get_by_command_id(identifier)
        if execution is not None:
            return [execution]
        return self._execution_repository.list_by_proposal(identifier)

    @staticmethod
    def _batch_from_executions(executions: tuple[ExecutionResult, ...]) -> ExecutionBatchResult:
        succeeded = sum(execution.status == ExecutionStatus.SUCCEEDED for execution in executions)
        if succeeded == len(executions):
            status = ExecutionBatchStatus.SUCCEEDED
        elif succeeded == 0:
            status = ExecutionBatchStatus.FAILED
        else:
            status = ExecutionBatchStatus.PARTIAL_FAILURE
        return ExecutionBatchResult(
            status=status,
            executions=executions,
            message=f"Retrieved {len(executions)} execution result(s).",
        )

    @staticmethod
    def _format_batch(batch: ExecutionBatchResult) -> str:
        if not batch.executions:
            return batch.message
        details = []
        for execution in batch.executions:
            detail = f"Execution {execution.execution_id}: {execution.status.value}. {execution.room_reference} {execution.measurement} target {execution.target_value:g} {execution.unit}."
            if execution.error:
                detail = f"{detail} Error: {execution.error}"
            details.append(detail)
        return f"Execution status: {batch.status.value}. {' '.join(details)}"
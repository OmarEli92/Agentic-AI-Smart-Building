from agentic_bim_iot.application.graph.state import AgentState
from agentic_bim_iot.application.interfaces.actuation import ActuationService
from agentic_bim_iot.application.interfaces.execution_repository import (
    ExecutionRepository,
    ExecutionRepositoryError,
)
from agentic_bim_iot.application.interfaces.proposal_repository import (
    ProposalRepository,
    ProposalRepositoryError,
)
from agentic_bim_iot.domain.execution import (
    ExecutionBatchResult,
    ExecutionBatchStatus,
    ExecutionResult,
    ExecutionStatus,
)
from agentic_bim_iot.domain.proposal import ProposalStatus
from agentic_bim_iot.domain.safety import SafetyValidationStatus


class ActuationNode:
    def __init__(self, actuation_service: ActuationService, execution_repository: ExecutionRepository, proposal_repository: ProposalRepository) -> None:
        self._actuation_service = actuation_service
        self._execution_repository = execution_repository
        self._proposal_repository = proposal_repository

    def __call__(self, state: AgentState) -> dict[str, object]:
        safety_result = state.get("safety_result")
        if safety_result is None or safety_result.status != SafetyValidationStatus.ALLOWED:
            result = ExecutionBatchResult(
                status=ExecutionBatchStatus.FAILED,
                executions=(),
                message="Actuation was not executed because the safety validation did not allow the command.",
            )
            return {
                "execution_batch_result": result,
                "execution_error": result.message,
                "final_answer": result.message,
            }
        executions: list[ExecutionResult] = []
        persistence_error = None
        for command in safety_result.commands:
            try:
                existing_execution = self._execution_repository.get_by_command_id(command.command_id)
            except ExecutionRepositoryError as exc:
                persistence_error = str(exc)
                break
            if existing_execution is not None:
                executions.append(existing_execution)
                continue
            execution = self._actuation_service.execute(command)
            executions.append(execution)
            try:
                self._execution_repository.save(execution)
            except ExecutionRepositoryError as exc:
                persistence_error = str(exc)
                break
        result = self._build_batch(executions=tuple(executions), persistence_error=persistence_error)
        proposal_error = self._update_proposal_status(result)
        output: dict[str, object] = {
            "execution_batch_result": result,
            "final_answer": result.message,
        }
        errors = [err for err in (persistence_error, proposal_error) if err]
        if errors:
            output["execution_error"] = " ".join(errors)

        return output

    def _update_proposal_status(self, result: ExecutionBatchResult) -> str | None:
        proposal_ids = {ex.proposal_id for ex in result.executions if ex.proposal_id is not None}
        if len(proposal_ids) != 1:
            return None
        proposal_id = next(iter(proposal_ids))
        try:
            proposal = self._proposal_repository.get(proposal_id)
            if proposal is None:
                return f"Proposal '{proposal_id}' could not be found after execution."
            proposal_status = (
                ProposalStatus.EXECUTED
                if result.status == ExecutionBatchStatus.SUCCEEDED
                else ProposalStatus.FAILED
            )
            self._proposal_repository.update(proposal.model_copy(update={"status": proposal_status}))

        except ProposalRepositoryError as exc:
            return str(exc)

        return None

    @staticmethod
    def _build_batch(executions: tuple[ExecutionResult, ...], persistence_error: str | None = None) -> ExecutionBatchResult:
        if not executions:
            message = "No actuation command was executed."
            if persistence_error is not None:
                message = f"{message} Execution persistence failed: {persistence_error}"

            return ExecutionBatchResult(status=ExecutionBatchStatus.FAILED, executions=(), message=message)

        succeeded = sum(ex.status == ExecutionStatus.SUCCEEDED for ex in executions)
        if succeeded == len(executions) and persistence_error is None:
            status = ExecutionBatchStatus.SUCCEEDED
            message = f"{len(executions)} actuation command(s) were executed successfully on ThingsBoard."
        elif succeeded == 0:
            status = ExecutionBatchStatus.FAILED
            message = "All actuation commands failed."
        else:
            status = ExecutionBatchStatus.PARTIAL_FAILURE
            message = f"{succeeded} of {len(executions)} actuation command(s) succeeded."
        if persistence_error is not None:
            message = f"{message} The execution result could not be fully persisted: {persistence_error}"
        return ExecutionBatchResult(status=status, executions=executions, message=message)
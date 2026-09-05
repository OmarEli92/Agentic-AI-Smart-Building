from agentic_bim_iot.application.graph.state import AgentState
from agentic_bim_iot.application.interfaces.safety import SafetyPolicyValidator
from agentic_bim_iot.domain.safety import SafetyValidationResult, SafetyValidationStatus


class SafetyValidationNode:
    """The safety validation"""
    def __init__(self, safety_validator: SafetyPolicyValidator) -> None:
        self._safety_validator = safety_validator

    def __call__(self, state: AgentState) -> dict[str, object]:
        command_result = state.get("command_result")
        if command_result is None:
            result = SafetyValidationResult(status=SafetyValidationStatus.BLOCKED, commands=(), violations=("The command structuring result is missing.",), message="The command was blocked because no structured command is available.",)
            return {"safety_result": result, "safety_error": result.message, "final_answer": result.message}
        result = self._safety_validator.validate(command_result.commands)
        output: dict[str, object] = {"safety_result": result, "final_answer": result.message,}
        if result.status == SafetyValidationStatus.BLOCKED:
            output["safety_error"] = "; ".join(result.violations)
        return output
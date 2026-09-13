from __future__ import annotations
from typing import Any
from langgraph.types import Command
from agentic_bim_iot.application.graph.dependencies import GraphDependencies
from agentic_bim_iot.application.graph.nodes.actuation import ActuationNode
from agentic_bim_iot.application.react_agent.tools.common import Runtime, to_json, tool_command
from agentic_bim_iot.domain.command import CommandStructuringResult, CommandStructuringStatus
from agentic_bim_iot.domain.execution import ExecutionBatchResult
from agentic_bim_iot.domain.safety import SafetyValidationStatus


class SafeActuationExecutor:
    """It's important that no tool can access directly the ActuationService, it's mandatory
    that when physical actuation are involved the system double check the safety and the validity of the request.
    In simple words the LLM CANNOT overcome the user request, guardrails and safety policies"""
    
    def __init__(self, dependencies: GraphDependencies):
        self._dependencies = dependencies
        self._actuation_node = ActuationNode(dependencies.actuation_service,dependencies.execution_repository, dependencies.proposal_repository)
        
    
    def execute(self, *, runtime: Runtime, command_result: CommandStructuringResult, extra_updates: dict[str, Any] | None = None) -> Command:
        updates = dict(extra_updates or {})
        updates["command_result"] = command_result
        #If the status of the command is NOT READY
        if command_result.status != CommandStructuringStatus.READY:
            return tool_command(runtime, to_json({"status" : "blocked","stage": "command_structuring","message": command_result.message}), **updates)
        safety_result = self._dependencies.safety_validator.validate(command_result.commands)
        updates["safety_result"] = safety_result
        #If the stauts of the safety result is NOT ALLOWED
        if safety_result.status != SafetyValidationStatus.ALLOWED:
            return tool_command(runtime, to_json({"status": "blocked", "stage": "safety_validation","message": safety_result.message,
                    "violations": list(safety_result.violations)}),**updates )
        output = self._actuation_node({"safety_result": safety_result})
        batch = output.get("execution_batch_result")
        if isinstance(batch, ExecutionBatchResult):
            updates["execution_batch_result"] = batch
        return tool_command(
            runtime,
            to_json({
                "status": "executed" if isinstance(batch, ExecutionBatchResult) else "error",
                "safety": safety_result.model_dump(mode="json"),
                "execution": batch.model_dump(mode="json") if isinstance(batch, ExecutionBatchResult) else None,
                "message": output.get("final_answer", "Actuation completed."),
            }),
            **updates,
        )

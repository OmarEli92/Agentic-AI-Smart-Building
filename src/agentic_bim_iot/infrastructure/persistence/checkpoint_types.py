from __future__ import annotations
from agentic_bim_iot.domain.approval import ApprovalOutcome, ApprovalResult
from agentic_bim_iot.domain.comfort import ComfortAssessment, ComfortLabel
from agentic_bim_iot.domain.command import ActuationCommand, CommandStructuringResult, CommandStructuringStatus
from agentic_bim_iot.domain.execution import ExecutionBatchResult, ExecutionResult, ExecutionStatus
from agentic_bim_iot.domain.proposal import ActionProposal, ProposalSource, ProposalStatus
from agentic_bim_iot.domain.safety import SafetyValidationResult, SafetyValidationStatus

CHECKPOINT_ALLOWED_TYPES: tuple[type, ...] = (
    # Comfort
    ComfortAssessment,
    ComfortLabel,
    # Proposal
    ActionProposal,
    ProposalSource,
    ProposalStatus,
    # Approval
    ApprovalResult,
    ApprovalOutcome,
    # Commands
    ActuationCommand,
    CommandStructuringResult,
    CommandStructuringStatus,
    # Safety
    SafetyValidationResult,
    SafetyValidationStatus,
    # Execution
    ExecutionBatchResult,
    ExecutionResult,
    ExecutionStatus
)
import logging
import re
import time
from agentic_bim_iot.application.interfaces import notification_repository
from agentic_bim_iot.application.interfaces.approval import ApprovalHandlerError
from agentic_bim_iot.application.interfaces.comfort import ComfortEngine, ComfortEngineError
from agentic_bim_iot.application.interfaces.proposal_repository import ProposalRepository, ProposalRepositoryError
from agentic_bim_iot.domain.approval import ApprovalOutcome, ApprovalResult
from agentic_bim_iot.domain.comfort import ComfortAssessment
from agentic_bim_iot.domain.enums import Intent
from agentic_bim_iot.domain.proposal import ActionProposal, ProposalStatus
from agentic_bim_iot.application.interfaces.notification_repository import NotificationRepository, NotificationRepositoryError

logger = logging.getLogger("agentic_bim_iot.approval")
_PROPOSAL_ID_PATTERN = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b")


class ProposalApprovalHandler:
    def __init__(self, proposal_repository: ProposalRepository, comfort_engine: ComfortEngine,
    notification_repository: NotificationRepository | None = None) -> None:
        self._proposal_repository = proposal_repository
        self._comfort_engine = comfort_engine
        self._comfort_engine = comfort_engine
        self._notification_repository = notification_repository
    def handle(self, intent: Intent, user_query: str, room_reference: str | None = None) -> ApprovalResult:
        proposal_result = self._resolve_pending_proposal(user_query=user_query, room_reference=room_reference)
        if isinstance(proposal_result, ApprovalResult):
            return proposal_result

        proposal = proposal_result
        current_time_ms = time.time_ns() // 1_000_000

        if current_time_ms >= proposal.expires_at_ms:
            expired_proposal = proposal.model_copy(update={"status": ProposalStatus.EXPIRED})
            self._update_proposal(expired_proposal)
            return ApprovalResult(outcome=ApprovalOutcome.EXPIRED, proposal=expired_proposal, current_comfort_assessment=None, message=f"Proposal '{proposal.proposal_id}' has expired and cannot be used anymore.",)

        if intent == Intent.REJECT_PROPOSAL:
            rejected_proposal = proposal.model_copy(update={"status": ProposalStatus.REJECTED})
            self._update_proposal(rejected_proposal)
            return ApprovalResult(outcome=ApprovalOutcome.REJECTED, proposal=rejected_proposal, current_comfort_assessment=None, message=f"Proposal '{proposal.proposal_id}' was rejected.",)

        if intent == Intent.MODIFY_PROPOSAL:
            return ApprovalResult(outcome=ApprovalOutcome.MODIFICATION_REQUESTED, proposal=proposal, current_comfort_assessment=None,
                message=f"Proposal '{proposal.proposal_id}' will be replanned using the requested modifications.")
        if intent != Intent.APPROVE_PROPOSAL:
            raise ApprovalHandlerError(f"Unsupported approval intent: {intent.value}")
        try:
            current_assessment = self._comfort_engine.assess(proposal.room_reference)
        except ComfortEngineError as exc:
            raise ApprovalHandlerError("The proposal could not be revalidated because the current comfort assessment failed.") from exc

        if self._proposal_is_stale(proposal=proposal, current_assessment=current_assessment):
            stale_proposal = proposal.model_copy(update={"status": ProposalStatus.STALE})
            self._update_proposal(stale_proposal)
            return ApprovalResult(outcome=ApprovalOutcome.STALE, proposal=stale_proposal, current_comfort_assessment=current_assessment, message=f"Proposal '{proposal.proposal_id}' is no longer valid because the current environmental conditions have changed.")

        approved_proposal = proposal.model_copy(update={"status": ProposalStatus.APPROVED,})
        self._update_proposal(approved_proposal)
        return ApprovalResult(outcome=ApprovalOutcome.APPROVED, proposal=approved_proposal, current_comfort_assessment=current_assessment, message=f"Proposal '{proposal.proposal_id}' was approved and is ready for command structuring.",)

    def _resolve_pending_proposal(self, user_query: str, room_reference: str | None) -> ActionProposal | ApprovalResult:
        explicit_proposal_id = self._extract_proposal_id(user_query)
        try:
            if explicit_proposal_id is not None:
                proposal = self._proposal_repository.get(explicit_proposal_id)
                if proposal is None or proposal.status != ProposalStatus.PENDING_APPROVAL:
                    return ApprovalResult(outcome=ApprovalOutcome.NOT_FOUND, proposal=proposal, current_comfort_assessment=None, message=f"No pending proposal with ID '{explicit_proposal_id}' was found.",)

                return proposal
            pending_proposals = self._proposal_repository.list_pending(room_reference=room_reference)

        except ProposalRepositoryError as exc:
            raise ApprovalHandlerError("The pending proposal could not be retrieved.") from exc
        if not pending_proposals:
            return ApprovalResult(outcome=ApprovalOutcome.NOT_FOUND, proposal=None, current_comfort_assessment=None, message="There is no pending proposal matching this request.",)

        if len(pending_proposals) > 1:
            proposal_ids = ", ".join(proposal.proposal_id for proposal in pending_proposals)
            return ApprovalResult(outcome=ApprovalOutcome.AMBIGUOUS, proposal=None, current_comfort_assessment=None, message=f"Multiple pending proposals match this request. Specify the proposal ID: {proposal_ids}.",)
        return pending_proposals[0]


    def _update_proposal(self, proposal: ActionProposal) -> None:
        try:
            self._proposal_repository.update(proposal)
        except ProposalRepositoryError as exc:
            raise ApprovalHandlerError("The proposal status could not be updated.") from exc


    def _resolve_notification_fail_open(self, proposal_id: str) -> None:
        if self._notification_repository is None:
            return
        try:
            self._notification_repository.resolve_by_proposal(proposal_id)
        except NotificationRepositoryError as exc:
            logger.warning("Could not resolve notification for proposal %s: %s",proposal_id, exc)


    @staticmethod
    def _proposal_is_stale(proposal: ActionProposal, current_assessment: ComfortAssessment) -> bool:
        for action in proposal.actions:
            parameter = current_assessment.parameters.get(action.measurement)
            if parameter is None or parameter.value is None:
                return True
            original_value = action.current_value
            current_value = parameter.value
            if original_value < parameter.minimum:
                if current_value >= parameter.minimum:
                    return True
                continue
            if original_value > parameter.maximum:
                if current_value <= parameter.maximum:
                    return True
                continue
            
            return True
        
        return False

    @staticmethod
    def _extract_proposal_id(user_query: str) -> str | None:
        match = _PROPOSAL_ID_PATTERN.search(
            user_query
        )
        if match is None:
            return None
        return match.group(0)
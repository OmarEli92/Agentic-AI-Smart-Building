import logging
import time
from uuid import uuid4

from langchain_core.runnables import RunnableConfig

from agentic_bim_iot.application.interfaces.comfort import ComfortEngine, ComfortEngineError
from agentic_bim_iot.application.interfaces.notification_repository import NotificationRepository, NotificationRepositoryError
from agentic_bim_iot.application.interfaces.planning import PlanningEngine, PlanningEngineError
from agentic_bim_iot.application.interfaces.proposal_repository import ProposalRepository, ProposalRepositoryError
from agentic_bim_iot.domain.notification import Notification, NotificationStatus, NotificationType
from agentic_bim_iot.domain.proactive import ProactiveCheckResult, ProactiveCheckStatus
from agentic_bim_iot.domain.proposal import ActionProposal, ProposalSource, ProposalStatus
from agentic_bim_iot.infrastructure.observability.tracing import trace_observation


logger = logging.getLogger("agentic_bim_iot.proactive")


class ProactiveComfortMonitor:
    """The core of the Proactive comfort functionality it starts from here"""
    def __init__(self, comfort_engine: ComfortEngine, planning_engine: PlanningEngine, proposal_repository: ProposalRepository, notification_repository: NotificationRepository, proposal_cooldown_seconds: int) -> None:
        self._comfort_engine = comfort_engine
        self._planning_engine = planning_engine
        self._proposal_repository = proposal_repository
        self._notification_repository = notification_repository
        self._proposal_cooldown_seconds = proposal_cooldown_seconds

    def check_room(self, room_reference: str, config: RunnableConfig | None = None) -> ProactiveCheckResult:
        room = " ".join(room_reference.strip().split())
        if not room:
            raise ValueError("Room reference cannot be empty.")
        with trace_observation("proactive_comfort.check_room", as_type="span", input_payload={"room_reference": room}) as observation:
            try:
                assessment = self._comfort_engine.assess(room)
                latest_proposal = self._proposal_repository.get_latest(room)
                latest_proposal = self._expire_if_needed(latest_proposal)
                if not assessment.data_complete:
                    result = ProactiveCheckResult(room_reference=room, status=ProactiveCheckStatus.DATA_INCOMPLETE, comfort_label=assessment.label.value, comfort_score=assessment.total_score, proposal_id=latest_proposal.proposal_id if latest_proposal is not None else None, message=f"Proactive planning was skipped for {room} because the comfort assessment is incomplete.")
                    observation.update(output=result.model_dump(mode="json"))
                    return result
                actionable = self._has_actionable_measurements(assessment)
                if not actionable:
                    if latest_proposal is not None and latest_proposal.status == ProposalStatus.PENDING_APPROVAL:
                        stale_proposal = latest_proposal.model_copy(update={"status": ProposalStatus.STALE})
                        self._proposal_repository.update(stale_proposal)
                        self._resolve_notification_fail_open(stale_proposal.proposal_id)
                        latest_proposal = stale_proposal
                    result = ProactiveCheckResult(room_reference=room, status=ProactiveCheckStatus.COMFORTABLE, comfort_label=assessment.label.value, comfort_score=assessment.total_score, proposal_id=latest_proposal.proposal_id if latest_proposal is not None else None, message=f"No proactive proposal is required for {room}.")
                    observation.update(output=result.model_dump(mode="json"))
                    return result
                if latest_proposal is not None and latest_proposal.status == ProposalStatus.PENDING_APPROVAL:
                    result = ProactiveCheckResult(room_reference=room, status=ProactiveCheckStatus.PENDING_PROPOSAL_EXISTS, comfort_label=assessment.label.value, comfort_score=assessment.total_score, proposal_id=latest_proposal.proposal_id, message=f"A pending proposal already exists for {room}.")
                    observation.update(output=result.model_dump(mode="json"))
                    return result
                if self._cooldown_is_active(latest_proposal):
                    result = ProactiveCheckResult(room_reference=room, status=ProactiveCheckStatus.COOLDOWN_ACTIVE, comfort_label=assessment.label.value, comfort_score=assessment.total_score, proposal_id=latest_proposal.proposal_id if latest_proposal is not None else None, message=f"Proactive planning for {room} is inside the proposal cooldown window.")
                    observation.update(output=result.model_dump(mode="json"))
                    return result
                planning_result = self._planning_engine.plan_from_assessment(user_query=f"Generate a proactive comfort-improvement proposal for {room}.", room_reference=room, assessment=assessment, previous_proposal=None, source=ProposalSource.PROACTIVE_MONITOR, config=config)
                if planning_result.proposal is None:
                    result = ProactiveCheckResult(room_reference=room, status=ProactiveCheckStatus.NO_ACTION_AVAILABLE, comfort_label=assessment.label.value, comfort_score=assessment.total_score, message=planning_result.message)
                    observation.update(output=result.model_dump(mode="json"))
                    return result
                proposal = planning_result.proposal
                self._create_notification_fail_open(proposal)
                result = ProactiveCheckResult(room_reference=room, status=ProactiveCheckStatus.PROPOSAL_CREATED, comfort_label=assessment.label.value, comfort_score=assessment.total_score, proposal_id=proposal.proposal_id, message=planning_result.message)
                observation.update(output=result.model_dump(mode="json"))
                return result
            except (ComfortEngineError, PlanningEngineError, ProposalRepositoryError) as exc:
                result = ProactiveCheckResult(room_reference=room, status=ProactiveCheckStatus.FAILED, message=str(exc))
                observation.update(level="ERROR", status_message=str(exc), output=result.model_dump(mode="json"))
                return result



    @staticmethod
    def _has_actionable_measurements(assessment) -> bool:
        return any(parameter.value is not None and parameter.within_range is False for parameter in assessment.parameters.values())



    def _expire_if_needed(self, proposal: ActionProposal | None) -> ActionProposal | None:
        if proposal is None or proposal.status != ProposalStatus.PENDING_APPROVAL:
            return proposal
        current_time_ms = time.time_ns() // 1_000_000
        if current_time_ms < proposal.expires_at_ms:
            return proposal
        expired = proposal.model_copy(update={"status": ProposalStatus.EXPIRED})
        self._proposal_repository.update(expired)
        self._resolve_notification_fail_open(expired.proposal_id)
        return expired


    def _cooldown_is_active(self, proposal: ActionProposal | None) -> bool:
        if proposal is None or proposal.status == ProposalStatus.PENDING_APPROVAL:
            return False
        current_time_ms = time.time_ns() // 1_000_000
        cooldown_ms = self._proposal_cooldown_seconds * 1000
        return current_time_ms - proposal.created_at_ms < cooldown_ms


    def _create_notification_fail_open(self, proposal: ActionProposal) -> None:
        notification = Notification(notification_id=str(uuid4()), notification_type=NotificationType.COMFORT_PROPOSAL, status=NotificationStatus.UNREAD, room_reference=proposal.room_reference, proposal_id=proposal.proposal_id, title=f"Comfort action proposed for {proposal.room_reference}", message=proposal.rationale, created_at_ms=time.time_ns() // 1_000_000)
        try:
            self._notification_repository.save(notification)
        except NotificationRepositoryError as exc:
            logger.warning("Could not persist proactive notification for proposal %s: %s", proposal.proposal_id, exc)



    def _resolve_notification_fail_open(self, proposal_id: str) -> None:
        try:
            self._notification_repository.resolve_by_proposal(proposal_id)
        except NotificationRepositoryError as exc:
            logger.warning("Could not resolve notification for proposal %s: %s", proposal_id, exc)
from dataclasses import dataclass
from threading import RLock
from typing import Any
from uuid import uuid4
from agentic_bim_iot.bootstrap import ApplicationRuntime
from agentic_bim_iot.domain.notification import Notification
from agentic_bim_iot.domain.proposal import ActionProposal
from agentic_bim_iot.infrastructure.observability.runtime import ObservabilityRuntime


@dataclass(slots=True, frozen=True)
class UIRequestResult:
    final_answer: str
    trace_id: str | None
    proposal_id: str | None
    graph_result: dict[str, Any]


class StreamlitController:
    """The main core of the streamlit layer it manage the messages, the incoming notifications, unread, read
    , unapproved proposal, pending proposal"""
    def __init__(self, runtime: ApplicationRuntime, observability: ObservabilityRuntime, session_id: str, graph_lock: RLock) -> None:
        self._runtime = runtime
        self._observability = observability
        self._session_id = session_id
        self._graph_lock = graph_lock


    def send_message(self, user_query: str, *, interaction_type: str = "chat") -> UIRequestResult:
        query = user_query.strip()
        if not query:
            raise ValueError("The Facility Manager query cannot be empty.")
        request_id = str(uuid4())
        try:
            with self._observability.trace_request(
                request_id=request_id,
                session_id=self._session_id,
                user_query=query,
                trace_name="agentic-smart-building-streamlit",
                tags=["streamlit", f"interaction:{interaction_type}"],
                metadata={"run_context": "streamlit", "interaction_type": interaction_type},
            ) as trace:
                with self._graph_lock:
                    result = self._runtime.graph.invoke(
                        {"user_query": query},
                        config={
                            "callbacks": trace.callbacks,
                            "run_name": "agentic-smart-building-graph",
                            "metadata": {
                                "request_id": request_id,
                                "ui_session_id": self._session_id,
                                "interaction_type": interaction_type
                            }
                        }
                    )
                final_answer = str(result.get("final_answer", ""))
                proposal = result.get("action_proposal")
                proposal_id = proposal.proposal_id if isinstance(proposal, ActionProposal) else None
                trace.set_output({"final_answer": final_answer, "proposal_id": proposal_id})
                return UIRequestResult(final_answer=final_answer, trace_id=trace.trace_id, proposal_id=proposal_id, graph_result=result)
        finally:
            self._observability.flush()


    def approve_proposal(self, proposal_id: str) -> UIRequestResult:
        return self.send_message(f"Approve proposal {proposal_id}.", interaction_type="proposal_approval")


    def reject_proposal(self, proposal_id: str) -> UIRequestResult:
        return self.send_message(f"Reject proposal {proposal_id}.", interaction_type="proposal_rejection")


    def modify_proposal(self, proposal_id: str, instructions: str) -> UIRequestResult:
        normalized_instructions = instructions.strip()
        if not normalized_instructions:
            raise ValueError("Modification instructions cannot be empty.")
        return self.send_message(f"Modify proposal {proposal_id}: {normalized_instructions}", interaction_type="proposal_modification")


    def get_proposal(self, proposal_id: str) -> ActionProposal | None:
        return self._runtime.proposal_repository.get(proposal_id)


    def list_pending_proposals(self) -> list[ActionProposal]:
        return self._runtime.proposal_repository.list_pending()


    def get_notification(self, notification_id: str) -> Notification | None:
        return self._runtime.notification_repository.get(notification_id)


    def list_unread_notifications(self) -> list[Notification]:
        return self._runtime.notification_repository.list_unread()


    def mark_notification_read(self, notification_id: str) -> None:
        self._runtime.notification_repository.mark_read(notification_id)


    def resolve_notification(self, proposal_id: str) -> None:
        self._runtime.notification_repository.resolve_by_proposal(proposal_id)
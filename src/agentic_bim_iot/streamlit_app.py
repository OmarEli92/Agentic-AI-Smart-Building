from uuid import uuid4
import streamlit as st
from dotenv import load_dotenv
from agentic_bim_iot.config.settings import get_settings
from agentic_bim_iot.domain.notification import NotificationStatus
from agentic_bim_iot.domain.proposal import ActionProposal, ProposalStatus
from agentic_bim_iot.presentation.streamlit.controller import StreamlitController, UIRequestResult
from agentic_bim_iot.presentation.streamlit.runtime import StreamlitRuntimeHolder

load_dotenv()
settings = get_settings()
st.set_page_config(page_title=settings.streamlit_page_title, layout="wide", initial_sidebar_state="expanded")


@st.cache_resource(show_spinner="Initializing the Agentic Smart Building...")
def get_runtime_holder() -> StreamlitRuntimeHolder:
    return StreamlitRuntimeHolder(settings=get_settings())


def initialize_session_state() -> None:
    if "ui_session_id" not in st.session_state:
        st.session_state.ui_session_id = str(uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_auto_popup_notification_id" not in st.session_state:
        st.session_state.last_auto_popup_notification_id = None


def append_message(*, role: str, content: str, proposal_id: str | None = None) -> None:
    st.session_state.messages.append(
        {
            "role": role,
            "content": content,
            "proposal_id": proposal_id,
        }
    )


def render_proposal(proposal: ActionProposal) -> None:
    source_label = proposal.source.value.replace("_", " ").title()
    status_label = proposal.status.value.replace("_", " ").title()
    st.caption(f"Source: {source_label} · Status: {status_label}")
    metric_room, metric_score, metric_actions = st.columns(3)
    metric_room.metric("Room", proposal.room_reference)
    metric_score.metric("Comfort score", proposal.comfort_assessment.total_score)
    metric_actions.metric("Actions", len(proposal.actions))
    st.markdown("**Rationale**")
    st.write(proposal.rationale)
    st.markdown("**Proposed actions**")
    for action in proposal.actions:
        with st.container(border=True):
            st.markdown(f"**{action.measurement.title()}**")
            st.write(f"{action.current_value:g} {action.unit} → {action.target_value:g} {action.unit}")
            st.caption(f"Actuator: {action.actuator_type} · {action.actuator_guid}")
            st.write(action.reason)


def handle_ui_result(result: UIRequestResult) -> None:
    append_message( role="assistant", content=result.final_answer, proposal_id=result.proposal_id)


@st.dialog("Comfort action proposal", width="large", dismissible=True, on_dismiss="rerun")
def proposal_dialog(proposal_id: str, notification_id: str | None = None) -> None:
    if notification_id is not None:
        notification = controller.get_notification(notification_id)
        if notification is not None and notification.status == NotificationStatus.UNREAD:
            controller.mark_notification_read(notification_id)

    proposal = controller.get_proposal(proposal_id)
    if proposal is None:
        st.error("The proposal no longer exists.")
        if st.button("Close", width="stretch"):
            st.rerun()
        return
    render_proposal(proposal)
    if proposal.status != ProposalStatus.PENDING_APPROVAL:
        st.info(f"This proposal is no longer pending. Current status: {proposal.status.value}.")
        if st.button("Close", width="stretch"):
            st.rerun()
        return
    approve_column, reject_column = st.columns(2)
    if approve_column.button("Approve", type="primary", width="stretch", key=f"approve-{proposal.proposal_id}"):
        with st.spinner("Revalidating current comfort and executing the approved action..."):
            result = controller.approve_proposal(proposal.proposal_id)
        handle_ui_result(result)
        st.success(result.final_answer)
        st.rerun()

    if reject_column.button("Reject", width="stretch", key=f"reject-{proposal.proposal_id}"):
        with st.spinner("Rejecting proposal..."):
            result = controller.reject_proposal(proposal.proposal_id)
        handle_ui_result(result)
        st.info(result.final_answer)
        st.rerun()

    st.divider()
    modification = st.text_area("Request a modification", placeholder="Example: keep the temperature target closer to 22 degrees.", key=f"modify-text-{proposal.proposal_id}")

    if st.button("Submit modification", width="stretch", key=f"modify-{proposal.proposal_id}"):
        if not modification.strip():
            st.warning("Enter the requested modification first.")
            return
        with st.spinner("Generating the revised proposal..."):
            result = controller.modify_proposal(proposal.proposal_id, modification)
        replacement = result.graph_result.get("action_proposal")
        if isinstance(replacement, ActionProposal) and replacement.proposal_id != proposal.proposal_id:
            controller.resolve_notification(proposal.proposal_id)
        handle_ui_result(result)
        st.success(result.final_answer)
        st.rerun()


def render_sidebar() -> None:
    with st.sidebar:
        st.title("Agentic Smart Building")
        st.caption("Facility Manager Console")
        st.divider()
        st.markdown("**Runtime configuration**")
        st.write(f"Semantic backend: `{settings.semantic_backend.value}`")
        st.write(f"Actuator resolver: `{settings.actuator_resolution_strategy.value}`")
        st.write(f"BIM cache: `{settings.bim_cache_backend.value}`")
        st.write(f"Observability: `{settings.observability_backend.value}`")
        proactive_status = "enabled" if settings.proactive_comfort_enabled else "disabled"
        st.write(f"Proactive comfort: `{proactive_status}`")
        st.caption("The proactive worker is a separate process. This indicates configuration, not worker liveness.")
        st.divider()
        if st.button("Clear conversation", width="stretch"):
            st.session_state.messages = []
            st.rerun()


def render_chat_history() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("proposal_id"):
                st.caption(f"Proposal: {message['proposal_id']}")
            

POLL_INTERVAL = f"{settings.streamlit_notification_poll_seconds}s"


@st.fragment(run_every=POLL_INTERVAL, key="proposal-notifications")
def notification_watcher() -> None:
    unread_notifications = controller.list_unread_notifications()
    pending_proposals = controller.list_pending_proposals()
    header_column, count_column = st.columns([4, 1])
    header_column.subheader("Action proposals")
    count_column.metric("Pending", len(pending_proposals))
    dialog_opened = False
    if pending_proposals:
        with st.expander("Pending proposals", expanded=False):
            for proposal in pending_proposals:
                proposal_column, button_column = st.columns([4, 1])
                proposal_column.write(f"**{proposal.room_reference}** · {proposal.source.value.replace('_', ' ')}")
                proposal_column.caption(proposal.rationale)
                if button_column.button("Review", key=f"review-{proposal.proposal_id}", width="stretch"):
                    proposal_dialog(proposal_id=proposal.proposal_id)
                    dialog_opened = True
                    return

    if dialog_opened or not unread_notifications:
        return
    newest_notification = unread_notifications[0]
    if newest_notification.proposal_id is None:
        return
    if st.session_state.last_auto_popup_notification_id == newest_notification.notification_id:
        return
    st.session_state.last_auto_popup_notification_id = newest_notification.notification_id
    proposal_dialog(proposal_id=newest_notification.proposal_id, notification_id=newest_notification.notification_id)


initialize_session_state()
runtime_holder = get_runtime_holder()
controller = StreamlitController(runtime=runtime_holder.runtime, observability=runtime_holder.observability,
                                 session_id=st.session_state.ui_session_id, graph_lock=runtime_holder.graph_lock)

render_sidebar()
st.title("Facility Manager Assistant")
st.caption("Ask about BIM information, live telemetry, comfort, recommendations, actuation and execution status.")
notification_watcher()
st.divider()
render_chat_history()
user_query = st.chat_input("Ask the smart building assistant...")

if user_query:
    append_message(role="user", content=user_query)
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Processing request..."):
                result = controller.send_message(user_query, interaction_type="chat")
            st.markdown(result.final_answer)
            if result.proposal_id is not None:
                st.caption(f"Proposal: {result.proposal_id}")
            handle_ui_result(result)

        except Exception as exc:
            error_message = f"The request could not be completed: {exc}"
            st.error(error_message)
            append_message(role="assistant", content=error_message)
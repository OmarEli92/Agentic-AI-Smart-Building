import signal
import time
from threading import Event
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv

from agentic_bim_iot.bootstrap import create_runtime
from agentic_bim_iot.config.settings import get_settings
from agentic_bim_iot.domain.proposal import ProposalStatus
from agentic_bim_iot.infrastructure.observability.logging_config import configure_application_logging
from agentic_bim_iot.infrastructure.observability.runtime import ObservabilityRuntime


def _find_proposal_id(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        proposal_id = value.get("proposal_id")
        if proposal_id:
            return str(proposal_id)
        for nested_value in value.values():
            found = _find_proposal_id(nested_value)
            if found is not None:
                return found
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            found = _find_proposal_id(item)
            if found is not None:
                return found
        return None
    return None


def _extract_proposal_id(result: Any) -> str | None:
    if result is None:
        return None
    direct_proposal_id = getattr(result, "proposal_id", None)
    if direct_proposal_id:
        return str(direct_proposal_id)
    proposal = getattr(result, "proposal", None)
    if proposal is not None:
        nested_proposal_id = getattr(proposal, "proposal_id", None)
        if nested_proposal_id:
            return str(nested_proposal_id)
    if hasattr(result, "model_dump"):
        payload = result.model_dump(mode="python")
        return _find_proposal_id(payload)
    return None


def _wait_for_proposal_resolution(runtime, proposal_id: str, stop_event: Event, poll_seconds: float = 0.5) -> None:
    print("\n" + "=" * 70)
    print("PROACTIVE MONITOR PAUSED")
    print("=" * 70)
    print(f"Waiting for proposal: {proposal_id}")
    print("No other rooms will be checked until the proposal is resolved.")
    print("=" * 70)

    while not stop_event.is_set():
        proposal = runtime.proposal_repository.get(proposal_id)
        if proposal is None:
            print(f"\nProposal {proposal_id} no longer exists.\nResuming proactive monitoring.")
            return
        if proposal.status != ProposalStatus.PENDING_APPROVAL:
            print("\n" + "=" * 70)
            print("PROPOSAL RESOLVED")
            print("=" * 70)
            print(f"Proposal: {proposal_id}")
            print(f"Status: {proposal.status.value}")
            print("Resuming proactive monitoring.")
            print("=" * 70)
            return
        stop_event.wait(poll_seconds)


def main() -> None:
    load_dotenv()
    settings = get_settings()
    logger = configure_application_logging(log_file_path=settings.log_file_path, level=settings.log_level)

    if not settings.proactive_comfort_enabled:
        print("Proactive comfort monitoring is disabled.")
        return

    observability = ObservabilityRuntime(settings=settings)
    stop_event = Event()

    def request_shutdown(signum, frame) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_shutdown)

    try:
        with create_runtime(settings) as runtime:
            if runtime.proactive_monitor is None:
                raise RuntimeError("The proactive comfort monitor cannot start because no planning engine is available.")

            rooms = runtime.room_catalog.list_rooms()
            if not rooms:
                raise RuntimeError("Proactive comfort monitoring is enabled but no rooms are configured.")

            print("\n" + "=" * 70)
            print("PROACTIVE COMFORT MONITOR")
            print("=" * 70)
            print(f"Rooms: {', '.join(rooms)}")
            print(f"Interval: {settings.proactive_comfort_interval_seconds} seconds")
            print("=" * 70 + "\n")

            while not stop_event.is_set():
                cycle_id = str(uuid4())
                print(f"Starting proactive cycle {cycle_id}")

                for room in rooms:
                    if stop_event.is_set():
                        break

                    request_id = str(uuid4())
                    proposal_id_to_wait: str | None = None
                    print(f"[{room}] Checking comfort...")

                    try:
                        with observability.trace_request(
                            request_id=request_id,
                            session_id=f"proactive:{cycle_id}",
                            user_query=f"Proactive comfort check for {room}",
                            trace_name="agentic-smart-building-proactive",
                            root_observation_name="proactive-comfort-check",
                            tags=["proactive", "comfort-monitor", f"room:{room}"],
                            metadata={"run_context": "proactive", "cycle_id": cycle_id, "room_reference": room},
                        ) as trace:
                            result = runtime.proactive_monitor.check_room(
                                room_reference=room,
                                config={"callbacks": trace.callbacks},
                            )
                            trace.set_output(result.model_dump(mode="json"))

                        print(f"[{room}] {result.status.value}: {result.message}")
                        proposal_id = _extract_proposal_id(result)

                        if proposal_id is not None:
                            proposal = runtime.proposal_repository.get(proposal_id)
                            if proposal is not None and proposal.status == ProposalStatus.PENDING_APPROVAL:
                                proposal_id_to_wait = proposal_id
                                print(f"[{room}] Pending proposal detected: {proposal_id}")

                    except Exception as exc:
                        print(f"[{room}] ERROR: {type(exc).__name__}: {exc}")
                        logger.exception(
                            "Proactive comfort check failed.",
                            extra={
                                "event": "proactive_check_failed",
                                "request_id": request_id,
                                "component": "proactive_monitor",
                            },
                        )
                    finally:
                        observability.flush()

                    if proposal_id_to_wait is not None:
                        _wait_for_proposal_resolution(
                            runtime=runtime,
                            proposal_id=proposal_id_to_wait,
                            stop_event=stop_event,
                            poll_seconds=0.5,
                        )
                        if stop_event.is_set():
                            break
                        print()

                if stop_event.is_set():
                    break

                print(f"Cycle completed. Next check in {settings.proactive_comfort_interval_seconds} seconds.")
                stop_event.wait(settings.proactive_comfort_interval_seconds)

    finally:
        observability.shutdown()


if __name__ == "__main__":
    main()
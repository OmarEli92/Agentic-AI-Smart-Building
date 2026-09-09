import signal
from threading import Event
from uuid import uuid4

from dotenv import load_dotenv

from agentic_bim_iot.bootstrap import create_runtime
from agentic_bim_iot.config.settings import get_settings
from agentic_bim_iot.infrastracture.observability.logging_config import configure_application_logging
from agentic_bim_iot.infrastracture.observability.runtime import ObservabilityRuntime


def main():
    load_dotenv()
    settings = get_settings()
    logger = configure_application_logging(log_file_path=settings.log_file_path, level=settings.log_level)
    if not settings.proactive_comfort_enabled:
        print("Proactive comfort monitoring is disabled.")
        return
    observability = ObservabilityRuntime(settings=settings)
    stop_event = Event()
    def request_shutdown(signum, frame):
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

            print()
            print("=" * 70)
            print("PROACTIVE COMFORT MONITOR")
            print("=" * 70)
            print(f"Rooms: {', '.join(rooms)}")
            print(f"Interval: {settings.proactive_comfort_interval_seconds} seconds")
            print("=" * 70)
            print()

            while not stop_event.is_set():
                cycle_id = str(uuid4())
                print(f"Starting proactive cycle {cycle_id}")
                for room in rooms:
                    if stop_event.is_set():
                        break

                    request_id = str(uuid4())
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
                            result = runtime.proactive_monitor.check_room(room_reference=room, config={"callbacks": trace.callbacks})
                            trace.set_output(result.model_dump(mode="json"))

                        print(f"[{room}] {result.status.value}: {result.message}")

                    except Exception as exc:
                        print(f"[{room}] ERROR: {type(exc).__name__}: {exc}")
                        logger.exception("Proactive comfort check failed.", extra={"event": "proactive_check_failed", "request_id": request_id, "component": "proactive_monitor"})

                    finally:
                        observability.flush()
                if stop_event.is_set():
                    break
                print(f"Cycle completed. Next check in {settings.proactive_comfort_interval_seconds} seconds.")
                stop_event.wait(settings.proactive_comfort_interval_seconds)
    finally:
        observability.shutdown()


if __name__ == "__main__":
    main()
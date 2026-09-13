from uuid import uuid4
from dotenv import load_dotenv
from agentic_bim_iot.bootstrap import create_application
from agentic_bim_iot.config.settings import get_settings
from agentic_bim_iot.infrastructure.observability.logging_config import configure_application_logging
from agentic_bim_iot.infrastructure.observability.runtime import ObservabilityRuntime


def main():
    load_dotenv()
    settings = get_settings()
    logger = configure_application_logging(log_file_path=settings.log_file_path, level=settings.log_level)
    observability = ObservabilityRuntime(settings=settings)
    session_id = str(uuid4())
    logger.info("Application session started.", extra={"event": "session_started", "session_id": session_id})
    try:
        with create_application(settings) as graph:
            while True:
                user_query = input("> ").strip()
                if user_query.lower() in {"exit", "quit"}:
                    break
                if not user_query:
                    continue
                request_id = str(uuid4())
                logger.info("Facility Manager request started.",
                    extra={
                        "event": "request_started",
                        "request_id": request_id,
                        "session_id": session_id,
                    }
                )
                try:
                    with observability.trace_request(
                        request_id=request_id,
                        session_id=session_id,
                        user_query=user_query,
                        tags=["interactive"],
                        metadata={"run_context": "interactive"},
                    ) as trace:
                        result = graph.invoke(
                            {"user_query": user_query},
                            config={
                                "callbacks": trace.callbacks,
                                "run_name": "agentic-smart-building-graph",
                                "metadata": {"request_id": request_id, "session_id": session_id,},
                                "configurable": {"thread_id": session_id}
                            }
                        )
                        final_answer = result.get("final_answer", "")
                        trace.set_output({"final_answer": final_answer})
                    print(final_answer)
                    logger.info("Facility Manager request completed successfully.",
                        extra={
                            "event": "request_completed",
                            "request_id": request_id,
                            "session_id": session_id,
                        }
                    )
                except Exception:
                    logger.exception("Facility Manager request failed.",
                        extra={
                            "event": "request_failed",
                            "request_id": request_id,
                            "session_id": session_id,
                        }
                    )
                    raise
                finally:
                    observability.flush()
    finally:
        logger.info("Application session terminated.", extra={"event": "session_terminated","session_id": session_id})
        observability.shutdown()


if __name__ == "__main__":
    main()
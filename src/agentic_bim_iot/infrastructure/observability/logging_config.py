import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in (
                "event",
                "request_id",
                "session_id",
                "component",
                "tool_name",
                "tool_args",
                "tool_status",
                "duration_ms",
            ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_application_logging(log_file_path: str, level: str = "INFO") -> logging.Logger:
    path = Path(log_file_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("agentic_bim_iot")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False
    if logger.handlers:
        return logger
    handler = RotatingFileHandler(filename=path, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)
    return logger
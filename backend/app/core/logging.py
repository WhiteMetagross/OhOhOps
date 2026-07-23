"""Structured JSON logging for OhOhOps.

All application logs are emitted as single-line JSON to stdout so they can be
parsed downstream (and, in Phase 4, surfaced in the dashboard's log window). Use
``configure_logging()`` once at startup, then ``logging.getLogger("ohohops")``
anywhere in the app.

Extra fields can be attached per call via the ``extra=`` argument, e.g.
``logger.info("run finished", extra={"run_id": rid, "exit_code": 0})`` — they are
merged into the JSON payload.
"""

import json
import logging
import sys
from datetime import datetime, timezone

LOGGER_NAME = "ohohops"

# Attributes that exist on every LogRecord; anything else passed via `extra` is
# treated as a custom field and included in the JSON output.
_RESERVED = set(
    logging.makeLogRecord({}).__dict__.keys()
) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure the 'ohohops' logger to emit JSON to stdout. Idempotent."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)

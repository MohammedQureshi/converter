"""Request-scoped context: request ID, structured logging, and the conversion deadline."""

from __future__ import annotations

import json
import logging
import sys
import time
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone

from app.errors import ConversionTimeout

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
# What the per-request summary log line reports. Only these non-sensitive fields ever go in it.
request_summary_var: ContextVar[dict | None] = ContextVar("request_summary", default=None)


def note_request(**fields) -> None:
    summary = request_summary_var.get()
    if summary is not None:
        summary.update(fields)


class Deadline:
    """One time budget shared by every engine call in a request.

    A per-call timeout would let an email with many attachments hold a synchronous
    caller for many multiples of CONVERSION_TIMEOUT_SECONDS. Each call instead gets
    whatever is left, so the conversion as a whole stays within the limit.
    """

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds
        self._expires = time.monotonic() + seconds

    def remaining(self) -> float:
        left = self._expires - time.monotonic()
        if left <= 0:
            raise ConversionTimeout(f"Conversion exceeded the {self.seconds:g}s time limit")
        return left

    def timeout_error(self) -> ConversionTimeout:
        return ConversionTimeout(f"Conversion exceeded the {self.seconds:g}s time limit")


class JsonFormatter(logging.Formatter):
    """One JSON object per line, tagged with the request ID."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "requestId": request_id_var.get(),
            "msg": record.getMessage(),
        }
        extra = getattr(record, "fields", None)
        if extra:
            entry.update(extra)
        if record.exc_info and record.exc_info[0] is not None:
            # The exception's type and code locations only. Its message could quote a filename
            # or file contents, which must never reach the logs.
            entry["excType"] = record.exc_info[0].__name__
            entry["stack"] = [f"{f.filename}:{f.lineno}:{f.name}" for f in traceback.extract_tb(record.exc_info[2])]
        return json.dumps(entry, ensure_ascii=False, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers[:] = []
        uvicorn_logger.propagate = True
    for name in ("PIL", "fontTools", "extract_msg", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)

"""Real-time log error rate counter for the anomaly telemetry loop.

Attaches a lightweight ``logging.Handler`` to the root logger so that every
log record emitted anywhere in the application is captured in a sliding
time-window.  ``error_rate(window_seconds)`` then returns a genuine signal —
the fraction of ERROR/CRITICAL records among all records in that window —
rather than ``random.uniform(0.0, 1.0)``.

Design choices:
- **No external dependencies** — uses only stdlib ``logging`` and
  ``collections.deque``.
- **Thread/async-safe** — ``deque`` appends/pops are atomic under CPython's
  GIL, which is sufficient for the asyncio event loop and the small number of
  background threads uvicorn uses.
- **Singleton** — ``LogErrorCounter.install()`` is idempotent; calling it
  twice installs the handler only once.  ``get_instance()`` returns the same
  object for the lifetime of the process so tests can inject records without
  touching the actual logger hierarchy.

Usage
-----
In ``lifespan.py`` (before the ``yield``)::

    from app.anomaly.log_counter import LogErrorCounter
    LogErrorCounter.install()

In ``telemetry.py``::

    from app.anomaly.log_counter import LogErrorCounter
    error_rate = LogErrorCounter.get_instance().error_rate()
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Deque, Optional, Tuple

logger = logging.getLogger("ohohops.anomaly.log_counter")

# Level threshold — ERROR and above count as "errors"
_ERROR_THRESHOLD = logging.ERROR


class LogErrorCounter(logging.Handler):
    """Sliding-window log-error-rate counter.

    Records are stored as ``(timestamp_float, is_error_bool)`` tuples in a
    ``deque``.  Old records outside the window are evicted lazily on each
    ``error_rate()`` call so memory stays bounded without a background task.
    """

    _instance: Optional["LogErrorCounter"] = None

    def __init__(self, maxlen: int = 10_000) -> None:
        super().__init__(level=logging.DEBUG)  # capture everything
        # Each entry: (monotonic timestamp, is_error)
        self._records: Deque[Tuple[float, bool]] = deque(maxlen=maxlen)

    # ── Singleton helpers ──────────────────────────────────────────────────

    @classmethod
    def get_instance(cls) -> "LogErrorCounter":
        """Return the process-wide singleton, creating it if necessary."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def install(cls) -> "LogErrorCounter":
        """Attach the singleton handler to the root logger (idempotent).

        Safe to call multiple times — checks whether an instance is already
        registered before adding a second one.
        """
        instance = cls.get_instance()
        root = logging.getLogger()
        # Avoid double-registration (e.g., during test setup/teardown)
        if instance not in root.handlers:
            root.addHandler(instance)
            logger.debug("LogErrorCounter installed on root logger")
        return instance

    # ── logging.Handler interface ──────────────────────────────────────────

    def emit(self, record: logging.LogRecord) -> None:
        """Called by the logging framework for every record.

        We skip our own logger to avoid infinite recursion when
        ``logger.debug(...)`` above would re-enter ``emit``.
        """
        if record.name == "ohohops.anomaly.log_counter":
            return
        is_error = record.levelno >= _ERROR_THRESHOLD
        self._records.append((time.monotonic(), is_error))

    # ── Public API ─────────────────────────────────────────────────────────

    def error_rate(self, window_seconds: float = 60.0) -> float:
        """Return the fraction of ERROR/CRITICAL records in the last window.

        ``0.0`` means no errors; ``1.0`` means every log line was an error.
        Returns ``0.0`` when the window is empty (clean startup).

        Args:
            window_seconds: How far back to look, in seconds (monotonic clock).
        """
        cutoff = time.monotonic() - window_seconds
        total = 0
        errors = 0
        for ts, is_error in self._records:
            if ts >= cutoff:
                total += 1
                if is_error:
                    errors += 1

        if total == 0:
            return 0.0
        return errors / total

    def inject(self, level: int, ts: Optional[float] = None) -> None:
        """Test helper: directly insert a record without going through logging.

        Args:
            level: e.g. ``logging.ERROR`` or ``logging.INFO``.
            ts:    Monotonic timestamp; defaults to ``time.monotonic()``.
        """
        self._records.append((ts if ts is not None else time.monotonic(), level >= _ERROR_THRESHOLD))

    def reset(self) -> None:
        """Test helper: clear all stored records."""
        self._records.clear()

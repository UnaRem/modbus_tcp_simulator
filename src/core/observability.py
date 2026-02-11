from __future__ import annotations

import json
import logging
import math
import sys
import time
import uuid
from collections import deque
from threading import Lock
from datetime import datetime, timezone


class Logger:
    def __init__(self, name: str = "modbus-sim"):
        self.logger = logging.getLogger(name)
        self.logger.propagate = False
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def configure(self, level: str | None = None, output: str | None = None) -> None:
        if output:
            self.logger.handlers.clear()
            if output.lower() == "stderr":
                handler = logging.StreamHandler(stream=sys.stderr)
            elif output.lower() == "stdout":
                handler = logging.StreamHandler(stream=sys.stdout)
            else:
                handler = logging.FileHandler(output, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)
        if level:
            self.logger.setLevel(self._parse_level(level))

    @staticmethod
    def _parse_level(level: str) -> int:
        value = str(level or "").upper()
        if value == "DEBUG":
            return logging.DEBUG
        if value in ("WARN", "WARNING"):
            return logging.WARNING
        if value == "ERROR":
            return logging.ERROR
        if value == "CRITICAL":
            return logging.CRITICAL
        return logging.INFO

    def event(self, level: str, fields: dict) -> None:
        fields = dict(fields)
        fields.setdefault("ts", datetime.now(timezone.utc).isoformat())
        fields.setdefault("level", level.lower())
        fields.setdefault("trace_id", uuid.uuid4().hex)
        payload = json.dumps(fields, ensure_ascii=False)
        lvl = level.lower()
        if lvl in ("error", "fatal"):
            self.logger.error(payload)
        elif lvl in ("warn", "warning"):
            self.logger.warning(payload)
        else:
            self.logger.info(payload)


class Metrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, dict[str, float]] = {}
        self._windows: dict[str, deque[tuple[float, float]]] = {}
        self.window_s = 60.0

    def _key(self, name: str, tags: dict | None) -> str:
        if not tags:
            return name
        parts = [f"{k}={tags[k]}" for k in sorted(tags)]
        return f"{name}|{','.join(parts)}"

    def inc(self, name: str, value: float = 1.0, tags: dict | None = None) -> None:
        key = self._key(name, tags)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + float(value)

    def observe(self, name: str, value: float, tags: dict | None = None) -> None:
        key = self._key(name, tags)
        now = time.monotonic()
        with self._lock:
            stat = self._histograms.setdefault(
                key, {"count": 0.0, "sum": 0.0, "max": float("-inf"), "min": float("inf")}
            )
            stat["count"] += 1.0
            stat["sum"] += float(value)
            stat["max"] = max(stat["max"], float(value))
            stat["min"] = min(stat["min"], float(value))
            window = self._windows.setdefault(key, deque())
            window.append((now, float(value)))
            cutoff = now - self.window_s
            while window and window[0][0] < cutoff:
                window.popleft()

    def set(self, name: str, value: float, tags: dict | None = None) -> None:
        key = self._key(name, tags)
        with self._lock:
            self._gauges[key] = float(value)

    def snapshot(self) -> dict:
        with self._lock:
            histograms = {}
            now = time.monotonic()
            for key, stat in self._histograms.items():
                snap = dict(stat)
                window = self._windows.get(key) or deque()
                cutoff = now - self.window_s
                values = [val for ts, val in window if ts >= cutoff]
                if values:
                    values.sort()
                    idx = max(0, math.ceil(len(values) * 0.95) - 1)
                    snap["p95"] = values[idx]
                else:
                    snap["p95"] = None
                histograms[key] = snap
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": histograms,
            }

from __future__ import annotations

import threading
import time

from .observability import Logger, Metrics
from .scripting import ScriptRunner


class PhysicsEngine:
    def __init__(
        self,
        scripts: list[dict],
        runner: ScriptRunner,
        logger: Logger | None = None,
        metrics: Metrics | None = None,
    ):
        self.scripts = scripts
        self.runner = runner
        self.logger = logger or Logger("physics")
        self.metrics = metrics
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="physics", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self) -> None:
        compiled: list[dict] = []
        for item in self.scripts:
            if not item or not item.get("script"):
                continue
            if item.get("enabled", True) is False:
                continue
            try:
                code = self.runner.compile(item.get("script", ""))
                compiled.append(
                    {
                        "code": code,
                        "interval": float(item.get("interval", 1.0)),
                        "timeout_ms": int(item.get("timeout_ms", 100)),
                        "time_scale": float(item.get("time_scale", 1.0) or 1.0),
                        "next_run": time.monotonic(),
                        "last_run": None,
                        "error_count": 0,
                        "disabled": False,
                        "name": item.get("name") or "script",
                    }
                )
            except Exception as exc:
                self.logger.event("warn", {"msg": "script compile failed", "error": str(exc)})

        while not self._stop.is_set():
            if not compiled:
                time.sleep(0.5)
                continue
            now = time.monotonic()
            next_wake = now + 1.0
            for item in compiled:
                if item["disabled"]:
                    continue
                if now >= item["next_run"]:
                    start = time.monotonic()
                    last_run = item.get("last_run")
                    interval = float(item["interval"]) if item["interval"] else 1.0
                    if last_run is None:
                        dt_s = interval
                    else:
                        dt_s = now - float(last_run)
                    dt_s = min(dt_s, interval * 2)
                    scale = float(item.get("time_scale", 1.0) or 1.0)
                    if scale > 0:
                        dt_s *= scale
                    try:
                        self.runner.run(item["code"], item["timeout_ms"], {"dt_s": dt_s})
                        item["error_count"] = 0
                    except Exception as exc:
                        if self.metrics:
                            self.metrics.inc("script_errors_total", 1.0, {"name": item["name"]})
                        if isinstance(exc, TimeoutError):
                            item["disabled"] = True
                            self.logger.event(
                                "warn",
                                {"msg": "script timeout", "name": item["name"], "error": str(exc)},
                            )
                            self.logger.event(
                                "warn",
                                {"msg": "script disabled after timeout", "name": item["name"]},
                            )
                        else:
                            item["error_count"] += 1
                            self.logger.event(
                                "warn",
                                {"msg": "script run failed", "name": item["name"], "error": str(exc)},
                            )
                            if item["error_count"] >= 3:
                                item["disabled"] = True
                                self.logger.event(
                                    "warn",
                                    {"msg": "script disabled after errors", "name": item["name"]},
                                )
                    finally:
                        if self.metrics:
                            elapsed_ms = (time.monotonic() - start) * 1000.0
                            self.metrics.observe("script_latency_ms", elapsed_ms, {"name": item["name"]})
                    item["last_run"] = now
                    item["next_run"] = now + interval
                next_wake = min(next_wake, item["next_run"])
            sleep_s = max(0.05, next_wake - time.monotonic())
            time.sleep(sleep_s)

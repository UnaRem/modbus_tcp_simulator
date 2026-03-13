from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time

from .core.config import build_device_registry, load_config
from .core.errors import ConfigError
from .core.observability import Logger, Metrics
from .core.physics import PhysicsEngine
from .core.scripting import ScriptRunner
from .core.server import ModbusServer


class SimulatorRuntime:
    def __init__(self, config_path: str | Path, port_overrides: list[int] | None = None):
        self.config_path = Path(config_path)
        self.port_overrides = list(port_overrides or [])
        self.logger = Logger("app")
        self.server: ModbusServer | None = None
        self.engine: PhysicsEngine | None = None
        self.httpd: ThreadingHTTPServer | None = None
        self.metrics: Metrics | None = None
        self.registry = None
        self.cfg: dict | None = None
        self._stop_event = threading.Event()
        self._metrics_thread: threading.Thread | None = None
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._stop_event.clear()

        cfg = load_config(self.config_path)
        logging_cfg = cfg.get("logging") or {}
        self.logger.configure(logging_cfg.get("level"), logging_cfg.get("output"))

        listeners = cfg.get("listeners") or []
        if self.port_overrides:
            if not listeners:
                raise ConfigError("no listeners configured for port override")
            if len(self.port_overrides) == 1 and len(listeners) == 1:
                listeners[0]["port"] = self.port_overrides[0]
            elif len(self.port_overrides) == len(listeners):
                for listener, port in zip(listeners, self.port_overrides, strict=True):
                    listener["port"] = port
            else:
                raise ConfigError("port override count must match listeners or be single for one listener")

        metrics_cfg = cfg.get("metrics") or {}
        self.metrics = Metrics() if metrics_cfg.get("enabled", True) else None
        self.registry = build_device_registry(cfg, self.config_path.parent)
        self.server = ModbusServer(self.registry, self.logger, cfg.get("runtime") or {}, self.metrics)
        self.server.start_listeners(listeners)

        runner = ScriptRunner(self.registry, self.logger)
        self.engine = PhysicsEngine(cfg.get("simulation") or [], runner, self.logger, self.metrics)
        self.engine.start()

        if self.metrics and metrics_cfg.get("output", "log") == "log":
            interval_s = float(metrics_cfg.get("interval_s", 10))

            def _metrics_loop() -> None:
                while not self._stop_event.is_set():
                    time.sleep(interval_s)
                    self.logger.event("info", {"msg": "metrics", "metrics": self.metrics.snapshot()})

            self._metrics_thread = threading.Thread(target=_metrics_loop, daemon=True)
            self._metrics_thread.start()

        if self.metrics and metrics_cfg.get("output") == "http":
            address = metrics_cfg.get("address", "0.0.0.0")
            port = int(metrics_cfg.get("port", 9090))
            endpoint = metrics_cfg.get("endpoint", "/metrics")
            metrics = self.metrics

            class MetricsHandler(BaseHTTPRequestHandler):
                def do_GET(self) -> None:
                    if self.path != endpoint:
                        self.send_response(404)
                        self.end_headers()
                        return
                    payload = metrics.snapshot()
                    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)

                def log_message(self, format, *args):  # noqa: A002
                    return

            self.httpd = ThreadingHTTPServer((address, port), MetricsHandler)
            threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
            self.logger.event(
                "info",
                {"msg": "metrics http started", "address": address, "port": port, "endpoint": endpoint},
            )

        self.cfg = cfg
        self._started = True
        self.logger.event("info", {"msg": "modbus simulator started"})

    def stop(self) -> None:
        if not self._started:
            return
        self._stop_event.set()
        if self.engine:
            self.engine.stop()
        if self.server:
            self.server.stop()
        if self.httpd:
            self.httpd.shutdown()
        self._started = False
        self.logger.event("info", {"msg": "shutdown"})

    @property
    def started(self) -> bool:
        return self._started

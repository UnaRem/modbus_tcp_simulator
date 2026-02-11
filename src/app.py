from __future__ import annotations

import argparse
from pathlib import Path
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json

from .core.config import build_device_registry, load_config
from .core.errors import ConfigError
from .core.observability import Logger, Metrics
from .core.physics import PhysicsEngine
from .core.scripting import ScriptRunner
from .core.server import ModbusServer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="configs/example.yaml")
    parser.add_argument(
        "-p",
        "--port",
        action="append",
        help="Override listener port(s). Use multiple -p or comma-separated values.",
    )
    args = parser.parse_args()

    logger = Logger("app")
    server = None
    engine = None
    httpd = None
    stop_event = threading.Event()

    try:
        cfg_path = Path(args.config)
        cfg = load_config(cfg_path)

        logging_cfg = cfg.get("logging") or {}
        logger.configure(logging_cfg.get("level"), logging_cfg.get("output"))
        listeners = cfg.get("listeners") or []
        if args.port:
            ports: list[int] = []
            for raw in args.port:
                for part in str(raw).split(","):
                    part = part.strip()
                    if not part:
                        continue
                    try:
                        ports.append(int(part))
                    except ValueError as exc:
                        raise ConfigError(f"invalid port override: {part}") from exc
            if not listeners:
                raise ConfigError("no listeners configured for port override")
            if len(ports) == 1 and len(listeners) == 1:
                listeners[0]["port"] = ports[0]
            elif len(ports) == len(listeners):
                for listener, port in zip(listeners, ports, strict=True):
                    listener["port"] = port
            else:
                raise ConfigError("port override count must match listeners or be single for one listener")

        metrics_cfg = cfg.get("metrics") or {}
        metrics = Metrics() if metrics_cfg.get("enabled", True) else None
        registry = build_device_registry(cfg, cfg_path.parent)
        server = ModbusServer(registry, logger, cfg.get("runtime") or {}, metrics)
        server.start_listeners(cfg.get("listeners") or [])
        runner = ScriptRunner(registry, logger)
        engine = PhysicsEngine(cfg.get("simulation") or [], runner, logger, metrics)
        engine.start()

        if metrics and metrics_cfg.get("output", "log") == "log":
            interval_s = float(metrics_cfg.get("interval_s", 10))

            def _metrics_loop() -> None:
                while not stop_event.is_set():
                    time.sleep(interval_s)
                    logger.event("info", {"msg": "metrics", "metrics": metrics.snapshot()})

            threading.Thread(target=_metrics_loop, daemon=True).start()
        if metrics and metrics_cfg.get("output") == "http":
            address = metrics_cfg.get("address", "0.0.0.0")
            port = int(metrics_cfg.get("port", 9090))
            endpoint = metrics_cfg.get("endpoint", "/metrics")

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

            httpd = ThreadingHTTPServer((address, port), MetricsHandler)
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            logger.event("info", {"msg": "metrics http started", "address": address, "port": port, "endpoint": endpoint})

        logger.event("info", {"msg": "modbus simulator started"})
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
        if engine:
            engine.stop()
        if server:
            server.stop()
        if httpd:
            httpd.shutdown()
        logger.event("info", {"msg": "shutdown"})
    except Exception as exc:
        stop_event.set()
        if engine:
            engine.stop()
        if server:
            server.stop()
        if httpd:
            httpd.shutdown()
        logger.event("fatal", {"msg": "fatal error", "error": str(exc)})
        raise SystemExit(1)


if __name__ == "__main__":
    main()

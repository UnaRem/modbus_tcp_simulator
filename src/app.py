from __future__ import annotations

import argparse
from pathlib import Path
import time

from .core.errors import ConfigError
from .gui import launch_gui
from .runtime import SimulatorRuntime


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="configs/example.yaml")
    parser.add_argument(
        "-p",
        "--port",
        action="append",
        help="Override listener port(s). Use multiple -p or comma-separated values.",
    )
    parser.add_argument("--gui", action="store_true", help="Launch the desktop control GUI.")
    args = parser.parse_args()

    ports: list[int] = []
    if args.port:
        for raw in args.port:
            for part in str(raw).split(","):
                part = part.strip()
                if not part:
                    continue
                try:
                    ports.append(int(part))
                except ValueError as exc:
                    raise ConfigError(f"invalid port override: {part}") from exc

    runtime = SimulatorRuntime(Path(args.config), ports)

    try:
        if args.gui:
            launch_gui(runtime)
            return

        runtime.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        runtime.stop()
    except Exception as exc:
        runtime.stop()
        runtime.logger.event("fatal", {"msg": "fatal error", "error": str(exc)})
        raise SystemExit(1)


if __name__ == "__main__":
    main()

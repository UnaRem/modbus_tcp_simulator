from __future__ import annotations

from types import CodeType
from threading import Event, Thread
from typing import Any

from .errors import RegisterError, ScriptError
from .device import DeviceRegistry
from .observability import Logger


class ScriptRunner:
    def __init__(self, registry: DeviceRegistry, logger: Logger | None = None):
        self.registry = registry
        self.logger = logger or Logger("script")
        self.max_script_len = 64 * 1024
        self.max_vars = 256

    def compile(self, script: str) -> CodeType:
        if script and len(script) > self.max_script_len:
            raise ValueError("script too large")
        return compile(script, "<script>", "exec")

    def run(self, code_obj: CodeType, timeout_ms: int = 100, context: dict | None = None) -> None:
        api = {
            "get_value": self.get_value,
            "set_value": self.set_value,
            "get_bit": self.get_bit,
            "set_bit": self.set_bit,
            "get_meta": self.get_meta,
            "log": self.log,
            "min": min,
            "max": max,
            "abs": abs,
            "range": range,
        }
        locals_scope = dict(api)
        if context:
            locals_scope.update(context)
        base_count = len(locals_scope)
        done = Event()
        error: list[Exception | None] = [None]

        def _exec() -> None:
            try:
                exec(code_obj, {"__builtins__": {}}, locals_scope)
                extra = len(locals_scope) - base_count
                if self.max_vars and extra > self.max_vars:
                    raise ScriptError(f"too many variables: {extra} > {self.max_vars}")
            except Exception as exc:
                error[0] = exc
            finally:
                done.set()

        thread = Thread(target=_exec, daemon=True)
        thread.start()
        done.wait(timeout=max(0.001, timeout_ms / 1000.0))
        if not done.is_set():
            raise TimeoutError("script timeout")
        if error[0]:
            raise error[0]

    def get_value(self, device_name: str, address: int):
        device = self.registry.get_by_name(device_name)
        if not device:
            raise ScriptError(f"unknown device: {device_name}")
        try:
            return device.get_engineering_value(address)
        except RegisterError as exc:
            raise ScriptError(str(exc)) from exc

    def set_value(self, device_name: str, address: int, value) -> None:
        device = self.registry.get_by_name(device_name)
        if not device:
            raise ScriptError(f"unknown device: {device_name}")
        try:
            device.set_engineering_value(address, value)
        except RegisterError as exc:
            raise ScriptError(str(exc)) from exc

    def get_meta(self, device_name: str, address: int) -> dict[str, Any]:
        device = self.registry.get_by_name(device_name)
        if not device:
            return {}
        for store in device.stores.values():
            reg = store.get_def(address)
            if reg:
                return {
                    "name": reg.name,
                    "unit": reg.unit,
                    "scale": reg.scale,
                    "offset": reg.offset,
                    "access": reg.access,
                    "bits": dict(reg.bits or {}),
                }
        return {}

    def get_bit(self, device_name: str, address: int, bit_index: int) -> int:
        device = self.registry.get_by_name(device_name)
        if not device:
            raise ScriptError(f"unknown device: {device_name}")
        try:
            return device.get_bit(address, int(bit_index))
        except RegisterError as exc:
            raise ScriptError(str(exc)) from exc

    def set_bit(self, device_name: str, address: int, bit_index: int, value: int | bool) -> None:
        device = self.registry.get_by_name(device_name)
        if not device:
            raise ScriptError(f"unknown device: {device_name}")
        try:
            device.set_bit(address, int(bit_index), value)
        except RegisterError as exc:
            raise ScriptError(str(exc)) from exc

    def log(self, level: str, message: str) -> None:
        self.logger.event(level, {"msg": message})

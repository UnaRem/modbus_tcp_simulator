from __future__ import annotations

import threading
from typing import Iterable
import uuid
from dataclasses import dataclass, field

from pymodbus.constants import ExcCodes
from pymodbus.datastore import ModbusDeviceContext, ModbusServerContext, ModbusSparseDataBlock
from pymodbus.pdu import ExceptionResponse, ModbusPDU
from pymodbus.server import ModbusTcpServer
from pymodbus.server.requesthandler import ServerRequestHandler
import asyncio
import time
from collections import deque
from threading import Lock

from .bus import VirtualBus
from .errors import RegisterError
from .device import DeviceContext, DeviceRegistry
from .observability import Logger, Metrics


class RegisterDataBlock(ModbusSparseDataBlock):
    def __init__(
        self,
        device: DeviceContext,
        reg_type: str,
        address_base: int,
        listener_port: int,
        logger: Logger,
        limiter: "RateLimiter | None" = None,
        tracker: "ConnectionTracker | None" = None,
        request_timeout_ms: int | None = None,
    ):
        super().__init__({})
        self.device = device
        self.reg_type = reg_type
        self.address_base = address_base
        self.listener_port = listener_port
        self.logger = logger
        self.limiter = limiter
        self.tracker = tracker
        self.request_timeout_ms = request_timeout_ms or 0
        self.metrics: Metrics | None = None

    def validate(self, address: int, count: int = 1) -> bool:
        try:
            real = (address - 1) + self.address_base
            self.device.read_raw(self.reg_type, real, count)
            return True
        except RegisterError:
            return False

    def getValues(self, address: int, count: int = 1) -> list[int] | ExcCodes:
        real = (address - 1) + self.address_base
        trace_id = uuid.uuid4().hex
        start = time.monotonic()
        length_error = self._check_length("read", count)
        if length_error is not None:
            self._log_request("read", real, count, start, "error", length_error, trace_id)
            self._record_metrics("read", start, length_error)
            return ExcCodes.ILLEGAL_VALUE
        try:
            result = self.device.read_raw(self.reg_type, real, count)
            allow_error = self._allow_request()
            if allow_error is not None:
                self._log_request("read", real, count, start, "error", allow_error, trace_id)
                self._record_metrics("read", start, allow_error)
                return ExcCodes.DEVICE_BUSY
            self._log_request("read", real, count, start, "ok", None, trace_id)
            self._log_slow(start, "read", real, count, trace_id)
            self._record_metrics("read", start, None)
            return result
        except RegisterError as err:
            self._log_request("read", real, count, start, "error", err.code, trace_id, str(err))
            self._log_slow(start, "read", real, count, trace_id)
            self._record_metrics("read", start, err.code)
            return self._map_error(err)

    def setValues(self, address: int, values: Iterable[int]) -> None | ExcCodes:
        values = list(values)
        real = (address - 1) + self.address_base
        trace_id = uuid.uuid4().hex
        start = time.monotonic()
        length_error = self._check_length("write", len(values))
        if length_error is not None:
            self._log_request("write", real, len(values), start, "error", length_error, trace_id)
            self._record_metrics("write", start, length_error)
            return ExcCodes.ILLEGAL_VALUE
        try:
            self.device.validate_write(self.reg_type, real, values)
        except RegisterError as err:
            self._log_request("write", real, len(values), start, "error", err.code, trace_id, str(err))
            self._log_slow(start, "write", real, len(values), trace_id)
            self._record_metrics("write", start, err.code)
            return self._map_error(err)
        allow_error = self._allow_request()
        if allow_error is not None:
            self._log_request("write", real, len(values), start, "error", allow_error, trace_id)
            self._record_metrics("write", start, allow_error)
            return ExcCodes.DEVICE_BUSY
        try:
            self.device.write_raw(self.reg_type, real, values)
        except RegisterError as err:
            self._log_request("write", real, len(values), start, "error", err.code, trace_id, str(err))
            self._log_slow(start, "write", real, len(values), trace_id)
            self._record_metrics("write", start, err.code)
            return self._map_error(err)
        self._log_request("write", real, len(values), start, "ok", None, trace_id)
        self._log_slow(start, "write", real, len(values), trace_id)
        self._record_metrics("write", start, None)
        return None

    def _map_error(self, err: RegisterError) -> ExcCodes:
        if err.code == 0x02:
            return ExcCodes.ILLEGAL_ADDRESS
        if err.code == 0x03:
            return ExcCodes.ILLEGAL_VALUE
        if err.code == 0x06:
            return ExcCodes.DEVICE_BUSY
        return ExcCodes.DEVICE_FAILURE

    def _allow_request(self) -> int | None:
        if self.tracker and self.tracker.over_limit():
            return 0x06
        if self.limiter and not self.limiter.allow():
            return 0x06
        return None

    def _log_slow(self, start: float, op: str, address: int, count: int, trace_id: str) -> None:
        if not self.request_timeout_ms:
            return
        elapsed_ms = (time.monotonic() - start) * 1000.0
        if elapsed_ms > self.request_timeout_ms:
            self.logger.event(
                "warn",
                {
                    "msg": "slow request",
                    "listener_port": self.listener_port,
                    "slave_id": self.device.slave_id,
                    "fc": self._infer_fc(op, count),
                    "op": op,
                    "address": address,
                    "count": count,
                    "elapsed_ms": round(elapsed_ms, 2),
                    "trace_id": trace_id,
                },
            )

    def _log_request(
        self,
        op: str,
        address: int,
        count: int,
        start: float,
        status: str,
        error_code: int | None,
        trace_id: str,
        error: str | None = None,
    ) -> None:
        fc = self._infer_fc(op, count)
        elapsed_ms = (time.monotonic() - start) * 1000.0
        payload = {
            "msg": "modbus request",
            "listener_port": self.listener_port,
            "slave_id": self.device.slave_id,
            "fc": fc,
            "addr": address,
            "len": count,
            "status": status,
            "error_code": error_code,
            "latency_ms": round(elapsed_ms, 2),
            "trace_id": trace_id,
        }
        if error:
            payload["error"] = error
        if status == "error":
            self.logger.event("warn", payload)
        else:
            self.logger.event("info", payload)

    def _infer_fc(self, op: str, count: int) -> int:
        if op == "read":
            if self.reg_type == "holding":
                return 0x03
            if self.reg_type == "input":
                return 0x04
            if self.reg_type == "coil":
                return 0x01
            if self.reg_type == "discrete":
                return 0x02
        if op == "write":
            if self.reg_type == "holding":
                return 0x06 if count == 1 else 0x10
            if self.reg_type == "coil":
                return 0x05 if count == 1 else 0x0F
        return 0

    def _check_length(self, op: str, count: int) -> int | None:
        if count <= 0:
            return 0x03
        if op == "read" and self.reg_type in ("holding", "input") and count > 125:
            return 0x03
        if op == "write" and self.reg_type == "holding" and count > 123:
            return 0x03
        return None

    def _record_metrics(self, op: str, start: float | None, error_code: int | None) -> None:
        if not self.metrics:
            return
        self.metrics.inc("requests_total", 1.0, {"op": op})
        if error_code is not None:
            self.metrics.inc("modbus_errors_total", 1.0, {"code": error_code})
        if start is not None:
            elapsed_ms = (time.monotonic() - start) * 1000.0
            self.metrics.observe("request_latency_ms", elapsed_ms, {"op": op})


class RawResponse(ModbusPDU):
    def __init__(self, function_code: int, payload: bytes | None = None):
        super().__init__()
        self.function_code = int(function_code) & 0xFF
        self._payload = payload or b""

    def encode(self) -> bytes:
        return self._payload

    def decode(self, data: bytes) -> None:
        self._payload = data


class GuardedRequestHandler(ServerRequestHandler):
    async def handle_request(self):
        if not self.last_pdu:
            return
        allowed = getattr(self.server, "allowed_function_codes", None)
        if allowed is not None and self.last_pdu.function_code not in allowed:
            response = ExceptionResponse(
                self.last_pdu.function_code,
                exception_code=ExcCodes.ILLEGAL_FUNCTION,
            )
            response.transaction_id = self.last_pdu.transaction_id
            response.dev_id = self.last_pdu.dev_id
            self.server_send(response, self.last_addr)
            return
        bus = getattr(self.server, "bus", None)
        if bus is not None:
            raw_req = bytes([self.last_pdu.function_code]) + self.last_pdu.encode()
            raw_resp = bus.handle_request(raw_req, self.last_pdu.dev_id)
            if not raw_resp:
                return
            response = RawResponse(raw_resp[0], raw_resp[1:])
            response.transaction_id = self.last_pdu.transaction_id
            response.dev_id = self.last_pdu.dev_id
            self.server_send(response, self.last_addr)
            return
        await super().handle_request()


class GuardedModbusTcpServer(ModbusTcpServer):
    def __init__(
        self,
        *args,
        allowed_function_codes: set[int] | None = None,
        bus: VirtualBus | None = None,
        **kwargs,
    ):
        self.allowed_function_codes = allowed_function_codes
        self.bus = bus
        super().__init__(*args, **kwargs)

    def callback_new_connection(self):
        return GuardedRequestHandler(
            self,
            self.trace_packet,
            self.trace_pdu,
            self.trace_connect,
        )


@dataclass
class ListenerHandle:
    port: int
    thread: threading.Thread
    loop: asyncio.AbstractEventLoop | None = None
    server: GuardedModbusTcpServer | None = None
    ready: threading.Event = field(default_factory=threading.Event)


class RateLimiter:
    def __init__(self, max_qps: int, metrics: Metrics | None = None, tags: dict | None = None):
        self.max_qps = max_qps
        self._lock = Lock()
        self._times = deque()
        self.metrics = metrics
        self.tags = tags or {}

    def allow(self) -> bool:
        now = time.monotonic()
        with self._lock:
            while self._times and now - self._times[0] >= 1.0:
                self._times.popleft()
            if self.max_qps > 0 and len(self._times) >= self.max_qps:
                if self.metrics:
                    self.metrics.set("qps", float(len(self._times)), self.tags)
                return False
            self._times.append(now)
            if self.metrics:
                self.metrics.set("qps", float(len(self._times)), self.tags)
        return True


class ConnectionTracker:
    def __init__(self, max_connections: int, metrics: Metrics | None = None, tags: dict | None = None):
        self.max_connections = max_connections
        self._lock = Lock()
        self._count = 0
        self.metrics = metrics
        self.tags = tags or {}

    def trace(self, connected: bool) -> None:
        with self._lock:
            if connected:
                self._count += 1
            else:
                self._count = max(0, self._count - 1)
            if self.metrics:
                self.metrics.set("connections_current", float(self._count), self.tags)

    def over_limit(self) -> bool:
        if not self.max_connections or self.max_connections <= 0:
            return False
        with self._lock:
            return self._count > self.max_connections


class ModbusServer:
    def __init__(
        self,
        registry: DeviceRegistry,
        logger: Logger | None = None,
        runtime: dict | None = None,
        metrics: Metrics | None = None,
    ):
        self.registry = registry
        self.logger = logger or Logger("modbus")
        self.runtime = runtime or {}
        self.metrics = metrics
        self._listeners: list[ListenerHandle] = []

    def start_listeners(self, listeners: list[dict]) -> None:
        for listener in listeners:
            port = int(listener.get("port"))
            address_base = int(listener.get("address_base", 0))
            device_names = listener.get("devices") or []
            tags = {"port": port}
            limiter = RateLimiter(int(self.runtime.get("max_qps", 0) or 0), self.metrics, tags)
            tracker = ConnectionTracker(int(self.runtime.get("max_connections", 0) or 0), self.metrics, tags)
            request_timeout_ms = int(self.runtime.get("request_timeout_ms", 0) or 0)
            slaves = {}
            for name in device_names:
                dev = self.registry.get_by_name(name)
                if not dev:
                    continue
                slaves[dev.slave_id] = self._build_slave_context(
                    dev,
                    address_base,
                    port,
                    limiter,
                    tracker,
                    request_timeout_ms,
                )
            context = ModbusServerContext(devices=slaves, single=False)
            bus = VirtualBus(contexts=slaves, address_base=address_base, logger=self.logger)
            handle = ListenerHandle(port=port, thread=threading.Thread(target=lambda: None))

            def run_server() -> None:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def _serve() -> None:
                    server = GuardedModbusTcpServer(
                        context,
                        address=("0.0.0.0", port),
                        trace_connect=tracker.trace,
                        allowed_function_codes={0x03, 0x04, 0x06, 0x10},
                        bus=bus,
                    )
                    handle.loop = loop
                    handle.server = server
                    handle.ready.set()
                    await server.serve_forever()

                try:
                    loop.run_until_complete(_serve())
                except Exception as exc:
                    handle.ready.set()
                    self.logger.event("error", {"msg": "listener failed", "port": port, "error": str(exc)})
                finally:
                    try:
                        loop.run_until_complete(loop.shutdown_asyncgens())
                    finally:
                        loop.close()

            thread = threading.Thread(target=run_server, daemon=True)
            handle.thread = thread
            thread.start()
            ready = handle.ready.wait(timeout=5)
            self._listeners.append(handle)
            if not ready:
                self.logger.event("error", {"msg": "listener start timeout", "port": port})
            else:
                self.logger.event("info", {"msg": "listener started", "port": port, "slaves": list(slaves.keys())})

    def stop(self) -> None:
        for handle in self._listeners:
            if handle.server and handle.loop:
                try:
                    future = asyncio.run_coroutine_threadsafe(handle.server.shutdown(), handle.loop)
                    future.result(timeout=2)
                except Exception as exc:
                    self.logger.event("warn", {"msg": "listener shutdown failed", "port": handle.port, "error": str(exc)})
        for handle in self._listeners:
            if handle.thread:
                handle.thread.join(timeout=2)
        self._listeners.clear()

    def _build_slave_context(
        self,
        device: DeviceContext,
        address_base: int,
        listener_port: int,
        limiter: RateLimiter,
        tracker: ConnectionTracker,
        request_timeout_ms: int,
    ) -> ModbusDeviceContext:
        holding = RegisterDataBlock(
            device, "holding", address_base, listener_port, self.logger, limiter, tracker, request_timeout_ms
        )
        input_regs = RegisterDataBlock(
            device, "input", address_base, listener_port, self.logger, limiter, tracker, request_timeout_ms
        )
        coils = RegisterDataBlock(
            device, "coil", address_base, listener_port, self.logger, limiter, tracker, request_timeout_ms
        )
        discretes = RegisterDataBlock(
            device, "discrete", address_base, listener_port, self.logger, limiter, tracker, request_timeout_ms
        )
        for block in (holding, input_regs, coils, discretes):
            block.metrics = self.metrics
        return ModbusDeviceContext(hr=holding, ir=input_regs, co=coils, di=discretes)

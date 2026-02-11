from __future__ import annotations

import struct
from typing import Iterable

from pymodbus.constants import ExcCodes
from pymodbus.datastore import ModbusDeviceContext

from .errors import RegisterError
from .models import DeviceContext
from .observability import Logger


class VirtualBus:
    """轻量虚拟总线：负责按 SlaveID 路由并处理基础 Modbus 请求。"""

    def __init__(
        self,
        devices: Iterable[DeviceContext] | None = None,
        contexts: dict[int, ModbusDeviceContext] | None = None,
        address_base: int = 0,
        logger: Logger | None = None,
    ):
        self.address_base = int(address_base or 0)
        self.logger = logger or Logger("bus")
        self._devices: dict[int, DeviceContext] = {dev.slave_id: dev for dev in (devices or [])}
        self._contexts = contexts or {}

    def route(self, unit_id: int) -> DeviceContext:
        dev = self._devices.get(int(unit_id))
        if not dev:
            raise RegisterError(0x02, "unknown device")
        return dev

    def handle_request(self, pdu: bytes, unit_id: int) -> bytes:
        if not pdu:
            return b""
        fc = pdu[0]
        if fc not in (0x03, 0x04, 0x06, 0x10):
            return self._exception(fc, 0x01)
        try:
            if fc in (0x03, 0x04):
                return self._handle_read(fc, pdu, unit_id)
            if fc == 0x06:
                return self._handle_write_single(pdu, unit_id)
            return self._handle_write_multiple(pdu, unit_id)
        except RegisterError as err:
            if str(err) == "unknown device":
                return b""
            return self._exception(fc, err.code)

    def _handle_read(self, fc: int, pdu: bytes, unit_id: int) -> bytes:
        if len(pdu) < 5:
            return self._exception(fc, 0x03)
        address, count = struct.unpack(">HH", pdu[1:5])
        if count <= 0 or count > 125:
            return self._exception(fc, 0x03)
        values = self._read_values(unit_id, fc, address, count)
        payload = bytearray([fc, len(values) * 2])
        for value in values:
            payload.extend(struct.pack(">H", value & 0xFFFF))
        return bytes(payload)

    def _handle_write_single(self, pdu: bytes, unit_id: int) -> bytes:
        if len(pdu) < 5:
            return self._exception(0x06, 0x03)
        address, value = struct.unpack(">HH", pdu[1:5])
        self._write_values(unit_id, 0x06, address, [value])
        return bytes(pdu[:5])

    def _handle_write_multiple(self, pdu: bytes, unit_id: int) -> bytes:
        if len(pdu) < 6:
            return self._exception(0x10, 0x03)
        address, count, byte_count = struct.unpack(">HHB", pdu[1:6])
        if count <= 0 or count > 123:
            return self._exception(0x10, 0x03)
        expected_bytes = count * 2
        if byte_count != expected_bytes or len(pdu) < 6 + expected_bytes:
            return self._exception(0x10, 0x03)
        values = []
        offset = 6
        for _ in range(count):
            values.append(struct.unpack(">H", pdu[offset:offset + 2])[0])
            offset += 2
        self._write_values(unit_id, 0x10, address, values)
        return bytes([0x10]) + struct.pack(">HH", address, count)

    @staticmethod
    def _exception(fc: int, code: int) -> bytes:
        return bytes([(fc | 0x80) & 0xFF, code & 0xFF])

    def _read_values(self, unit_id: int, fc: int, address: int, count: int) -> list[int]:
        if self._contexts:
            ctx = self._contexts.get(int(unit_id))
            if not ctx:
                raise RegisterError(0x02, "unknown device")
            result = ctx.getValues(fc, address, count)
            if isinstance(result, ExcCodes):
                raise RegisterError(int(result), "modbus error")
            return result
        reg_type = "holding" if fc == 0x03 else "input"
        device = self.route(unit_id)
        real = address + self.address_base
        return device.read_raw(reg_type, real, count)

    def _write_values(self, unit_id: int, fc: int, address: int, values: list[int]) -> None:
        if self._contexts:
            ctx = self._contexts.get(int(unit_id))
            if not ctx:
                raise RegisterError(0x02, "unknown device")
            result = ctx.setValues(fc, address, values)
            if isinstance(result, ExcCodes):
                raise RegisterError(int(result), "modbus error")
            return
        device = self.route(unit_id)
        real = address + self.address_base
        device.write_raw("holding", real, values)

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Iterable

from .encoding import decode_value, encode_value
from .errors import RegisterError

__all__ = ["RegisterDef", "RegisterStore", "DeviceContext", "DeviceRegistry"]


@dataclass
class RegisterDef:
    address: int
    name: str
    reg_type: str
    data_type: str
    access: str
    scale: float = 1.0
    offset: float = 0.0
    unit: str | None = None
    default: float | int | str | None = None
    min: float | int | None = None
    max: float | int | None = None
    endian: str = "be"
    length: int = 1
    bits: dict[int, str] = field(default_factory=dict)
    comment: str | None = None


class RegisterStore:
    def __init__(self, defs: Iterable[RegisterDef]):
        self.defs = list(defs)
        self._by_addr: dict[int, RegisterDef] = {}
        self._values: dict[int, int] = {}
        self._lock = RLock()

        for reg in self.defs:
            length = max(1, int(reg.length))
            for offset in range(length):
                addr = reg.address + offset
                self._by_addr[addr] = reg
                self._values.setdefault(addr, 0)

        for reg in self.defs:
            if reg.default is None:
                continue
            raw = encode_value(reg.data_type, reg.default, reg.length, reg.endian)
            for i, val in enumerate(raw):
                self._values[reg.address + i] = int(val)

    def has_address(self, address: int) -> bool:
        return address in self._by_addr

    def get_def(self, address: int) -> RegisterDef | None:
        return self._by_addr.get(address)

    def read_raw(self, address: int, count: int) -> list[int]:
        if count <= 0:
            raise RegisterError(0x03, "invalid count")
        with self._lock:
            for i in range(count):
                if (address + i) not in self._by_addr:
                    raise RegisterError(0x02, "illegal address")
            return [self._values.get(address + i, 0) for i in range(count)]

    def validate_write(self, address: int, values: Iterable[int]) -> None:
        values = list(values)
        if not values:
            return
        with self._lock:
            self._validate_write_locked(address, values)

    def write_raw(self, address: int, values: Iterable[int]) -> None:
        values = list(values)
        if not values:
            return
        with self._lock:
            self._validate_write_locked(address, values)
            for i, raw in enumerate(values):
                addr = address + i
                self._values[addr] = int(raw) & 0xFFFF

    def _validate_write_locked(self, address: int, values: list[int]) -> None:
        addr_map = {address + i: int(raw) & 0xFFFF for i, raw in enumerate(values)}
        impacted: dict[int, RegisterDef] = {}
        for addr in addr_map:
            reg = self._by_addr.get(addr)
            if not reg:
                raise RegisterError(0x02, "illegal address")
            impacted[reg.address] = reg

        for reg in impacted.values():
            if reg.access == "ro":
                raise RegisterError(0x03, "read only")

            raw_values: list[int] = []
            for offset in range(max(1, int(reg.length))):
                addr = reg.address + offset
                if addr in addr_map:
                    raw_values.append(addr_map[addr])
                else:
                    raw_values.append(self._values.get(addr, 0))

            if reg.min is None and reg.max is None:
                continue

            value = decode_value(reg.data_type, raw_values, reg.endian)
            if not isinstance(value, (int, float)):
                continue
            if reg.min is not None and value < reg.min:
                raise RegisterError(0x03, "value too low")
            if reg.max is not None and value > reg.max:
                raise RegisterError(0x03, "value too high")

    def get_engineering_value(self, base_address: int) -> float | int | str:
        reg = self._by_addr.get(base_address)
        if not reg:
            raise RegisterError(0x02, "illegal address")
        raw = self.read_raw(reg.address, reg.length)
        val = decode_value(reg.data_type, raw, reg.endian)
        if isinstance(val, (int, float)):
            return (val * reg.scale) + reg.offset
        return val

    def set_engineering_value(self, base_address: int, value) -> None:
        reg = self._by_addr.get(base_address)
        if not reg:
            raise RegisterError(0x02, "illegal address")
        if reg.access == "ro":
            raise RegisterError(0x03, "read only")
        if isinstance(value, (int, float)):
            raw_val = (float(value) - reg.offset) / (reg.scale or 1.0)
        else:
            raw_val = value
        raw = encode_value(reg.data_type, raw_val, reg.length, reg.endian)
        self.write_raw(reg.address, raw)


class DeviceContext:
    def __init__(self, name: str, slave_id: int, stores: dict[str, RegisterStore]):
        self.name = name
        self.slave_id = slave_id
        self.stores = stores
        self.lock = RLock()

    def get_store(self, reg_type: str) -> RegisterStore:
        return self.stores.get(reg_type) or RegisterStore([])

    def read_raw(self, reg_type: str, address: int, count: int) -> list[int]:
        with self.lock:
            return self.get_store(reg_type).read_raw(address, count)

    def write_raw(self, reg_type: str, address: int, values: Iterable[int]) -> None:
        with self.lock:
            self.get_store(reg_type).write_raw(address, values)

    def validate_write(self, reg_type: str, address: int, values: Iterable[int]) -> None:
        with self.lock:
            self.get_store(reg_type).validate_write(address, values)

    def get_engineering_value(self, address: int):
        with self.lock:
            for store in self.stores.values():
                if store.has_address(address):
                    return store.get_engineering_value(address)
        raise RegisterError(0x02, "illegal address")

    def set_engineering_value(self, address: int, value) -> None:
        with self.lock:
            for store in self.stores.values():
                if store.has_address(address):
                    return store.set_engineering_value(address, value)
        raise RegisterError(0x02, "illegal address")


class DeviceRegistry:
    def __init__(self, devices: list[DeviceContext]):
        self.by_name = {d.name: d for d in devices}
        self.by_slave_id: dict[int, list[DeviceContext]] = {}
        for dev in devices:
            self.by_slave_id.setdefault(dev.slave_id, []).append(dev)

    def get_by_name(self, name: str) -> DeviceContext | None:
        return self.by_name.get(name)

    def get_by_slave_id(self, slave_id: int) -> DeviceContext | None:
        items = self.by_slave_id.get(slave_id) or []
        if len(items) == 1:
            return items[0]
        return None

    def get_all_by_slave_id(self, slave_id: int) -> list[DeviceContext]:
        return list(self.by_slave_id.get(slave_id) or [])

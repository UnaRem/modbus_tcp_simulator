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
        self._by_base: dict[int, RegisterDef] = {}
        self._covers: dict[int, list[RegisterDef]] = {}
        self._values: dict[int, int] = {}
        self._lock = RLock()

        for reg in self.defs:
            length = max(1, int(reg.length))
            self._by_base.setdefault(reg.address, reg)
            for offset in range(length):
                addr = reg.address + offset
                self._covers.setdefault(addr, []).append(reg)
                self._values.setdefault(addr, 0)

        for reg in self.defs:
            if reg.default is None:
                continue
            raw = encode_value(reg.data_type, reg.default, reg.length, reg.endian)
            for i, val in enumerate(raw):
                self._values[reg.address + i] = int(val)

    def has_address(self, address: int) -> bool:
        return address in self._covers

    def get_def(self, address: int) -> RegisterDef | None:
        reg = self._by_base.get(address)
        if reg:
            return reg
        regs = self._covers.get(address) or []
        return self._pick_preferred(regs)

    def read_raw(self, address: int, count: int) -> list[int]:
        if count <= 0:
            raise RegisterError(0x03, "invalid count")
        with self._lock:
            for i in range(count):
                if (address + i) not in self._covers:
                    raise RegisterError(0x02, "illegal address")
            return [self._values.get(address + i, 0) for i in range(count)]

    def get_bit(self, address: int, bit_index: int) -> int:
        reg = self._by_base.get(address) or self._select_reg_for_address(address)
        if not reg:
            raise RegisterError(0x02, "illegal address")
        if (
            reg.reg_type not in ("coil", "discrete")
            and reg.data_type not in ("int16", "uint16", "int32", "uint32")
            and not (reg.bits and len(reg.bits) > 0)
        ):
            raise RegisterError(0x03, "bit not supported")
        width = self._bit_width(reg)
        if bit_index < 0 or bit_index >= width:
            raise RegisterError(0x03, "bit out of range")
        raw = self.read_raw(reg.address, reg.length)
        value = self._raw_to_uint(reg, raw)
        return 1 if ((value >> bit_index) & 0x1) else 0

    def set_bit(self, address: int, bit_index: int, value: int | bool) -> None:
        reg = self._by_base.get(address) or self._select_reg_for_address(address)
        if not reg:
            raise RegisterError(0x02, "illegal address")
        if reg.access == "ro":
            raise RegisterError(0x03, "read only")
        if (
            reg.reg_type not in ("coil", "discrete")
            and reg.data_type not in ("int16", "uint16", "int32", "uint32")
            and not (reg.bits and len(reg.bits) > 0)
        ):
            raise RegisterError(0x03, "bit not supported")
        width = self._bit_width(reg)
        if bit_index < 0 or bit_index >= width:
            raise RegisterError(0x03, "bit out of range")
        raw = self.read_raw(reg.address, reg.length)
        current = self._raw_to_uint(reg, raw)
        mask = 1 << bit_index
        if int(value):
            current |= mask
        else:
            current &= ~mask
        new_raw = encode_value(self._bit_data_type(reg), current, reg.length, reg.endian)
        self.write_raw(reg.address, new_raw)

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
            reg = self._select_reg_for_address(addr)
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
        reg = self._by_base.get(base_address) or self._select_reg_for_address(base_address)
        if not reg:
            raise RegisterError(0x02, "illegal address")
        raw = self.read_raw(reg.address, reg.length)
        val = decode_value(reg.data_type, raw, reg.endian)
        if isinstance(val, (int, float)):
            return (val * reg.scale) + reg.offset
        return val

    def set_engineering_value(self, base_address: int, value) -> None:
        reg = self._by_base.get(base_address) or self._select_reg_for_address(base_address)
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

    @staticmethod
    def _bit_data_type(reg: RegisterDef) -> str:
        if reg.length and int(reg.length) > 1:
            return "uint32"
        return "uint16"

    @staticmethod
    def _bit_width(reg: RegisterDef) -> int:
        length = max(1, int(reg.length or 1))
        if reg.reg_type in ("coil", "discrete"):
            return 1
        return 16 * length

    def _raw_to_uint(self, reg: RegisterDef, raw: list[int]) -> int:
        data_type = self._bit_data_type(reg)
        value = decode_value(data_type, raw, reg.endian)
        if data_type == "uint16":
            return int(value) & 0xFFFF
        return int(value) & 0xFFFFFFFF

    def _select_reg_for_address(self, address: int) -> RegisterDef | None:
        reg = self._by_base.get(address)
        if reg:
            return reg
        regs = self._covers.get(address) or []
        return self._pick_preferred(regs)

    @staticmethod
    def _pick_preferred(regs: list[RegisterDef]) -> RegisterDef | None:
        if not regs:
            return None
        return min(regs, key=lambda reg: max(1, int(reg.length)))


class DeviceContext:
    def __init__(
        self,
        name: str,
        slave_id: int,
        stores: dict[str, RegisterStore],
        profile_name: str | None = None,
        read_fc: int | None = None,
        write_fc: int | None = None,
        allowed_function_codes: set[int] | None = None,
    ):
        self.name = name
        self.slave_id = slave_id
        self.stores = stores
        self.lock = RLock()
        self.profile_name = profile_name
        self.read_fc = read_fc
        self.write_fc = write_fc
        self.allowed_function_codes = allowed_function_codes

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

    def get_bit(self, address: int, bit_index: int) -> int:
        with self.lock:
            for store in self.stores.values():
                if store.has_address(address):
                    return store.get_bit(address, bit_index)
        raise RegisterError(0x02, "illegal address")

    def set_bit(self, address: int, bit_index: int, value: int | bool) -> None:
        with self.lock:
            for store in self.stores.values():
                if store.has_address(address):
                    return store.set_bit(address, bit_index, value)
        raise RegisterError(0x02, "illegal address")

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

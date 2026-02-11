from __future__ import annotations

import struct
from typing import Iterable


def _to_uint16(value: int) -> int:
    return value & 0xFFFF


def encode_value(data_type: str, value, length: int, endian: str = "be") -> list[int]:
    if data_type == "string":
        raw = (value or "").encode("utf-8", errors="ignore")
        raw = raw[: length * 2]
        raw = raw.ljust(length * 2, b"\x00")
        regs = []
        for i in range(0, len(raw), 2):
            regs.append(int.from_bytes(raw[i:i+2], byteorder="big"))
        return regs

    if data_type in ("int16", "uint16"):
        iv = int(value)
        return [_to_uint16(iv)]

    if data_type in ("int32", "uint32"):
        iv = int(value)
        raw = iv & 0xFFFFFFFF
        if endian == "le":
            return [_to_uint16(raw), _to_uint16(raw >> 16)]
        return [_to_uint16(raw >> 16), _to_uint16(raw)]

    if data_type == "float32":
        fv = float(value)
        raw = struct.pack(">f", fv)
        hi = int.from_bytes(raw[0:2], "big")
        lo = int.from_bytes(raw[2:4], "big")
        if endian == "le":
            return [lo, hi]
        return [hi, lo]

    iv = int(value)
    return [_to_uint16(iv)] 


def decode_value(data_type: str, regs: Iterable[int], endian: str = "be"):
    regs = list(regs)
    if data_type == "string":
        raw = b"".join(int(r).to_bytes(2, "big") for r in regs)
        return raw.rstrip(b"").decode("utf-8", errors="ignore")

    if data_type in ("int16", "uint16"):
        v = regs[0] if regs else 0
        if data_type == "int16" and v >= 0x8000:
            v -= 0x10000
        return v

    if data_type in ("int32", "uint32"):
        if len(regs) < 2:
            return 0
        if endian == "le":
            raw = (regs[1] << 16) | regs[0]
        else:
            raw = (regs[0] << 16) | regs[1]
        if data_type == "int32" and raw >= 0x80000000:
            raw -= 0x100000000
        return raw

    if data_type == "float32":
        if len(regs) < 2:
            return 0.0
        if endian == "le":
            raw = regs[1].to_bytes(2, "big") + regs[0].to_bytes(2, "big")
        else:
            raw = regs[0].to_bytes(2, "big") + regs[1].to_bytes(2, "big")
        return struct.unpack(">f", raw)[0]

    return regs[0] if regs else 0

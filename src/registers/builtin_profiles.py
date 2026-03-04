from __future__ import annotations

from typing import Iterable

from .pcs_register_map import (
    load_pcs_register_map,
    READ_REGISTER as PCS_READ_REGISTER,
    WRITE_REGISTER as PCS_WRITE_REGISTER,
)
from .bms_pw_100261a_register_map import (
    load_bms_pw_100261a_register_map,
    READ_REGISTER as PW_READ_REGISTER,
    WRITE_REGISTER as PW_WRITE_REGISTER,
)
from .bms_cimc_ess_832_314_register_map import (
    load_bms_cimc_ess_832_314_register_map,
    READ_REGISTER as CIMC_READ_REGISTER,
    WRITE_REGISTER as CIMC_WRITE_REGISTER,
)


_TYPE_ALIASES = {
    "u16": "uint16",
    "u32": "uint32",
    "i16": "int16",
    "i32": "int32",
    "float": "float32",
}

_ACCESS_ORDER = {"ro": 0, "wo": 1, "rw": 2}


def _normalize_access(value: str | None) -> str:
    if not value:
        return "rw"
    raw = str(value).strip().lower()
    raw = raw.replace(" ", "").replace("/", "").replace("\\", "")
    if raw in ("r", "ro", "read"):
        return "ro"
    if raw in ("w", "wo", "write"):
        return "wo"
    if "r" in raw and "w" in raw:
        return "rw"
    return "rw"


def _merge_access(current: str, incoming: str) -> str:
    if _ACCESS_ORDER.get(incoming, 0) > _ACCESS_ORDER.get(current, 0):
        return incoming
    return current


def _normalize_data_type(value: str | None, length: int, is_bitfield: bool) -> str:
    if is_bitfield:
        return "uint32" if int(length or 1) > 1 else "uint16"
    if not value:
        return "int16"
    raw = str(value).strip().lower()
    if raw == "bitfield":
        return "uint32" if int(length or 1) > 1 else "uint16"
    if raw == "enum16":
        return "enum16"
    return _TYPE_ALIASES.get(raw, raw)


def _register_name(label: str | None, fallback: str | None, address: int) -> str:
    if label:
        return str(label)
    if fallback:
        return str(fallback)
    return f"reg_{address}"


def _build_registers(
    defs: Iterable[object],
    *,
    label_attr: str,
    name_attr: str,
    access_attr: str,
    reg_type_resolver=None,
    length_resolver=None,
) -> list[dict]:
    entries: dict[int, dict] = {}
    for item in defs:
        address = int(getattr(item, "address"))
        length = int(getattr(item, "length", 1) or 1)
        if length_resolver:
            length = int(length_resolver(item, length) or 1)
        raw_type = getattr(item, "data_type", None)
        bit_index = getattr(item, "bit_index", None)
        is_bitfield = raw_type == "bitfield" or bit_index is not None
        data_type = _normalize_data_type(raw_type, length, is_bitfield)
        access = _normalize_access(getattr(item, access_attr, None))
        label = getattr(item, label_attr, None)
        field_name = getattr(item, name_attr, None)
        name = _register_name(label, field_name, address)
        unit = getattr(item, "unit", None)
        scale = getattr(item, "scale", None)
        scale = float(scale) if scale not in (None, "") else 1.0

        reg_type = reg_type_resolver(item, access) if reg_type_resolver else "holding"

        if is_bitfield:
            entry = entries.get(address)
            if entry is None:
                entry = {
                    "address": address,
                    "name": name,
                    "reg_type": reg_type,
                    "data_type": data_type,
                    "access": access,
                }
                if unit:
                    entry["unit"] = unit
                if scale != 1.0:
                    entry["scale"] = scale
                if data_type in ("int32", "uint32", "float32"):
                    entry["length"] = 2
                entries[address] = entry
            else:
                entry["access"] = _merge_access(entry.get("access", "rw"), access)
            if bit_index is not None:
                entry.setdefault("bits", {})[int(bit_index)] = name
            continue

        entry = {
            "address": address,
            "name": name,
            "reg_type": reg_type,
            "data_type": data_type,
            "access": access,
        }
        if unit:
            entry["unit"] = unit
        if scale != 1.0:
            entry["scale"] = scale
        if data_type == "string":
            entry["length"] = length
        elif data_type in ("int32", "uint32", "float32"):
            entry["length"] = 2
        elif length != 1:
            entry["length"] = length
        entries[address] = entry

    return [entries[address] for address in sorted(entries)]


def load_builtin_profiles() -> dict[str, dict]:
    profiles: dict[str, dict] = {}
    pcs_models = {
        "SP30HBG2": "sinosoar-pcs-sp30hbg2",
        "SP60HBG2": "sinosoar-pcs-sp60hbg2",
        "SP100HX": "sinosoar-pcs-sp100hx",
        "SP125HX": "sinosoar-pcs-sp125hx",
    }
    for model, profile_name in pcs_models.items():
        regs = load_pcs_register_map(model=model)
        profiles[profile_name] = {
            "description": f"builtin from pcs_register_map ({model})",
            "read_fc": PCS_READ_REGISTER,
            "write_fc": PCS_WRITE_REGISTER,
            "ignore_fallback": True,
            "allow_overlap": True,
            "registers": _build_registers(
                regs,
                label_attr="label_cn",
                name_attr="field_name",
                access_attr="attribute",
            ),
        }

    profiles["pw-100261a"] = {
        "description": "builtin from bms_pw_100261a_register_map",
        "read_fc": PW_READ_REGISTER,
        "write_fc": PW_WRITE_REGISTER,
        "ignore_fallback": True,
        "allow_overlap": True,
        "registers": _build_registers(
            load_bms_pw_100261a_register_map(),
            label_attr="label_cn",
            name_attr="field_name",
            access_attr="attribute",
        ),
    }
    def _cimc_reg_type(_, access: str) -> str:
        return "holding"

    profiles["cimc-ess-832-314-dc-c"] = {
        "description": "builtin from bms_cimc_ess_832_314_register_map",
        "read_fc": CIMC_READ_REGISTER,
        "write_fc": CIMC_WRITE_REGISTER,
        "mirror_input_to_holding": True,
        "ignore_fallback": True,
        "allow_overlap": True,
        "registers": _build_registers(
            load_bms_cimc_ess_832_314_register_map(),
            label_attr="label_cn",
            name_attr="field_name",
            access_attr="attribute",
            reg_type_resolver=_cimc_reg_type,
        ),
    }
    return profiles

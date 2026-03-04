from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
import yaml

from .errors import ConfigError
from .device import DeviceContext, DeviceRegistry, RegisterDef, RegisterStore
from ..registers.builtin_profiles import load_builtin_profiles


_DATA_TYPE_ALIASES = {
    "enum16": "uint16",
}


def _normalize_data_type(value: str | None) -> str:
    if value is None:
        return "int16"
    raw = str(value).strip().lower()
    return _DATA_TYPE_ALIASES.get(raw, raw)


_FLOAT32_MAX = 3.4028235e38
_DOC_PATH_RE = re.compile(r"docs/[^\s)]+\.md", re.IGNORECASE)


def _normalize_header(value: str | None) -> str:
    return re.sub(r"[\s（）()]+", "", str(value or "")).lower()


_ADDRESS_HEADER_KEYS = {
    "address",
    "addr",
    "绝对地址",
    "绝对地址10进制",
    "地址",
    "寄存器地址",
}


def _resolve_doc_path(description: str | None, base_dir: Path) -> Path | None:
    if not description:
        return None
    match = _DOC_PATH_RE.search(description)
    if not match:
        return None
    return _resolve_path(base_dir, match.group(0))


def _doc_columns_for_profile(profile_name: str, doc_path: Path | None) -> list[str]:
    name = (profile_name or "").lower()
    path = str(doc_path or "").lower()
    if "sinosoar" in name or "pcs" in name or "sinosoar" in path:
        return ["precision", "精度"]
    if "cimc" in name or "cimc" in path:
        return ["定义", "definition", "comment"]
    if "pw-100261a" in name or "pw-100261a" in path or "pw" in name or "pw" in path:
        return ["数据解析", "注释"]
    return []


def _parse_addr_cell(text: str) -> list[int]:
    value = str(text or "").strip()
    if not value:
        return []
    range_match = re.match(r"^\s*(0x[0-9a-fA-F]+|\d+)\s*[-~～]\s*(0x[0-9a-fA-F]+|\d+)\s*$", value)
    def _parse_num(raw: str) -> int:
        raw = raw.strip()
        if raw.lower().startswith("0x"):
            return int(raw, 16)
        return int(raw)

    if range_match:
        start = _parse_num(range_match.group(1))
        end = _parse_num(range_match.group(2))
        if end < start:
            start, end = end, start
        return list(range(start, end + 1))
    single = re.search(r"(0x[0-9a-fA-F]+|\d+)", value)
    if single:
        return [_parse_num(single.group(1))]
    return []


def _load_doc_comment_map(path: Path, columns: list[str]) -> dict[int, str]:
    if not path or not path.exists():
        return {}
    column_keys = {_normalize_header(c) for c in columns}
    comment_map: dict[int, str] = {}
    headers: list[str] | None = None
    addr_idx: int | None = None
    comment_indices: list[int] = []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for line in lines:
        if "|" not in line:
            continue
        raw_cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not raw_cells or all(not c for c in raw_cells):
            continue
        # separator line
        if all(re.fullmatch(r"[-:]+", c or "-") for c in raw_cells):
            continue
        normalized = [_normalize_header(c) for c in raw_cells]
        if any(n in _ADDRESS_HEADER_KEYS for n in normalized):
            headers = raw_cells
            addr_idx = next(
                (i for i, n in enumerate(normalized) if n in _ADDRESS_HEADER_KEYS),
                None,
            )
            comment_indices = [i for i, n in enumerate(normalized) if n in column_keys]
            continue
        if headers is None or addr_idx is None or not comment_indices:
            continue
        if len(raw_cells) < len(headers):
            raw_cells = raw_cells + [""] * (len(headers) - len(raw_cells))
        else:
            raw_cells = raw_cells[: len(headers)]
        addr_cell = raw_cells[addr_idx]
        addrs = _parse_addr_cell(addr_cell)
        if not addrs:
            continue
        parts = [raw_cells[i] for i in comment_indices if raw_cells[i]]
        if not parts:
            continue
        comment_text = " ".join(p.strip() for p in parts if p.strip())
        if not comment_text:
            continue
        for addr in addrs:
            existing = comment_map.get(addr)
            if existing:
                if comment_text not in existing:
                    comment_map[addr] = f"{existing} {comment_text}"
            else:
                comment_map[addr] = comment_text
    return comment_map


_RANGE_PATTERN = re.compile(r"(-?\d+(?:\.\d+)?)\s*(?:~|～|－|—|–|-)\s*(-?\d+(?:\.\d+)?)")
_ENUM_PATTERN = re.compile(r"(0x[0-9a-fA-F]+|\d+)\s*(?:[:：]|-)(?=[^0-9])")
_MAX_ONLY_PATTERN = re.compile(r"[~～]\s*(-?\d+(?:\.\d+)?)")
_DEFAULT_PATTERN = re.compile(r"(?:default|默认)\s*[:：]\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE)


def _extract_limits(text: str) -> tuple[float, float] | None:
    if not text:
        return None
    ranges = _RANGE_PATTERN.findall(text)
    if ranges:
        values = []
        for left, right in ranges:
            values.append(float(left))
            values.append(float(right))
        return (min(values), max(values))
    enums = []
    for raw in _ENUM_PATTERN.findall(text):
        if raw.lower().startswith("0x"):
            enums.append(int(raw, 16))
        else:
            enums.append(int(raw))
    if enums:
        return (float(min(enums)), float(max(enums)))
    max_only = _MAX_ONLY_PATTERN.search(text)
    if max_only:
        return (0.0, float(max_only.group(1)))
    return None


def _extract_default(text: str) -> float | None:
    if not text:
        return None
    match = _DEFAULT_PATTERN.search(text)
    if not match:
        return None
    return float(match.group(1))


def _clamp_to_type(value: float, data_type: str) -> float:
    if data_type == "int16":
        return float(max(-32768, min(32767, int(round(value)))))
    if data_type == "uint16":
        return float(max(0, min(65535, int(round(value)))))
    if data_type == "int32":
        return float(max(-2147483648, min(2147483647, int(round(value)))))
    if data_type == "uint32":
        return float(max(0, min(4294967295, int(round(value)))))
    return value


def _boundary_default(
    *,
    reg_type: str,
    data_type: str,
    length: int,
    bits: dict | None,
    boundary_types: dict,
    bit_value: int,
    scale: float,
    offset: float,
    limit: tuple[float, float] | None,
    default_value: float | None,
):
    if reg_type in ("coil", "discrete") or (bits and isinstance(bits, dict) and len(bits) > 0):
        return int(bit_value)
    mode = str(boundary_types.get(data_type, "min")).strip().lower()
    use_max = mode == "max"
    if data_type in ("int16", "uint16", "int32", "uint32", "float32"):
        if default_value is not None:
            eng_value = float(default_value)
        else:
            if data_type == "int16":
                raw_base = 32767 if use_max else -32768
            elif data_type == "uint16":
                raw_base = 65535 if use_max else 0
            elif data_type == "int32":
                raw_base = 2147483647 if use_max else -2147483648
            elif data_type == "uint32":
                raw_base = 4294967295 if use_max else 0
            else:
                raw_base = _FLOAT32_MAX if use_max else -_FLOAT32_MAX
            eng_value = (float(raw_base) * float(scale)) + float(offset)
        if limit:
            eng_min, eng_max = limit
            if eng_value < eng_min:
                eng_value = eng_min
            if eng_value > eng_max:
                eng_value = eng_max
        if scale:
            raw = (eng_value - float(offset)) / float(scale)
        else:
            raw = 0.0
        return _clamp_to_type(raw, data_type)

    if data_type == "string":
        if use_max:
            width = max(1, int(length)) * 2
            return "Z" * width
        return ""
    return 0


class ConfigLoader:
    def load(self, path: Path) -> dict:
        return _load_yaml(path)


class ConfigNormalizer:
    def apply_defaults(self, cfg: dict) -> dict:
        data = deepcopy(cfg)
        data.setdefault("profile_files", [])
        data.setdefault("profiles", {})
        data.setdefault("listeners", [])
        data.setdefault("devices", [])
        data.setdefault("simulation", [])
        data.setdefault("runtime", {})
        data.setdefault("logging", {})
        data.setdefault("metrics", {})
        data.setdefault("boundary_values", {})

        runtime = data["runtime"]
        runtime.setdefault("max_connections", 100)
        runtime.setdefault("max_qps", 200)
        runtime.setdefault("request_timeout_ms", 200)
        runtime.setdefault("max_slaves_per_port", 32)

        logging_cfg = data["logging"]
        logging_cfg.setdefault("level", "INFO")
        logging_cfg.setdefault("format", "json")
        logging_cfg.setdefault("output", "stdout")

        metrics_cfg = data["metrics"]
        metrics_cfg.setdefault("enabled", True)
        metrics_cfg.setdefault("output", "log")
        metrics_cfg.setdefault("interval_s", 10)
        metrics_cfg.setdefault("endpoint", "/metrics")
        metrics_cfg.setdefault("address", "0.0.0.0")
        metrics_cfg.setdefault("port", 9090)

        boundary_cfg = data.get("boundary_values")
        if isinstance(boundary_cfg, dict):
            boundary_cfg.setdefault("enabled", False)
            boundary_cfg.setdefault("bit", 0)
            types_cfg = boundary_cfg.setdefault("types", {})
            if isinstance(types_cfg, dict):
                types_cfg.setdefault("int16", "max")
                types_cfg.setdefault("uint16", "max")
                types_cfg.setdefault("int32", "max")
                types_cfg.setdefault("uint32", "max")
                types_cfg.setdefault("float32", "max")
                types_cfg.setdefault("string", "max")

        for listener in data["listeners"]:
            if isinstance(listener, dict):
                listener.setdefault("type", "tcp")
                listener.setdefault("address_base", 0)
                listener.setdefault("devices", [])

        for item in data["simulation"]:
            if isinstance(item, dict):
                item.setdefault("interval", 1.0)
                item.setdefault("time_scale", 1.0)
                item.setdefault("enabled", True)

        return data


class ConfigValidator:
    def __init__(self, profiles: dict):
        self.profiles = profiles or {}

    def validate(self, cfg: dict) -> list[str]:
        errors: list[str] = []
        self._validate_config_version(cfg, errors)
        self._validate_runtime(cfg, errors)
        self._validate_metrics(cfg, errors)
        self._validate_logging(cfg, errors)
        self._validate_boundary_values(cfg, errors)
        self._validate_listeners(cfg, errors)
        self._validate_devices(cfg, errors)
        self._validate_profiles(errors)
        return errors

    def _validate_config_version(self, cfg: dict, errors: list[str]) -> None:
        if cfg.get("config_version") != "v1":
            errors.append("config_version must be v1")

    def _validate_runtime(self, cfg: dict, errors: list[str]) -> None:
        runtime = cfg.get("runtime") or {}
        for key in ("max_connections", "max_qps", "request_timeout_ms", "max_slaves_per_port"):
            try:
                value = int(runtime.get(key, 0))
            except (TypeError, ValueError):
                errors.append(f"runtime.{key} must be int")
                continue
            if value < 0:
                errors.append(f"runtime.{key} must be >= 0")

    def _validate_metrics(self, cfg: dict, errors: list[str]) -> None:
        metrics = cfg.get("metrics") or {}
        metrics_output = metrics.get("output", "log")
        if metrics_output not in ("log", "http"):
            errors.append("metrics.output must be log or http")
        metrics_enabled = bool(metrics.get("enabled", True))
        if metrics_enabled:
            try:
                interval_s = float(metrics.get("interval_s", 10))
            except (TypeError, ValueError):
                errors.append("metrics.interval_s must be number")
                interval_s = 0
            if interval_s <= 0:
                errors.append("metrics.interval_s must be > 0")
            if metrics_output == "http":
                endpoint = metrics.get("endpoint", "/metrics")
                if not isinstance(endpoint, str) or not endpoint.startswith("/"):
                    errors.append("metrics.endpoint must start with '/'")
                try:
                    port = int(metrics.get("port", 9090))
                except (TypeError, ValueError):
                    errors.append("metrics.port must be int")
                    port = 0
                if not (1 <= port <= 65535):
                    errors.append("metrics.port must be 1-65535")

    def _validate_logging(self, cfg: dict, errors: list[str]) -> None:
        logging_cfg = cfg.get("logging") or {}
        level = logging_cfg.get("level", "INFO")
        if not isinstance(level, str):
            errors.append("logging.level must be string")
        else:
            if level.upper() not in ("DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL"):
                errors.append(f"logging.level invalid: {level}")
        fmt = logging_cfg.get("format", "json")
        if fmt != "json":
            errors.append("logging.format must be json")
        output = logging_cfg.get("output", "stdout")
        if not isinstance(output, str):
            errors.append("logging.output must be string")

    def _validate_boundary_values(self, cfg: dict, errors: list[str]) -> None:
        boundary_cfg = cfg.get("boundary_values")
        if boundary_cfg is None:
            return
        if not isinstance(boundary_cfg, dict):
            errors.append("boundary_values must be map")
            return
        enabled = boundary_cfg.get("enabled", False)
        if not isinstance(enabled, (bool, int)):
            errors.append("boundary_values.enabled must be bool")
        bit_raw = boundary_cfg.get("bit", 0)
        try:
            bit_val = int(bit_raw)
        except (TypeError, ValueError):
            errors.append("boundary_values.bit must be 0 or 1")
            bit_val = -1
        if bit_val not in (0, 1):
            errors.append("boundary_values.bit must be 0 or 1")
        types_cfg = boundary_cfg.get("types", {})
        if not isinstance(types_cfg, dict):
            errors.append("boundary_values.types must be map")
            return
        allowed_types = {"int16", "uint16", "int32", "uint32", "float32", "string"}
        for key, value in types_cfg.items():
            if key not in allowed_types:
                errors.append(f"boundary_values.types invalid type: {key}")
                continue
            mode = str(value).strip().lower()
            if mode not in ("min", "max"):
                errors.append(f"boundary_values.types.{key} must be min or max")

    def _validate_listeners(self, cfg: dict, errors: list[str]) -> None:
        listeners = cfg.get("listeners") or []
        devices_cfg = cfg.get("devices") or []
        device_names = {d.get("name") for d in devices_cfg}
        runtime = cfg.get("runtime") or {}
        max_slaves_per_port = int(runtime.get("max_slaves_per_port", 0) or 0)

        for idx, listener in enumerate(listeners):
            if not isinstance(listener, dict):
                errors.append(f"listeners[{idx}] must be map")
                continue
            try:
                port = int(listener.get("port"))
            except (TypeError, ValueError):
                errors.append(f"listeners[{idx}].port must be int")
                continue
            if not (1 <= port <= 65535):
                errors.append(f"listeners[{idx}].port out of range: {port}")
            ltype = listener.get("type", "tcp")
            if ltype != "tcp":
                errors.append(f"listeners[{idx}].type must be tcp")
            try:
                address_base = int(listener.get("address_base", 0))
            except (TypeError, ValueError):
                errors.append(f"listeners[{idx}].address_base must be int")
                address_base = -1
            if address_base not in (0, 1):
                errors.append(f"listeners[{idx}].address_base must be 0 or 1")

            devs = listener.get("devices") or []
            if max_slaves_per_port and len(devs) > max_slaves_per_port:
                errors.append("listener devices exceed runtime.max_slaves_per_port")
            for name in devs:
                if name not in device_names:
                    errors.append(f"listener device not found: {name}")

    def _validate_devices(self, cfg: dict, errors: list[str]) -> None:
        devices_cfg = cfg.get("devices") or []
        seen_names: set[str] = set()
        for idx, dev in enumerate(devices_cfg):
            if not isinstance(dev, dict):
                errors.append(f"devices[{idx}] must be map")
                continue
            name = str(dev.get("name") or "")
            if not name:
                errors.append(f"devices[{idx}].name required")
            elif name in seen_names:
                errors.append(f"duplicate device name: {name}")
            seen_names.add(name)

            try:
                slave_id = int(dev.get("slave_id"))
            except (TypeError, ValueError):
                errors.append(f"devices[{idx}].slave_id must be int")
                slave_id = 0
            if not (1 <= slave_id <= 247):
                errors.append(f"slave_id out of range: {slave_id}")
            profile_name = dev.get("profile")
            if not profile_name:
                errors.append(f"devices[{idx}].profile required")
            elif profile_name not in self.profiles:
                errors.append(f"profile not found: {profile_name}")

        listeners = cfg.get("listeners") or []
        name_to_slave = {d.get("name"): d.get("slave_id") for d in devices_cfg}
        for idx, listener in enumerate(listeners):
            devs = listener.get("devices") or []
            seen: set[int] = set()
            for name in devs:
                slave_id = name_to_slave.get(name)
                if slave_id is None:
                    continue
                if slave_id in seen:
                    errors.append(f"listeners[{idx}] duplicate slave_id: {slave_id}")
                seen.add(slave_id)

    def _validate_profiles(self, errors: list[str]) -> None:
        allowed_reg_types = {"holding", "input", "coil", "discrete"}
        allowed_data_types = {"int16", "uint16", "int32", "uint32", "float32", "string"}
        allowed_access = {"ro", "rw", "wo"}

        for name, body in self.profiles.items():
            regs = body.get("registers") or []
            if not isinstance(regs, list):
                errors.append(f"profile {name} registers must be list")
                continue
            allow_overlap = bool(body.get("allow_overlap"))
            occupied_by_type: dict[str, set[int]] = {} if not allow_overlap else {}
            for idx, item in enumerate(regs):
                if not isinstance(item, dict):
                    errors.append(f"profile {name} register[{idx}] must be map")
                    continue
                try:
                    addr = int(item.get("address"))
                except (TypeError, ValueError):
                    errors.append(f"profile {name} register[{idx}].address must be int")
                    continue
                if addr < 0:
                    errors.append(f"profile {name} register[{idx}].address must be >= 0")
                reg_type = item.get("reg_type", "holding")
                if reg_type not in allowed_reg_types:
                    errors.append(f"profile {name} register[{idx}].reg_type invalid: {reg_type}")
                occupied = occupied_by_type.setdefault(reg_type, set())
                data_type = _normalize_data_type(item.get("data_type", "int16"))
                if data_type not in allowed_data_types:
                    errors.append(f"profile {name} register[{idx}].data_type invalid: {data_type}")
                access = item.get("access", "rw")
                if access not in allowed_access:
                    errors.append(f"profile {name} register[{idx}].access invalid: {access}")

                raw_length = item.get("length")
                length = 1
                if data_type in ("int32", "uint32", "float32"):
                    if raw_length not in (None, "", 2):
                        errors.append(f"profile {name} register[{idx}].length must be 2 for {data_type}")
                    length = 2
                elif data_type == "string":
                    try:
                        length = int(raw_length or 1)
                    except (TypeError, ValueError):
                        errors.append(f"profile {name} register[{idx}].length must be int for string")
                        length = 1
                else:
                    try:
                        length = int(raw_length or 1)
                    except (TypeError, ValueError):
                        errors.append(f"profile {name} register[{idx}].length must be int")
                        length = 1

                if length <= 0:
                    errors.append(f"profile {name} register[{idx}].length must be > 0")
                    length = 1

                if reg_type in ("coil", "discrete"):
                    if data_type not in ("int16", "uint16"):
                        errors.append(
                            f"profile {name} register[{idx}].data_type invalid for {reg_type}"
                        )
                    if length != 1:
                        errors.append(
                            f"profile {name} register[{idx}].length must be 1 for {reg_type}"
                        )

                if not allow_overlap:
                    for offset in range(length):
                        addr_i = addr + offset
                        if addr_i in occupied:
                            errors.append(
                                f"profile {name} register[{idx}] overlaps address {addr_i}"
                            )
                        occupied.add(addr_i)

                min_val = item.get("min")
                max_val = item.get("max")
                if min_val is not None and max_val is not None:
                    try:
                        if float(min_val) > float(max_val):
                            errors.append(
                                f"profile {name} register[{idx}] min greater than max"
                            )
                    except (TypeError, ValueError):
                        errors.append(
                            f"profile {name} register[{idx}] min/max must be numeric"
                        )


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        raise ConfigError(f"config not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ConfigError("invalid config format")
    return data


def load_profiles(profile_files: list[Path]) -> dict:
    profiles: dict = {}
    for path in profile_files:
        data = _load_yaml(path)
        chunk = data.get("profiles") or {}
        for name, body in chunk.items():
            profiles[name] = body
    return profiles


def _register_addresses(item: dict) -> tuple[str, list[int]]:
    reg_type = str(item.get("reg_type", "holding"))
    data_type = _normalize_data_type(item.get("data_type"))
    length = item.get("length")
    if data_type in ("int32", "uint32", "float32"):
        length = 2
    elif data_type == "string":
        try:
            length = int(length or 1)
        except (TypeError, ValueError):
            length = 1
    else:
        try:
            length = int(length or 1)
        except (TypeError, ValueError):
            length = 1
    if length <= 0:
        length = 1
    address = int(item.get("address"))
    return reg_type, list(range(address, address + length))


def _merge_profile_registers(primary: list | None, fallback: list | None) -> list:
    primary = list(primary or [])
    fallback = list(fallback or [])
    occupied: dict[str, set[int]] = {}
    for item in primary:
        reg_type, addrs = _register_addresses(item)
        occupied.setdefault(reg_type, set()).update(addrs)

    merged = list(primary)
    fallback_sorted = sorted(
        fallback,
        key=lambda item: int(item.get("address", 0)),
    )
    for item in fallback_sorted:
        reg_type, addrs = _register_addresses(item)
        reg_occupied = occupied.setdefault(reg_type, set())
        if any(addr in reg_occupied for addr in addrs):
            continue
        merged.append(item)
        reg_occupied.update(addrs)
    return merged


def _merge_profile_body(primary: dict, fallback: dict) -> dict:
    if primary.get("ignore_fallback"):
        return dict(primary)
    merged = dict(fallback or {})
    merged.update(primary or {})
    merged["registers"] = _merge_profile_registers(
        primary.get("registers") if isinstance(primary, dict) else [],
        fallback.get("registers") if isinstance(fallback, dict) else [],
    )
    return merged


def _merge_profiles(primary: dict, fallback: dict) -> dict:
    merged = dict(fallback or {})
    for name, body in (primary or {}).items():
        if name in merged:
            merged[name] = _merge_profile_body(body, merged[name])
        else:
            merged[name] = body
    return merged


def _resolve_path(base_dir: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    candidate = (base_dir / path).resolve()
    if candidate.exists():
        return candidate
    alt = (base_dir.parent / path).resolve()
    if alt.exists():
        return alt
    return candidate


def resolve_profile_files(cfg: dict, base_dir: Path) -> list[Path]:
    files: list[Path] = []
    for raw in cfg.get("profile_files", []) or []:
        files.append(_resolve_path(base_dir, str(raw)))
    profiles_dir = cfg.get("profiles_dir")
    if profiles_dir:
        pdir = _resolve_path(base_dir, str(profiles_dir))
        if pdir.exists():
            files.extend(sorted(pdir.glob("*.yaml")))
    return files


def load_config(path: Path) -> dict:
    loader = ConfigLoader()
    normalizer = ConfigNormalizer()
    cfg = loader.load(path)
    return normalizer.apply_defaults(cfg)


def build_device_registry(cfg: dict, base_dir: Path) -> DeviceRegistry:

    normalizer = ConfigNormalizer()
    cfg = normalizer.apply_defaults(cfg)
    profile_files = resolve_profile_files(cfg, base_dir)
    profiles = load_profiles(profile_files)
    profiles.update(cfg.get("profiles") or {})
    profiles = _merge_profiles(load_builtin_profiles(), profiles)
    errors = ConfigValidator(profiles).validate(cfg)
    if errors:
        detail = "\n- " + "\n- ".join(errors)
        raise ConfigError(f"config validation failed:{detail}")

    devices_cfg = cfg.get("devices") or []
    devices: list[DeviceContext] = []
    boundary_cfg = cfg.get("boundary_values") or {}
    boundary_enabled = bool(boundary_cfg.get("enabled", False))
    boundary_types = boundary_cfg.get("types") or {}
    try:
        bit_value = 1 if int(boundary_cfg.get("bit", 0)) else 0
    except (TypeError, ValueError):
        bit_value = 0
    doc_comment_cache: dict[str, dict[int, str]] = {}

    for dev in devices_cfg:
        profile_name = dev.get("profile")
        profile = profiles.get(profile_name)
        if not profile:
            raise ConfigError(f"profile not found: {profile_name}")
        read_fc = profile.get("read_fc")
        write_fc = profile.get("write_fc")
        mirror_input = bool(profile.get("mirror_input_to_holding"))
        regs = profile.get("registers") or []
        defs_by_type: dict[str, list[RegisterDef]] = {}
        doc_comments: dict[int, str] = {}
        if boundary_enabled and profile_name:
            cached = doc_comment_cache.get(profile_name)
            if cached is None:
                doc_path = _resolve_doc_path(profile.get("description"), base_dir)
                columns = _doc_columns_for_profile(profile_name, doc_path)
                cached = _load_doc_comment_map(doc_path, columns) if columns else {}
                doc_comment_cache[profile_name] = cached
            doc_comments = cached

        for item in regs:
            reg_type = item.get("reg_type", "holding")
            data_type = _normalize_data_type(item.get("data_type", "int16"))
            length = item.get("length")
            if data_type in ("int32", "uint32", "float32"):
                length = 2
            if data_type == "string":
                length = int(length or 1)
            length = int(length or 1)

            default_value = item.get("default")
            if boundary_enabled:
                comment_text = doc_comments.get(int(item.get("address")))
                limit = _extract_limits(comment_text) if comment_text else None
                default_override = _extract_default(comment_text) if comment_text else None
                default_value = _boundary_default(
                    reg_type=reg_type,
                    data_type=data_type,
                    length=length,
                    bits=item.get("bits") or {},
                    boundary_types=boundary_types,
                    bit_value=bit_value,
                    scale=float(item.get("scale") or 1.0),
                    offset=float(item.get("offset") or 0.0),
                    limit=limit,
                    default_value=default_override,
                )

            reg = RegisterDef(
                address=int(item.get("address")),
                name=str(item.get("name")),
                reg_type=reg_type,
                data_type=data_type,
                access=item.get("access", "rw"),
                scale=float(item.get("scale") or 1.0),
                offset=float(item.get("offset") or 0.0),
                unit=item.get("unit"),
                default=default_value,
                min=item.get("min"),
                max=item.get("max"),
                endian=item.get("endian", "be"),
                length=length,
                bits=item.get("bits") or {},
                comment=item.get("comment"),
            )
            defs_by_type.setdefault(reg_type, []).append(reg)

        stores = {rtype: RegisterStore(defs) for rtype, defs in defs_by_type.items()}
        if mirror_input and "holding" in stores:
            stores["input"] = stores["holding"]
        allowed_fcs: set[int] | None = None
        try:
            rf = int(read_fc) if read_fc is not None else None
            wf = int(write_fc) if write_fc is not None else None
        except (TypeError, ValueError):
            rf = None
            wf = None
        if rf is not None or wf is not None:
            allowed_fcs = set()
            if rf is not None:
                allowed_fcs.add(rf)
            if wf is not None:
                allowed_fcs.add(wf)
        device = DeviceContext(
            name=str(dev.get("name")),
            slave_id=int(dev.get("slave_id")),
            stores=stores,
            profile_name=str(profile_name) if profile_name is not None else None,
            read_fc=rf,
            write_fc=wf,
            allowed_function_codes=allowed_fcs,
        )
        devices.append(device)

    return DeviceRegistry(devices)

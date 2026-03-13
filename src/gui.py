from __future__ import annotations

from dataclasses import dataclass
from tkinter import BooleanVar, StringVar, Tk, ttk, messagebox
import tkinter as tk
from typing import Iterable

from .core.device import DeviceContext, RegisterDef
from .runtime import SimulatorRuntime


@dataclass(frozen=True)
class KeyMetric:
    label: str
    address: int


PCS_METRICS = [
    KeyMetric("故障综合", 32),
    KeyMetric("A相有功(kW)", 110),
    KeyMetric("B相有功(kW)", 111),
    KeyMetric("C相有功(kW)", 112),
    KeyMetric("总有功(kW)", 122),
    KeyMetric("有功调度(kW)", 135),
    KeyMetric("直流功率(kW)", 141),
]

BMS_PW_METRICS = [
    KeyMetric("SOC(%)", 1303),
    KeyMetric("SOH(%)", 1304),
    KeyMetric("总压(V)", 1301),
    KeyMetric("总电流(A)", 1302),
    KeyMetric("可充(kWh)", 1341),
    KeyMetric("可放(kWh)", 1342),
]

BMS_CIMC_METRICS = [
    KeyMetric("SOC(‰)", 0x200E),
    KeyMetric("SOH(‰)", 0x200F),
    KeyMetric("总压(V)", 0x200B),
    KeyMetric("总电流(A)", 0x200C),
    KeyMetric("总有功(kW)", 0x3029),
    KeyMetric("Rack故障", 0x2004),
]


def _iter_register_defs(device: DeviceContext) -> list[RegisterDef]:
    defs: list[RegisterDef] = []
    seen: set[tuple[str, int]] = set()
    for reg_type, store in device.stores.items():
        for reg in store.defs:
            key = (reg_type, reg.address)
            if key in seen:
                continue
            seen.add(key)
            defs.append(reg)
    return sorted(defs, key=lambda reg: (reg.reg_type, reg.address))


def _device_metrics(device: DeviceContext) -> list[KeyMetric]:
    profile = (device.profile_name or "").lower()
    if "pcs" in profile:
        return PCS_METRICS
    if "pw-100261a" in profile:
        return BMS_PW_METRICS
    return BMS_CIMC_METRICS


def _classify_bits(device: DeviceContext) -> tuple[list[RegisterDef], list[RegisterDef]]:
    fault_regs: list[RegisterDef] = []
    alarm_regs: list[RegisterDef] = []
    for reg in _iter_register_defs(device):
        if not reg.bits or reg.access == "ro":
            continue
        name = reg.name.lower()
        if any(token in name for token in ("fault", "故障")):
            fault_regs.append(reg)
        elif any(token in name for token in ("alarm", "alert", "warning", "告警", "报警")):
            alarm_regs.append(reg)
    return fault_regs, alarm_regs


class SimulatorGui:
    def __init__(self, runtime: SimulatorRuntime):
        self.runtime = runtime
        self.root = Tk()
        self.root.title("Modbus Simulator Control")
        self.root.geometry("1320x860")
        self.root.configure(bg="#eef1f5")
        self.device_var = StringVar()
        self.filter_var = StringVar()
        self.power_var = StringVar(value="0")
        self.status_var = StringVar(value="未启动")
        self.current_device: DeviceContext | None = None
        self.reg_tree: ttk.Treeview | None = None
        self.metrics_frame: ttk.Frame | None = None
        self.fault_frame: ttk.LabelFrame | None = None
        self.alarm_frame: ttk.LabelFrame | None = None
        self.fault_body: ttk.Frame | None = None
        self.alarm_body: ttk.Frame | None = None
        self.device_box: ttk.Combobox | None = None
        self._build_styles()
        self._build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(300, self._refresh_loop)

    def _build_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Title.TLabel", background="#ffffff", foreground="#364152", font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("Value.TLabel", background="#ffffff", foreground="#274c77", font=("Microsoft YaHei UI", 14, "bold"))

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(outer, padding=(0, 0, 0, 8))
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Button(toolbar, text="启动模拟器", command=self.start_runtime).pack(side="left")
        ttk.Button(toolbar, text="停止模拟器", command=self.stop_runtime).pack(side="left", padx=8)
        ttk.Button(toolbar, text="刷新状态", command=self.refresh_view).pack(side="left")
        ttk.Label(toolbar, text="PCS_1有功功率(kW)").pack(side="left", padx=(18, 4))
        ttk.Entry(toolbar, textvariable=self.power_var, width=10).pack(side="left")
        ttk.Button(toolbar, text="写入功率", command=self.apply_power).pack(side="left", padx=8)
        ttk.Label(toolbar, textvariable=self.status_var).pack(side="right")

        left = ttk.Frame(outer, padding=(0, 0, 12, 0))
        left.grid(row=1, column=0, sticky="ns")
        ttk.Label(left, text="设备").grid(row=0, column=0, sticky="w")
        self.device_box = ttk.Combobox(left, textvariable=self.device_var, state="readonly", width=26)
        self.device_box.grid(row=1, column=0, sticky="ew", pady=(4, 8))
        self.device_box.bind("<<ComboboxSelected>>", lambda _evt: self.refresh_view())
        ttk.Label(left, text="搜索寄存器").grid(row=2, column=0, sticky="w")
        ttk.Entry(left, textvariable=self.filter_var, width=28).grid(row=3, column=0, sticky="ew", pady=(4, 8))
        ttk.Button(left, text="应用搜索", command=self.refresh_view).grid(row=4, column=0, sticky="ew")

        right = ttk.Frame(outer)
        right.grid(row=1, column=1, sticky="nsew")
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        self.metrics_frame = ttk.Frame(right)
        self.metrics_frame.grid(row=0, column=0, sticky="ew")

        bit_wrap = ttk.Frame(right, padding=(0, 12, 0, 12))
        bit_wrap.grid(row=1, column=0, sticky="ew")
        bit_wrap.columnconfigure(0, weight=1)
        bit_wrap.columnconfigure(1, weight=1)
        self.fault_frame = ttk.LabelFrame(bit_wrap, text="故障位控制", padding=10)
        self.fault_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.alarm_frame = ttk.LabelFrame(bit_wrap, text="告警位控制", padding=10)
        self.alarm_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.fault_body = self._build_scroll_body(self.fault_frame)
        self.alarm_body = self._build_scroll_body(self.alarm_frame)

        table_card = ttk.Frame(right)
        table_card.grid(row=2, column=0, sticky="nsew")
        table_card.rowconfigure(0, weight=1)
        table_card.columnconfigure(0, weight=1)
        columns = ("address", "name", "value", "unit", "access", "bits")
        self.reg_tree = ttk.Treeview(table_card, columns=columns, show="headings")
        for key, label, width in (
            ("address", "地址", 80),
            ("name", "名称", 260),
            ("value", "值", 120),
            ("unit", "单位", 80),
            ("access", "权限", 80),
            ("bits", "位定义", 360),
        ):
            self.reg_tree.heading(key, text=label)
            self.reg_tree.column(key, width=width, anchor="w")
        self.reg_tree.grid(row=0, column=0, sticky="nsew")
        ybar = ttk.Scrollbar(table_card, orient="vertical", command=self.reg_tree.yview)
        ybar.grid(row=0, column=1, sticky="ns")
        self.reg_tree.configure(yscrollcommand=ybar.set)

    def _build_scroll_body(self, parent: ttk.LabelFrame) -> ttk.Frame:
        canvas = tk.Canvas(parent, highlightthickness=0, bg="#ffffff", height=220)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)
        body = ttk.Frame(canvas)
        body.bind(
            "<Configure>",
            lambda _evt, c=canvas: c.configure(scrollregion=c.bbox("all")),
        )
        canvas.create_window((0, 0), window=body, anchor="nw")
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        return body

    def start_runtime(self) -> None:
        if self.runtime.started:
            self.status_var.set("已启动")
            return
        try:
            self.runtime.start()
        except Exception as exc:
            messagebox.showerror("启动失败", str(exc))
            self.status_var.set("启动失败")
            return
        self.status_var.set("已启动")
        self._load_devices()
        self.refresh_view()

    def stop_runtime(self) -> None:
        self.runtime.stop()
        self.status_var.set("已停止")

    def apply_power(self) -> None:
        if not self.runtime.started or not self.runtime.registry:
            messagebox.showwarning("未启动", "请先启动模拟器")
            return
        device = self.runtime.registry.get_by_name("PCS_1")
        if not device:
            messagebox.showerror("写入失败", "未找到 PCS_1")
            return
        try:
            device.set_engineering_value(135, float(self.power_var.get()))
        except Exception as exc:
            messagebox.showerror("写入失败", str(exc))
            return
        self.refresh_view()

    def _load_devices(self) -> None:
        if not self.runtime.registry or not self.device_box:
            return
        names = sorted(self.runtime.registry.by_name.keys())
        self.device_box["values"] = names
        if names and not self.device_var.get():
            self.device_var.set(names[0])

    def refresh_view(self) -> None:
        if not self.runtime.started or not self.runtime.registry:
            return
        self._load_devices()
        device = self.runtime.registry.get_by_name(self.device_var.get())
        self.current_device = device
        if not device:
            return
        self._render_metrics(device)
        self._render_bit_controls(device)
        self._render_register_table(device)

    def _render_metrics(self, device: DeviceContext) -> None:
        for child in self.metrics_frame.winfo_children():
            child.destroy()
        metrics = _device_metrics(device)
        for idx, metric in enumerate(metrics):
            card = ttk.Frame(self.metrics_frame, style="Card.TFrame", padding=12)
            card.grid(row=idx // 4, column=idx % 4, sticky="nsew", padx=4, pady=4)
            ttk.Label(card, text=metric.label, style="Title.TLabel").pack(anchor="w")
            ttk.Label(card, text=self._safe_value(device, metric.address), style="Value.TLabel").pack(anchor="w", pady=(8, 0))

    def _render_bit_controls(self, device: DeviceContext) -> None:
        for frame in (self.fault_body, self.alarm_body):
            for child in frame.winfo_children():
                child.destroy()
        fault_regs, alarm_regs = _classify_bits(device)
        self._populate_bit_frame(self.fault_body, device, fault_regs)
        self._populate_bit_frame(self.alarm_body, device, alarm_regs)

    def _populate_bit_frame(self, frame: ttk.Frame, device: DeviceContext, regs: Iterable[RegisterDef]) -> None:
        row = 0
        for reg in regs:
            ttk.Label(frame, text=f"{reg.address} {reg.name}").grid(row=row, column=0, sticky="w", pady=(0, 4))
            row += 1
            for bit_index, label in sorted((reg.bits or {}).items()):
                var = BooleanVar(value=bool(device.get_bit(reg.address, bit_index)))
                check = ttk.Checkbutton(
                    frame,
                    text=f"Bit{bit_index} {label}",
                    variable=var,
                    command=lambda a=reg.address, b=bit_index, v=var: self._toggle_bit(device, a, b, v),
                )
                check.grid(row=row, column=0, sticky="w")
                row += 1

    def _render_register_table(self, device: DeviceContext) -> None:
        self.reg_tree.delete(*self.reg_tree.get_children())
        keyword = self.filter_var.get().strip().lower()
        for reg in _iter_register_defs(device):
            bits_text = ", ".join(f"{idx}:{name}" for idx, name in sorted((reg.bits or {}).items()))
            value = self._safe_value(device, reg.address)
            if keyword:
                haystack = f"{reg.address} {reg.name} {value}".lower()
                if keyword not in haystack:
                    continue
            self.reg_tree.insert("", "end", values=(reg.address, reg.name, value, reg.unit or "", reg.access, bits_text))

    def _toggle_bit(self, device: DeviceContext, address: int, bit_index: int, var: BooleanVar) -> None:
        try:
            device.set_bit(address, bit_index, 1 if var.get() else 0)
        except Exception as exc:
            messagebox.showerror("写入失败", str(exc))
        self.refresh_view()

    def _safe_value(self, device: DeviceContext, address: int) -> str:
        try:
            return str(device.get_engineering_value(address))
        except Exception:
            return "-"

    def _refresh_loop(self) -> None:
        if self.runtime.started:
            self.status_var.set("已启动")
            self.refresh_view()
        self.root.after(1000, self._refresh_loop)

    def _on_close(self) -> None:
        self.runtime.stop()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def launch_gui(runtime: SimulatorRuntime) -> None:
    gui = SimulatorGui(runtime)
    gui.start_runtime()
    gui.run()

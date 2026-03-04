
# 中集储能直流侧261kWh储能柜 BMS 数据点表

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class BMSCimcEss832314RegisterDefinition:
    address: int
    length: int
    field_name: str
    label_cn: str
    attribute: str
    unit: str
    scale: float
    scale_decimals: int
    data_type: str
    group: str
    bit_index: Optional[int] = None

    def addresses(self) -> List[int]:
        return list(range(self.address, self.address + self.length))


GROUP_HEARTBEAT = "心跳组"
GROUP_CORE      = "实时组"
GROUP_STATIC    = "静态组"
GROUP_CONTROL   = "控制组"

READ_REGISTER = 0x04
WRITE_REGISTER = 0x10

BMS_CIMC_ESS_832_314_REGISTER_MAP: List[BMSCimcEss832314RegisterDefinition] = [
    BMSCimcEss832314RegisterDefinition(0x2001, 1, 'rack_run_state', 'Rack运行状态', 'R', '', 1.0, 0, 'uint16', "心跳组", None),
    BMSCimcEss832314RegisterDefinition(0x2002, 1, 'rack_precharge_phase', 'Rack预充电阶段', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2003, 1, 'rack_connection_state', 'Rack接触器状态', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2004, 1, 'rack_fault', 'Rack故障', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2005, 1, 'rack_warning', 'Rack一级报警', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2006, 1, 'rack_alarm', 'Rack二级报警', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2007, 1, 'rack_critical_alarm', 'Rack三级报警', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2008, 1, 'reason_of_rack_1_step_in_failure', 'Rack切入失败原因', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2009, 1, 'the_reason_why_rack_did_not_start_step_in', 'Rack未启动切入原因', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x200A, 1, 'rack_precharge_total_vol', 'RACK的LINK总压', 'R', 'V', 0.1, 1, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x200B, 1, 'rack_rack_voltage', 'Rack电池总电压', 'R', 'V', 0.1, 1, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x200C, 1, 'rack_current', 'Rack电池总电流', 'R', 'A', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x200D, 1, 'rack_charge_discharge_state', 'Rack充放电指示', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x200E, 1, 'rack_soc', 'RackSOC', 'R', '‰', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x200F, 1, 'rack_soh', 'RackSOH', 'R', '‰', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2010, 1, 'rack_insulation_value', 'Rack绝缘值', 'R', 'KΩ', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2011, 1, 'rack_positive_insulation_value', 'Rack正极绝缘值', 'R', 'KΩ', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2013, 1, 'rack_max_charge_current', 'Rack最大充电电流', 'R', 'A', 0.1, 1, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2014, 1, 'rack_max_discharge_current', 'Rack最大放电电流', 'R', 'A', 0.1, 1, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2015, 1, 'rack_max_vol_cell_id', 'Rack单体电压最高节序号', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2016, 1, 'rack_max_cell_voltage', 'Rack单体最高电压值', 'R', 'mV', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2017, 1, 'rack_min_vol_cell_id', 'Rack单体电压最低节序号', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2018, 1, 'rack_min_cell_voltage', 'Rack单体最低电压值', 'R', 'Mv', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2019, 1, 'rack_max_temperature_cell_id', 'Rack单体温度最高节序号', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x201A, 1, 'rack_max_cell_temperature', 'Rack单体温度最高值', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x201B, 1, 'rack_min_temperature_cell_id', 'Rack单体温度最低节序号', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x201C, 1, 'rack_min_cell_temperature', 'Rack单体温度最低值', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x201D, 1, 'rack_average_voltage', 'Rack平均电压', 'R', 'mV', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x201E, 1, 'rack_average_temperature', 'Rack平均温度', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x201F, 1, 'rack_cell_voltage_cumulative_sum', 'Rack单体累加和总压', 'R', 'V', 0.1, 1, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2020, 1, 'hvb_temp1', 'Rack高压箱温度1', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2021, 1, 'hvb_temp2', 'Rack高压箱温度2', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2022, 1, 'hvb_temp3', 'Rack高压箱温度3', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2023, 1, 'hvb_temp4', 'Rack高压箱温度4', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2024, 1, 'hvb_temp5', 'Rack高压箱温度5', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2025, 1, 'hvb_temp6', 'Rack高压箱温度6', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2026, 1, 'hvb_temp7', 'Rack高压箱温度7', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2027, 1, 'hvb_temp8', 'Rack高压箱温度8', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2028, 1, 'reg_2028', '可充电量', 'R', 'KWH', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2029, 1, 'reg_2029', '可放电量', 'R', 'KWH', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x202A, 1, 'reg_202a', '最近一次充电电量', 'R', 'KWH', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x202B, 1, 'reg_202b', '最近一次放电电量', 'R', 'KWH', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x202C, 1, 'reg_202c', '累计充电电量高位', 'R', 'KWH', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x202D, 1, 'reg_202d', '累计充电电量低位', 'R', 'KWH', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x202E, 1, 'reg_202e', '累计放电电量高位', 'R', 'KWH', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x202F, 1, 'reg_202f', '累计放电电量低位', 'R', 'KWH', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x2030, 1, 'reg_2030', '日充电量', 'R', 'KWH', 1.0, 0, 'uint16', "静态组", None),
    BMSCimcEss832314RegisterDefinition(0x2031, 1, 'reg_2031', '日放电量', 'R', 'KWH', 1.0, 0, 'uint16', "静态组", None),
    BMSCimcEss832314RegisterDefinition(0x2220, 1, 'pack1_positive_pole_temperature', 'Pack1正极柱温度', 'R', '℃', 0.1, 1, 'int16', "静态组", None),
    BMSCimcEss832314RegisterDefinition(0x225F, 64, 'pack64_positive_pole_temperature', 'Pack64正极柱温度', 'R', '℃', 0.1, 1, 'int16', "静态组", None),
    BMSCimcEss832314RegisterDefinition(0x2260, 1, 'pack1_negative_pole_temperature', 'Pack1负极柱温度', 'R', '℃', 0.1, 1, 'int16', "静态组", None),
    BMSCimcEss832314RegisterDefinition(0x229F, 64, 'pack64_negative_pole_temperature', 'Pack64负极柱温度', 'R', '℃', 0.1, 1, 'int16', "静态组", None),
    BMSCimcEss832314RegisterDefinition(0x2400, 380, 'rack_cell_voltage_1', 'Rack单体电池电压', 'R', 'mV', 1.0, 0, 'uint16', "静态组", None),
    BMSCimcEss832314RegisterDefinition(0x25FF, 1, 'rack_cell_voltage_512', 'Rack单体电池电压', 'R', 'mV', 1.0, 0, 'uint16', "静态组", None),
    BMSCimcEss832314RegisterDefinition(0x2600, 152, 'rack_cell_temperature_1', 'Rack单体电池温度', 'R', '℃', 0.1, 1, 'int16', "静态组", None),
    BMSCimcEss832314RegisterDefinition(0x27FF, 1, 'rack_cell_temperature_512', 'Rack单体电池温度', 'R', '℃', 0.1, 1, 'int16', "静态组", None),
    BMSCimcEss832314RegisterDefinition(0x3001, 1, 'tms_unit_operating_status', 'TMS机组运行状态（风冷空调也用这个）', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3002, 1, 'tms_supply_temperature', 'TMS供液温度', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3003, 1, 'tms_return_temperature', 'TMS回液温度', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3004, 1, 'tms_operating_mode', 'TMS运行模式（风冷空调也用这个）', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3005, 1, 'tms_constant_temperature_preset_temperature', 'TMS恒温方式预设温度', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3006, 1, 'reg_3006', '制冷开启温度   （风冷空调也用这个）', 'R/W', '℃', 0.1, 1, 'int16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x3007, 1, 'reg_3007', '制冷停止温度   （风冷空调也用这个）', 'R/W', '℃', 0.1, 1, 'int16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x3008, 1, 'reg_3008', '制热开启温度   （风冷空调也用这个）', 'R/W', '℃', 0.1, 1, 'int16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x3009, 1, 'reg_3009', '制热停止温度   （风冷空调也用这个）', 'R/W', '℃', 0.1, 1, 'int16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x300A, 1, 'reg_1', '故障字1：', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x300B, 1, 'reg_2', '故障字2：', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x300C, 1, 'reg_3', '故障字3：', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x300D, 1, 'reg_4', '故障字4：', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x300F, 1, 'reg_5', '故障字5：', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3010, 1, 'reg_3010', '供液压力', 'R', 'bar', 0.1, 1, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3011, 1, 'reg_3011', '回液压力', 'R', 'bar', 0.1, 1, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3012, 1, 'reg_3012', '环境温度', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3013, 1, 'reg_3013', '交流供电电压', 'R', 'V', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3014, 1, 'reg_3014', '压缩机转速', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3015, 1, 'reg_3015', '进出水压差值', 'R', 'bar', 0.1, 1, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3016, 1, 'reg_3016', '软件版本', 'R', '', 1.0, 0, 'uint16', "静态组", None),
    BMSCimcEss832314RegisterDefinition(0x3017, 1, 'reg_3017', '产品机型', 'R', '', 1.0, 0, 'uint16', "静态组", None),
    BMSCimcEss832314RegisterDefinition(0x3018, 1, 'reg_3018', '供应商代码', 'R', '', 1.0, 0, 'uint16', "静态组", None),
    BMSCimcEss832314RegisterDefinition(0x3019, 1, 'reg_3019', '吸气温度', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x301A, 1, 'reg_301a', '板换温度', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x301B, 1, 'reg_301b', '冷凝盘温度', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x301C, 1, 'reg_301c', '高压侧压力值', 'R', 'bar', 0.1, 1, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x301D, 1, 'reg_301d', '低压侧压力值', 'R', 'bar', 0.1, 1, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x301E, 1, 'reg_301e', '电子膨胀阀开度', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x301F, 1, 'reg_301f', '机组运行状态', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3020, 1, 'reg_3020', '电表状态', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3021, 2, 'reg_3021', '日正向总电能', 'R', 'Kwh', 1.0, 0, 'u32', "静态组", None),
    BMSCimcEss832314RegisterDefinition(0x3023, 2, 'reg_3023', '日反向总电能', 'R', 'Kwh', 1.0, 0, 'u32', "静态组", None),
    BMSCimcEss832314RegisterDefinition(0x3025, 2, 'reg_3025', '累计正向总电能', 'R', 'Kwh', 1.0, 0, 'u32', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3027, 2, 'reg_3027', '累计反向总电能', 'R', 'Kwh', 1.0, 0, 'u32', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3029, 1, 'reg_3029', '总有功功率', 'R', 'Kw', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x302A, 1, 'a', 'A相有功功率', 'R', 'Kw', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x302B, 1, 'b', 'B相有功功率', 'R', 'Kw', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x302C, 1, 'c', 'C相有功功率', 'R', 'Kw', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3040, 1, 'reg_3040', '除湿器运行状态', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3041, 1, 'reg_3041', '温度启动值', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3042, 1, 'reg_3042', '温度关闭值', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3043, 1, 'reg_3043', '除湿启动值', 'R', '%RH', 1.0, 0, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3044, 1, 'reg_3044', '除湿关闭值', 'R', '%RH', 1.0, 0, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3045, 1, 'reg_3045', '环境湿度', 'R', '%RH', 1.0, 0, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3046, 1, 'reg_3046', '环境温度', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3047, 1, 'reg_3047', '内部温度', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3060, 1, 'reg_3060', '消防运行状态', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3061, 1, 'reg_3061', '水浸运行状态', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3062, 1, 'reg_3062', '烟雾运行状态', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3063, 1, 'co', 'CO浓度', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3068, 1, 'reg_3068', '风扇工作状态', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x3069, 1, 't1', 'T1温度值', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x306A, 1, 't2', 'T2温度值', 'R', '℃', 0.1, 1, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x306B, 1, 'reg_1_306b', '风扇1转速', 'R', 'RPM', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x306C, 1, 'reg_2_306c', '风扇2转速', 'R', 'RPM', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x306D, 1, 'reg_3_306d', '风扇3转速', 'R', 'RPM', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x306E, 1, 'reg_4_306e', '风扇4转速', 'R', 'RPM', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x4000, 1, 'reg_4000', '紧急下电指令（断脱扣断路器）', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4001, 1, 'reg_4001', '退避并接指令（断脱总正负负继电器）', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4002, 1, 'bms', 'BMS重启指令', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4003, 1, 'bms_4003', 'BMS版本号', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4004, 3, 'fwid', '软件FWID', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4007, 1, 'reg_4007', '绝缘检测指令', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x400A, 8, 'hdiw', '硬件HDIW', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4100, 1, 'bms_tms', 'BMS发指令给TMS开关机', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4101, 1, 'bms_tms_4101', 'BMS发指令给TMS控制工作模式', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4102, 1, 'reg_4102', '开启制冷点', 'W/R', '℃', 0.1, 1, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4103, 1, 'reg_4103', '关闭制冷点', 'W/R', '℃', 0.1, 1, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4104, 1, 'reg_4104', '开启制热点', 'W/R', '℃', 0.1, 1, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4105, 1, 'reg_4105', '关闭制热点', 'W/R', '℃', 0.1, 1, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4106, 1, 'reg_4106', '制冷目标温度', 'W/R', '℃', 0.1, 1, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4107, 1, 'reg_4107', '制热目标温度', 'W/R', '℃', 0.1, 1, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4108, 1, 'reg_4108', '电芯温差（自循环温度）', 'W/R', '℃', 0.1, 1, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4109, 1, 'reg_4109', '除湿开启湿度点', 'W/R', '%', 0.1, 2, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x410A, 1, 'reg_410a', '除湿关闭湿度点', 'W/R', '%', 0.1, 2, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4500, 1, 'cell_balance_0_15', '0~15号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4501, 1, 'cell_balance_16_31', '16~31号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4502, 1, 'cell_balance_32_47', '32~47号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4503, 1, 'cell_balance_48_63', '48~63号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4504, 1, 'cell_balance_64_79', '64~79号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4505, 1, 'cell_balance_80_95', '80~95号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4506, 1, 'cell_balance_96_111', '96~111号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4507, 1, 'cell_balance_112_127', '112~127号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4508, 1, 'cell_balance_128_143', '128~143号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4509, 1, 'cell_balance_144_159', '144~159号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x450A, 1, 'cell_balance_160_175', '160~175号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x450B, 1, 'cell_balance_176_191', '176~191号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x450C, 1, 'cell_balance_192_207', '192~207号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x450D, 1, 'cell_balance_208_223', '208~223号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x450E, 1, 'cell_balance_224_239', '224~239号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x450F, 1, 'cell_balance_240_255', '240~255号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4510, 1, 'cell_balance_256_271', '256~271号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4511, 1, 'cell_balance_272_287', '272~287号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4512, 1, 'cell_balance_288_303', '288~303号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4513, 1, 'cell_balance_304_319', '304~319号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4514, 1, 'cell_balance_320_335', '320~335号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4515, 1, 'cell_balance_336_351', '336~351号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4516, 1, 'cell_balance_352_367', '352~367号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4517, 1, 'cell_balance_368_383', '368~383号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4518, 1, 'cell_balance_384_399', '384~399号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x4519, 1, 'cell_balance_400_415', '400~415号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x451A, 1, 'cell_balance_416_431', '416~431号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x451B, 1, 'cell_balance_432_447', '432~447号电芯均衡状态', 'W/R', '', 1.0, 0, 'uint16', "控制组", None),
    BMSCimcEss832314RegisterDefinition(0x5001, 1, 'dostatus', 'DO总状态', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x5002, 1, 'distatus', 'DI总状态', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x5003, 1, 'door_status', '门禁状态', 'R', '', 1.0, 0, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x5004, 1, 'estop_status', '急停状态', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x5005, 1, 'water_status', '水浸状态', 'R', '', 1.0, 0, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x5006, 1, 'somke_status', '烟感状态', 'R', '', 1.0, 0, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x5007, 1, 'fire_1status', '消防本身故障', 'R', '', 1.0, 0, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x5008, 1, 'liquid_status', '液位异常状态', 'R', '', 1.0, 0, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x5009, 1, 'switch_status', '交流开关反馈', 'R', '', 1.0, 0, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x500A, 1, 'lightning_staus', '防雷反馈', 'R', '', 1.0, 0, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x500B, 1, 'fire2_status', '消防检测到故障', 'R', '', 1.0, 0, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x500C, 1, 'fire_3status', '消防喷洒状态', 'R', '', 1.0, 0, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x500D, 1, 'reg_3_500d', '预留3', 'R', '', 1.0, 0, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x500E, 1, 'reg_4_500e', '预留4', 'R', '', 1.0, 0, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x500F, 1, 'reg_5_500f', '预留5', 'R', '', 1.0, 0, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x5010, 1, 'reg_6', '预留6', 'R', '', 1.0, 0, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x5011, 1, 'reg_7', '预留7', 'R', '', 1.0, 0, 'int16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x5012, 1, 'slavedostatus', '从机Do总状态', 'R', '', 1.0, 0, 'uint16', "实时组", None),
    BMSCimcEss832314RegisterDefinition(0x5013, 1, 'slavedistatus', '从机DI总状态', 'R', '', 1.0, 0, 'uint16', "实时组", None),
]


def load_bms_cimc_ess_832_314_register_map(group: str = None) -> List[BMSCimcEss832314RegisterDefinition]:
    definitions = list(BMS_CIMC_ESS_832_314_REGISTER_MAP)
    if group:
        definitions = [d for d in definitions if d.group == group]
    return definitions



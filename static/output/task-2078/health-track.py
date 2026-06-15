#!/usr/bin/env python3
"""
健康指标自动追踪系统 - 每日录入脚本
==================================
功能：每日快速健康数据录入，自动保存为JSON格式
用法：python3 health-track.py daily
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 配置
DATA_DIR = Path(__file__).parent
DATA_FILE = DATA_DIR / "health-data.json"
CONFIG_FILE = DATA_DIR / "health-config.json"

# ===== 预警阈值配置 =====
DEFAULT_CONFIG = {
    "metrics": {
        "bp_sys": {"name": "收缩压", "unit": "mmHg", "normal": [90, 120], "warning": [85, 130]},
        "bp_dia": {"name": "舒张压", "unit": "mmHg", "normal": [60, 80], "warning": [55, 90]},
        "morning_hr": {"name": "晨起心率", "unit": "bpm", "normal": [50, 80], "warning": [45, 90]},
        "weight": {"name": "体重", "unit": "kg", "normal": [65, 85], "weekly_change_max": 2.0},
        "sleep_duration": {"name": "睡眠时长", "unit": "小时", "normal": [7, 8.5], "warning": [6, 10]},
        "energy_level": {"name": "精力评分", "unit": "/10", "normal": [6, 10], "low_consecutive_warn": 3},
        "hrv": {"name": "HRV", "unit": "ms", "normal": [30, 100], "warning": [20, 120]},
    },
    "exercise_types": ["跑步", "力量训练", "游泳", "瑜伽", "骑行", "散步", "休息"],
    "report_retention_days": 365
}


def load_config():
    """加载配置文件，不存在则创建默认配置"""
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        # print("✅ 已创建默认配置文件: health-config.json")
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_data():
    """加载历史数据，不存在则创建"""
    if not DATA_FILE.exists():
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    """保存数据到JSON文件"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def check_value(metric_key, value, config):
    """检查单个指标是否在正常范围内"""
    if metric_key not in config["metrics"]:
        return "", ""
    
    metric = config["metrics"][metric_key]
    normal = metric["normal"]
    warning = metric.get("warning", normal)
    
    if value < warning[0] or value > warning[1]:
        return "🔴 严重偏离", f"正常范围: {warning[0]}-{warning[1]} {metric['unit']}"
    elif value < normal[0] or value > normal[1]:
        return "⚠️ 轻微偏离", f"理想范围: {normal[0]}-{normal[1]} {metric['unit']}"
    return "✅ 正常", f"理想范围: {normal[0]}-{normal[1]} {metric['unit']}"


def check_weight_trend(data, today_str, weight, config):
    """检查体重周趋势"""
    max_weekly_change = config["metrics"]["weight"].get("weekly_change_max", 2.0)
    
    # 查找7天前的体重
    today = datetime.strptime(today_str, "%Y-%m-%d")
    week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    
    if week_ago in data and "morning" in data[week_ago]:
        old_weight = data[week_ago]["morning"].get("weight")
        if old_weight:
            change = abs(weight - old_weight)
            if change > max_weekly_change:
                return f"⚠️ 周变化 {change:.1f}kg，超过阈值{max_weekly_change}kg"
            return f"✅ 周变化 {change:.1f}kg，在正常范围内"
    return ""


def check_energy_streak(data, today_str, config):
    """检查精力评分是否连续低分"""
    warn_threshold = config["metrics"]["energy_level"].get("low_consecutive_warn", 3)
    today = datetime.strptime(today_str, "%Y-%m-%d")
    
    low_count = 0
    for i in range(warn_threshold):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        if date_str in data:
            energy = data[date_str].get("energy", 10)
            if energy <= 4:
                low_count += 1
            else:
                break
    
    if low_count >= warn_threshold:
        return f"🔴 精力评分已连续{low_count}天≤4，建议调整作息！"
    return ""


def safe_input(prompt, type_=float, default=None):
    """安全的输入函数，支持类型转换和默认值"""
    while True:
        try:
            val = input(f"  {prompt}: ").strip()
            if val == "" and default is not None:
                return default
            return type_(val)
        except (ValueError, TypeError):
            # print(f"  ⚠️ 请输入有效数字（或直接回车使用默认值 {default}）")


def daily_entry():
    """每日健康数据录入"""
    config = load_config()
    data = load_data()
    
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M")
    
    # print("\n" + "=" * 50)
    # print(f"🏥 健康指标每日录入 - {today} {now}")
    # print("=" * 50)
    # print()
    
    # 显示上次记录
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    if yesterday in data:
        # print(f"📋 昨日记录 ({yesterday}):")
        y = data[yesterday]
        if "morning" in y:
            m = y["morning"]
            # print(f"   体重 {m.get('weight', '-')}kg | 血压 {m.get('bp_sys', '-')}/{m.get('bp_dia', '-')} | 心率 {m.get('morning_hr', '-')}")
        # print(f"   睡眠 {y.get('sleep_duration', '-')}h | 精力 {y.get('energy', '-')}/10")
        # print()
    
    entry = {"morning": {}, "sleep": {}, "exercise": {}}
    warnings = []
    
    # --- 晨起指标 ---
    # print("🌅 【晨起指标】")
    weight = safe_input("体重 (kg)", float, None)
    if weight:
        entry["morning"]["weight"] = weight
        status, info = check_value("weight", weight, config)
        if "⚠️" in status or "🔴" in status:
            warnings.append(f"体重: {status} ({info})")
        
        wt_check = check_weight_trend(data, today, weight, config)
        if wt_check:
            warnings.append(wt_check)
    
    bp_sys = safe_input("收缩压 (mmHg, 直接回车跳过)", int, None)
    if bp_sys:
        entry["morning"]["bp_sys"] = bp_sys
        status, info = check_value("bp_sys", bp_sys, config)
        if "⚠️" in status or "🔴" in status:
            warnings.append(f"收缩压: {status} ({info})")
    
    bp_dia = safe_input("舒张压 (mmHg, 直接回车跳过)", int, None)
    if bp_dia:
        entry["morning"]["bp_dia"] = bp_dia
        status, info = check_value("bp_dia", bp_dia, config)
        if "⚠️" in status or "🔴" in status:
            warnings.append(f"舒张压: {status} ({info})")
    
    morning_hr = safe_input("晨起心率 (bpm, 直接回车跳过)", int, None)
    if morning_hr:
        entry["morning"]["morning_hr"] = morning_hr
        status, info = check_value("morning_hr", morning_hr, config)
        if "⚠️" in status or "🔴" in status:
            warnings.append(f"晨起心率: {status} ({info})")
    
    hrv = safe_input("HRV (ms, 直接回车跳过)", int, None)
    if hrv:
        entry["morning"]["hrv"] = hrv
        status, info = check_value("hrv", hrv, config)
        if "⚠️" in status or "🔴" in status:
            warnings.append(f"HRV: {status} ({info})")
    
    # print()
    
    # --- 睡眠 ---
    # print("😴 【昨晚睡眠】")
    sleep_dur = safe_input("睡眠时长 (小时)", float, 7.5)
    entry["sleep"]["duration"] = sleep_dur
    status, info = check_value("sleep_duration", sleep_dur, config)
    if "⚠️" in status or "🔴" in status:
        warnings.append(f"睡眠: {status} ({info})")
    
    sleep_quality = safe_input("主观睡眠质量 (1-10)", int, 7)
    entry["sleep"]["quality"] = sleep_quality
    
    # print()
    
    # --- 精力 ---
    # print("⚡ 【今日精力】")
    energy = safe_input("当前精力评分 (1-10)", int, 7)
    entry["energy"] = energy
    status, info = check_value("energy_level", energy, config)
    if "⚠️" in status or "🔴" in status:
        warnings.append(f"精力: {status} ({info})")
    
    streak_warn = check_energy_streak(data, today, config)
    if streak_warn:
        warnings.append(streak_warn)
    
    # print()
    
    # --- 运动 ---
    # print("🏃 【今日运动】")
    # print("  可选: " + ", ".join(config["exercise_types"]))
    exercise_type = input("  运动类型 (直接回车=休息): ").strip()
    if exercise_type:
        entry["exercise"]["type"] = exercise_type
        duration = safe_input("  运动时长 (分钟)", int, 30)
        entry["exercise"]["duration_min"] = duration
    else:
        entry["exercise"]["type"] = "休息"
    
    # print()
    
    # --- 备注 ---
    notes = input("📝 备注 (身体状况/感受/特殊事件，直接回车跳过): ").strip()
    if notes:
        entry["notes"] = notes
    
    # 保存
    data[today] = entry
    save_data(data)
    
    # 显示汇总
    # print()
    # print("=" * 50)
    # print(f"✅ 数据已保存: {today}")
    # print("=" * 50)
    
    if warnings:
        # print("\n⚠️ 预警提醒:")
        for w in warnings:
            # print(f"  {w}")
    else:
        # print("\n🎉 所有指标均在正常范围内！继续保持！")
    
    # 显示近7天趋势
    print_recent_trend(data, config)


def print_recent_trend(data, config):
    """显示近7天关键指标趋势"""
    today = datetime.now()
    # print("\n📊 【近7天趋势】")
    
    records = []
    for i in range(7):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        if date_str in data:
            records.append((date_str, data[date_str]))
    
    if len(records) < 2:
        # print("  数据不足，无法生成趋势")
        return
    
    records.sort()
    
    # 体重趋势
    weights = [(d, r.get("morning", {}).get("weight")) for d, r in records if r.get("morning", {}).get("weight")]
    if len(weights) >= 2:
        change = weights[-1][1] - weights[0][1]
        arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
        # print(f"  体重: {weights[0][1]} → {weights[-1][1]} kg {arrow} ({change:+.1f})")
    
    # 睡眠趋势
    sleeps = [(d, r.get("sleep", {}).get("duration")) for d, r in records if r.get("sleep", {}).get("duration")]
    if len(sleeps) >= 2:
        avg = sum(s[1] for s in sleeps) / len(sleeps)
        # print(f"  睡眠: 平均 {avg:.1f}h ({len(sleeps)}天)")
    
    # 精力趋势
    energies = [(d, r.get("energy")) for d, r in records if r.get("energy") is not None]
    if len(energies) >= 2:
        avg = sum(e[1] for e in energies) / len(energies)
        arrow = "↑" if energies[-1][1] > energies[0][1] else "↓" if energies[-1][1] < energies[0][1] else "→"
        # print(f"  精力: {energies[0][1]} → {energies[-1][1]}/10 {arrow} (平均 {avg:.1f})")


def show_status():
    """显示当前健康状态摘要"""
    config = load_config()
    data = load_data()
    
    if not data:
        # print("📭 暂无健康数据，请先运行: python3 health-track.py daily")
        return
    
    today = datetime.now()
    
    # 最近7天
    # print("\n" + "=" * 50)
    # print(f"📊 健康状态摘要 - {today.strftime('%Y-%m-%d')}")
    # print("=" * 50)
    
    recent_records = {}
    for i in range(7):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        if date_str in data:
            recent_records[date_str] = data[date_str]
    
    if not recent_records:
        # print("近7天暂无数据")
        return
    
    total_days = len(recent_records)
    
    # 计算平均值
    weights = [r.get("morning", {}).get("weight") for r in recent_records.values() if r.get("morning", {}).get("weight")]
    sleep_durs = [r.get("sleep", {}).get("duration") for r in recent_records.values() if r.get("sleep", {}).get("duration")]
    energies = [r.get("energy") for r in recent_records.values() if r.get("energy") is not None]
    
    # print(f"\n📅 近{total_days}天统计:")
    if weights:
        # print(f"  平均体重: {sum(weights)/len(weights):.1f} kg (范围: {min(weights):.1f}-{max(weights):.1f})")
    if sleep_durs:
        # print(f"  平均睡眠: {sum(sleep_durs)/len(sleep_durs):.1f} 小时")
    if energies:
        # print(f"  平均精力: {sum(energies)/len(energies):.1f}/10")
    
    # 运动统计
    exercise_days = sum(1 for r in recent_records.values() 
                       if r.get("exercise", {}).get("type") not in ["休息", None, ""])
    # print(f"  运动天数: {exercise_days}/{total_days}")
    
    # 达标率 (sleep >= 7h)
    good_count = 0
    total_checks = 0
    for r in recent_records.values():
        if r.get("sleep", {}).get("duration", 0) >= 7:
            good_count += 1
        total_checks += 1
    if total_checks > 0:
        # print(f"  睡眠达标率: {good_count/total_checks*100:.0f}%")


def batch_import(csv_path):
    """从CSV批量导入历史数据"""
    import csv
    config = load_config()
    data = load_data()
    imported = 0
    
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row.get("date", "").strip()
                if not date:
                    continue
                
                entry = {"morning": {}, "sleep": {}, "exercise": {}}
                
                if row.get("weight"):
                    entry["morning"]["weight"] = float(row["weight"])
                if row.get("bp_sys"):
                    entry["morning"]["bp_sys"] = int(row["bp_sys"])
                if row.get("bp_dia"):
                    entry["morning"]["bp_dia"] = int(row["bp_dia"])
                if row.get("morning_hr"):
                    entry["morning"]["morning_hr"] = int(row["morning_hr"])
                if row.get("sleep_duration"):
                    entry["sleep"]["duration"] = float(row["sleep_duration"])
                if row.get("sleep_quality"):
                    entry["sleep"]["quality"] = int(row["sleep_quality"])
                if row.get("energy"):
                    entry["energy"] = int(row["energy"])
                if row.get("exercise_type"):
                    entry["exercise"]["type"] = row["exercise_type"]
                if row.get("exercise_duration"):
                    entry["exercise"]["duration_min"] = int(row["exercise_duration"])
                if row.get("notes"):
                    entry["notes"] = row["notes"]
                
                data[date] = entry
                imported += 1
        
        save_data(data)
        # print(f"✅ 成功导入 {imported} 条记录")
    except Exception as e:
        # print(f"❌ 导入失败: {e}")


def main():
    if len(sys.argv) < 2:
        # print("用法:")
        # print("  python3 health-track.py daily    # 每日录入")
        # print("  python3 health-track.py status   # 状态摘要")
        # print("  python3 health-track.py import <csv文件>  # 批量导入")
        return
    
    command = sys.argv[1]
    
    if command == "daily":
        daily_entry()
    elif command == "status":
        show_status()
    elif command == "import":
        if len(sys.argv) < 3:
            # print("用法: python3 health-track.py import <csv文件路径>")
            return
        batch_import(sys.argv[2])
    else:
        # print(f"❌ 未知命令: {command}")
        # print("可用命令: daily, status, import")


if __name__ == "__main__":
    main()

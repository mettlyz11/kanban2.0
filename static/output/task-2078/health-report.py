#!/usr/bin/env python3
"""
健康指标自动追踪系统 - 周报/月报生成脚本
=========================================
功能：基于已录入的健康数据，自动生成周报和月报
用法：
  python3 health-report.py weekly     # 生成上周周报
  python3 health-report.py monthly    # 生成上月月报
  python3 health-report.py dashboard  # 生成实时仪表盘
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent
DATA_FILE = DATA_DIR / "health-data.json"
CONFIG_FILE = DATA_DIR / "health-config.json"
DASHBOARD_FILE = DATA_DIR / "health-dashboard.md"


def load_data():
    if not DATA_FILE.exists():
        # print("❌ 无健康数据，请先运行: python3 health-track.py daily")
        sys.exit(1)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config():
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_date_range(period):
    """获取日期范围"""
    today = datetime.now()
    
    if period == "weekly":
        # 上周一到上周日
        start = today - timedelta(days=today.weekday() + 7)
        end = today - timedelta(days=today.weekday() + 1)
    elif period == "monthly":
        # 上个月
        first_this = today.replace(day=1)
        end = first_this - timedelta(days=1)
        start = end.replace(day=1)
    elif period == "last7":
        start = today - timedelta(days=7)
        end = today - timedelta(days=1)
    elif period == "last30":
        start = today - timedelta(days=30)
        end = today - timedelta(days=1)
    else:
        start = today - timedelta(days=7)
        end = today
    
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def extract_records(data, start_date, end_date):
    """提取日期范围内的记录"""
    records = {}
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        if date_str in data:
            records[date_str] = data[date_str]
        current += timedelta(days=1)
    
    return records


def calc_stats(records):
    """计算统计指标"""
    stats = {}
    weights = []
    bp_sys_vals = []
    bp_dia_vals = []
    hr_vals = []
    sleep_vals = []
    energy_vals = []
    exercise_types = []
    exercise_total_min = 0
    
    for date, record in records.items():
        morning = record.get("morning", {})
        sleep = record.get("sleep", {})
        
        if morning.get("weight"):
            weights.append(morning["weight"])
        if morning.get("bp_sys"):
            bp_sys_vals.append(morning["bp_sys"])
        if morning.get("bp_dia"):
            bp_dia_vals.append(morning["bp_dia"])
        if morning.get("morning_hr"):
            hr_vals.append(morning["morning_hr"])
        if sleep.get("duration"):
            sleep_vals.append(sleep["duration"])
        if record.get("energy"):
            energy_vals.append(record["energy"])
        
        exercise = record.get("exercise", {})
        if exercise.get("type") and exercise["type"] != "休息":
            exercise_types.append(exercise["type"])
            exercise_total_min += exercise.get("duration_min", 0)
    
    stats["days_recorded"] = len(records)
    stats["avg_weight"] = round(sum(weights) / len(weights), 1) if weights else None
    stats["min_weight"] = min(weights) if weights else None
    stats["max_weight"] = max(weights) if weights else None
    stats["avg_bp_sys"] = round(sum(bp_sys_vals) / len(bp_sys_vals)) if bp_sys_vals else None
    stats["avg_bp_dia"] = round(sum(bp_dia_vals) / len(bp_dia_vals)) if bp_dia_vals else None
    stats["avg_hr"] = round(sum(hr_vals) / len(hr_vals)) if hr_vals else None
    stats["avg_sleep"] = round(sum(sleep_vals) / len(sleep_vals), 1) if sleep_vals else None
    stats["avg_energy"] = round(sum(energy_vals) / len(energy_vals), 1) if energy_vals else None
    stats["exercise_days"] = len(exercise_types)
    stats["exercise_total_min"] = exercise_total_min
    stats["exercise_types"] = exercise_types
    stats["low_energy_days"] = sum(1 for e in energy_vals if e <= 4)
    
    return stats


def trend_arrow(current, previous):
    """趋势箭头"""
    if current is None or previous is None:
        return "→"
    if current > previous:
        return "↑"
    elif current < previous:
        return "↓"
    return "→"


def generate_report(period):
    """生成健康报告"""
    data = load_data()
    config = load_config()
    
    start_date, end_date = get_date_range(period)
    records = extract_records(data, start_date, end_date)
    
    if not records:
        # print(f"❌ {start_date} 至 {end_date} 期间无数据")
        return
    
    stats = calc_stats(records)
    period_name = "周报" if "week" in period or period == "last7" else "月报"
    
    # 计算上期对比
    prev_start = (datetime.strptime(start_date, "%Y-%m-%d") - 
                  timedelta(days=len(records))).strftime("%Y-%m-%d")
    prev_end = (datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    prev_records = extract_records(data, prev_start, prev_end)
    prev_stats = calc_stats(prev_records) if prev_records else {}
    
    report = []
    report.append(f"# 📊 健康{period_name}")
    report.append(f"\n**周期**: {start_date} ~ {end_date}")
    report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append(f"**记录天数**: {stats['days_recorded']}天")
    report.append("")
    
    # === 核心指标 ===
    report.append("## 🎯 核心指标总览")
    report.append("")
    report.append("| 指标 | 本期 | 上期 | 趋势 | 状态 |")
    report.append("|------|------|------|------|------|")
    
    # 体重
    w_trend = trend_arrow(stats["avg_weight"], prev_stats.get("avg_weight"))
    w_status = "✅" if stats["avg_weight"] and 65 <= stats["avg_weight"] <= 85 else "⚠️"
    report.append(f"| 体重(kg) | {stats['avg_weight'] or '-'} | {prev_stats.get('avg_weight', '-')} | {w_trend} | {w_status} |")
    
    # 血压
    bp_trend = trend_arrow(stats["avg_bp_sys"], prev_stats.get("avg_bp_sys"))
    bp_status = "✅" if stats["avg_bp_sys"] and 90 <= stats["avg_bp_sys"] <= 120 else "⚠️"
    report.append(f"| 收缩压(mmHg) | {stats['avg_bp_sys'] or '-'} | {prev_stats.get('avg_bp_sys', '-')} | {bp_trend} | {bp_status} |")
    
    # 心率
    hr_trend = trend_arrow(stats["avg_hr"], prev_stats.get("avg_hr"))
    hr_status = "✅" if stats["avg_hr"] and 50 <= stats["avg_hr"] <= 80 else "⚠️"
    report.append(f"| 晨起心率(bpm) | {stats['avg_hr'] or '-'} | {prev_stats.get('avg_hr', '-')} | {hr_trend} | {hr_status} |")
    
    # 睡眠
    sl_trend = trend_arrow(stats["avg_sleep"], prev_stats.get("avg_sleep"))
    sl_status = "✅" if stats["avg_sleep"] and stats["avg_sleep"] >= 7 else "⚠️"
    report.append(f"| 睡眠时长(h) | {stats['avg_sleep'] or '-'} | {prev_stats.get('avg_sleep', '-')} | {sl_trend} | {sl_status} |")
    
    # 精力
    en_trend = trend_arrow(stats["avg_energy"], prev_stats.get("avg_energy"))
    en_status = "✅" if stats["avg_energy"] and stats["avg_energy"] >= 6 else "⚠️"
    report.append(f"| 精力评分 | {stats['avg_energy'] or '-'} | {prev_stats.get('avg_energy', '-')} | {en_trend} | {en_status} |")
    
    report.append("")
    
    # === 运动统计 ===
    report.append("## 🏃 运动统计")
    report.append("")
    report.append(f"- **运动天数**: {stats['exercise_days']}/{stats['days_recorded']}天")
    report.append(f"- **总运动时长**: {stats['exercise_total_min']}分钟")
    report.append(f"- **平均每周运动**: {round(stats['exercise_total_min'] / max(stats['days_recorded']/7, 1))}分钟")
    
    if stats["exercise_types"]:
        from collections import Counter
        type_counts = Counter(stats["exercise_types"])
        report.append(f"- **运动类型分布**: {', '.join([f'{t}({c}次)' for t, c in type_counts.most_common()])}")
    
    # WHO标准对比
    who_target = 150  # 每周150分钟中等强度有氧
    report.append(f"- **WHO建议达标率**: {min(stats['exercise_total_min'] / (who_target * stats['days_recorded']/7) * 100, 100):.0f}%")
    report.append("")
    
    # === 睡眠质量 ===
    report.append("## 😴 睡眠质量")
    report.append("")
    if stats["avg_sleep"]:
        report.append(f"- **平均睡眠时长**: {stats['avg_sleep']}小时")
        if stats["avg_sleep"] >= 7:
            report.append("- ✅ 达到建议睡眠时长")
        else:
            report.append("- ⚠️ 未达到7小时建议值")
    
    low_energy = stats["low_energy_days"]
    if low_energy > 0:
        report.append(f"- ⚠️ 有{low_energy}天精力评分≤4，需关注")
    else:
        report.append("- ✅ 无低精力日")
    
    report.append("")
    
    # === 每日明细 ===
    report.append("## 📋 每日明细")
    report.append("")
    report.append("| 日期 | 体重 | 血压 | 心率 | 睡眠 | 精力 | 运动 |")
    report.append("|------|------|------|------|------|------|------|")
    
    for date in sorted(records.keys()):
        r = records[date]
        m = r.get("morning", {})
        sl = r.get("sleep", {})
        ex = r.get("exercise", {})
        
        bp = f"{m.get('bp_sys', '-')}/{m.get('bp_dia', '-')}" if m.get("bp_sys") else "-"
        ex_str = f"{ex.get('type', '-')} {ex.get('duration_min', '')}min" if ex.get("type") and ex["type"] != "休息" else "休息"
        
        report.append(f"| {date} | {m.get('weight', '-')} | {bp} | {m.get('morning_hr', '-')} | {sl.get('duration', '-')}h | {r.get('energy', '-')}/10 | {ex_str} |")
    
    report.append("")
    
    # === 建议 ===
    report.append("## 💡 健康建议")
    report.append("")
    
    suggestions = []
    
    if stats["avg_sleep"] and stats["avg_sleep"] < 7:
        suggestions.append(f"🔵 睡眠不足：本周平均{stats['avg_sleep']}小时，建议增加至7-8小时")
    
    if stats["avg_weight"] and stats["avg_weight"] > 80:
        suggestions.append("🔵 体重偏高：建议控制饮食+增加有氧运动")
    
    if stats["exercise_days"] < 3 and stats["days_recorded"] >= 5:
        suggestions.append(f"🔵 运动不足：本周仅{stats['exercise_days']}天运动，建议增加到3-5天")
    
    if stats["avg_bp_sys"] and stats["avg_bp_sys"] > 120:
        suggestions.append(f"🔴 血压偏高：平均收缩压{stats['avg_bp_sys']}mmHg，建议就医")
    
    if stats["low_energy_days"] > 2:
        suggestions.append(f"🔴 精力透支：{stats['low_energy_days']}天精力≤4，建议充分休息")
    
    if not suggestions:
        suggestions.append("✅ 本周各项指标良好，继续保持！")
    
    for s in suggestions:
        report.append(f"- {s}")
    
    report.append("")
    
    # 保存报告
    period_label = "weekly" if "week" in period or period == "last7" else "monthly"
    report_date = datetime.now().strftime("%Y%m%d")
    filename = f"health-{period_label}-report-{report_date}.md"
    filepath = DATA_DIR / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    
    # print(f"\n✅ {period_name}已生成: {filename}")
    # print(f"📄 保存路径: {filepath}")
    
    # 同时输出到控制台
    # print("\n" + "=" * 50)
    # print("\n".join(report))


def generate_dashboard():
    """生成实时健康仪表盘"""
    data = load_data()
    config = load_config()
    
    today = datetime.now()
    
    # 最近7天和30天
    r7_start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    r7_end = today.strftime("%Y-%m-%d")
    r30_start = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    
    records_7 = extract_records(data, r7_start, r7_end)
    records_30 = extract_records(data, r30_start, r7_end)
    
    stats_7 = calc_stats(records_7)
    stats_30 = calc_stats(records_30)
    
    lines = []
    lines.append("# 🏥 健康仪表盘")
    lines.append(f"\n**更新时间**: {today.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**总记录天数**: {len(data)}天")
    lines.append("")
    
    # 健康评分
    lines.append("## 📊 健康评分")
    lines.append("")
    
    score = 0
    max_score = 0
    
    # 睡眠评分 (0-25)
    if stats_7["avg_sleep"]:
        max_score += 25
        if stats_7["avg_sleep"] >= 7.5:
            score += 25
        elif stats_7["avg_sleep"] >= 7:
            score += 20
        elif stats_7["avg_sleep"] >= 6:
            score += 12
        else:
            score += 5
    
    # 运动评分 (0-25)
    if stats_7["days_recorded"] > 0:
        max_score += 25
        exercise_rate = stats_7["exercise_days"] / stats_7["days_recorded"]
        if exercise_rate >= 0.6:
            score += 25
        elif exercise_rate >= 0.4:
            score += 20
        elif exercise_rate >= 0.2:
            score += 12
        else:
            score += 5
    
    # 精力评分 (0-25)
    if stats_7["avg_energy"]:
        max_score += 25
        score += stats_7["avg_energy"] * 2.5
    
    # 血压评分 (0-25)
    if stats_7["avg_bp_sys"]:
        max_score += 25
        if 90 <= stats_7["avg_bp_sys"] <= 120:
            score += 25
        elif 85 <= stats_7["avg_bp_sys"] <= 130:
            score += 15
        else:
            score += 5
    
    if max_score > 0:
        health_score = round(score / max_score * 100)
    else:
        health_score = None
    
    if health_score:
        if health_score >= 80:
            level = "🟢 优秀"
        elif health_score >= 60:
            level = "🟡 良好"
        elif health_score >= 40:
            level = "🟠 需关注"
        else:
            level = "🔴 需改善"
        
        lines.append(f"**综合健康评分**: {health_score}/100 — {level}")
    else:
        lines.append("**综合健康评分**: 数据不足，请先录入数据")
    
    lines.append("")
    
    # 7天统计
    lines.append("## 📅 近7天统计")
    lines.append("")
    lines.append(f"| 指标 | 数值 | 状态 |")
    lines.append(f"|------|------|------|")
    
    if stats_7["avg_weight"]:
        lines.append(f"| 平均体重 | {stats_7['avg_weight']}kg | {'✅' if 65 <= stats_7['avg_weight'] <= 85 else '⚠️'} |")
    if stats_7["avg_bp_sys"]:
        lines.append(f"| 平均收缩压 | {stats_7['avg_bp_sys']}mmHg | {'✅' if 90 <= stats_7['avg_bp_sys'] <= 120 else '⚠️'} |")
    if stats_7["avg_hr"]:
        lines.append(f"| 平均心率 | {stats_7['avg_hr']}bpm | {'✅' if 50 <= stats_7['avg_hr'] <= 80 else '⚠️'} |")
    if stats_7["avg_sleep"]:
        lines.append(f"| 平均睡眠 | {stats_7['avg_sleep']}h | {'✅' if stats_7['avg_sleep'] >= 7 else '⚠️'} |")
    if stats_7["avg_energy"]:
        lines.append(f"| 平均精力 | {stats_7['avg_energy']}/10 | {'✅' if stats_7['avg_energy'] >= 6 else '⚠️'} |")
    lines.append(f"| 运动天数 | {stats_7['exercise_days']}/{stats_7['days_recorded']} | {'✅' if stats_7['exercise_days'] >= 3 else '⚠️'} |")
    
    lines.append("")
    
    # 30天趋势
    lines.append("## 📈 30天趋势对比")
    lines.append("")
    lines.append("| 指标 | 近7天 | 近30天 | 差异 |")
    lines.append("|------|-------|--------|------|")
    
    if stats_7["avg_weight"] and stats_30["avg_weight"]:
        diff = stats_7["avg_weight"] - stats_30["avg_weight"]
        lines.append(f"| 体重 | {stats_7['avg_weight']}kg | {stats_30['avg_weight']}kg | {diff:+.1f}kg |")
    if stats_7["avg_sleep"] and stats_30["avg_sleep"]:
        diff = stats_7["avg_sleep"] - stats_30["avg_sleep"]
        lines.append(f"| 睡眠 | {stats_7['avg_sleep']}h | {stats_30['avg_sleep']}h | {diff:+.1f}h |")
    if stats_7["avg_energy"] and stats_30["avg_energy"]:
        diff = stats_7["avg_energy"] - stats_30["avg_energy"]
        lines.append(f"| 精力 | {stats_7['avg_energy']}/10 | {stats_30['avg_energy']}/10 | {diff:+.1f} |")
    
    lines.append("")
    
    # 连续记录天数
    lines.append("## 🔥 连续记录")
    lines.append("")
    consecutive = 0
    for i in range(365):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        if date_str in data:
            consecutive += 1
        else:
            break
    
    if consecutive > 0:
        lines.append(f"- 连续记录: **{consecutive}天**")
        if consecutive >= 30:
            lines.append("- 🔥 已坚持一个月以上，继续保持！")
        elif consecutive >= 7:
            lines.append("- 👍 已坚持一周以上，加油！")
    else:
        lines.append("- 暂无连续记录")
    
    lines.append("")
    
    # 保存
    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    # print(f"✅ 仪表盘已更新: {DASHBOARD_FILE}")
    # print("\n" + "\n".join(lines))


def main():
    if len(sys.argv) < 2:
        # print("用法:")
        # print("  python3 health-report.py weekly     # 上周周报")
        # print("  python3 health-report.py monthly    # 上月月报")
        # print("  python3 health-report.py dashboard  # 实时仪表盘")
        return
    
    command = sys.argv[1]
    
    if command == "weekly":
        generate_report("weekly")
    elif command == "monthly":
        generate_report("monthly")
    elif command == "dashboard":
        generate_dashboard()
    else:
        # print(f"❌ 未知命令: {command}")
        # print("可用命令: weekly, monthly, dashboard")


if __name__ == "__main__":
    main()

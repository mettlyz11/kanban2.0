#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康指标追踪系统 - 核心脚本
适用于：刘宇宙教授（高频脑力工作者 + 创业者）
版本: v1.0 | 创建日期: 2026-04-26

功能：
1. 每日健康数据记录
2. 趋势分析与可视化
3. 健康周报生成
4. 健康预警检测
"""

import sqlite3
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import statistics

# ==================== 配置区 ====================

# 数据库路径（自动放在脚本同目录下的 data/ 子目录）
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "health_data.db")

# 健康参考值
HEALTH_BENCHMARKS = {
    "sleep_hours_min": 7.0,      # 最低建议睡眠时长
    "sleep_hours_optimal": 7.5,  # 最佳睡眠时长
    "water_cups_min": 8,         # 最低饮水杯数
    "exercise_min_min": 30,      # 最低运动分钟数
    "stress_max": 3,             # 最大可接受压力水平
    "energy_min": 5,             # 最低精力评分
}


# ==================== 数据库管理 ====================

def init_db():
    """初始化数据库，创建所需表"""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 每日记录表
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_records (
            date TEXT PRIMARY KEY,
            sleep_hours REAL,
            sleep_quality INTEGER CHECK(sleep_quality BETWEEN 1 AND 5),
            steps INTEGER,
            exercise_minutes INTEGER,
            exercise_type TEXT,
            energy_morning INTEGER CHECK(energy_morning BETWEEN 1 AND 10),
            energy_afternoon INTEGER CHECK(energy_afternoon BETWEEN 1 AND 10),
            energy_evening INTEGER CHECK(energy_evening BETWEEN 1 AND 10),
            stress_level INTEGER CHECK(stress_level BETWEEN 1 AND 5),
            focus_hours REAL,
            water_cups INTEGER,
            caffeine_count INTEGER,
            meals_regular INTEGER CHECK(meals_regular BETWEEN 0 AND 1),
            weight REAL,
            resting_hr INTEGER,
            hrv REAL,
            supplements TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 每周报告表
    c.execute('''
        CREATE TABLE IF NOT EXISTS weekly_reports (
            week_start TEXT PRIMARY KEY,
            week_end TEXT,
            avg_sleep REAL,
            avg_sleep_quality REAL,
            total_steps INTEGER,
            total_exercise INTEGER,
            avg_energy_morning REAL,
            avg_energy_afternoon REAL,
            avg_energy_evening REAL,
            avg_stress REAL,
            avg_focus REAL,
            avg_water REAL,
            avg_weight REAL,
            avg_resting_hr REAL,
            red_alerts INTEGER,
            yellow_alerts INTEGER,
            summary TEXT,
            next_week_goals TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 预警记录表
    c.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            level TEXT CHECK(level IN ('red', 'yellow', 'green')),
            metric TEXT,
            value TEXT,
            threshold TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    # print(f"✅ 数据库初始化完成: {DB_PATH}")


# ==================== 数据录入 ====================

def record_today():
    """交互式记录今日健康数据"""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 检查今天是否已记录
    c.execute("SELECT date FROM daily_records WHERE date = ?", (today,))
    existing = c.fetchone()

    if existing:
        # print(f"\n📝 检测到今天({today})已有记录，将更新现有数据。")
        c.execute("SELECT * FROM daily_records WHERE date = ?", (today,))
        row = c.fetchone()
        columns = [desc[0] for desc in c.description]
        # print("当前记录：")
        for col, val in zip(columns, row):
            if val is not None and col not in ('created_at', 'updated_at'):
                # print(f"  {col}: {val}")

    # print(f"\n{'='*50}")
    # print(f"📊 健康数据记录 - {today}")
    # print(f"{'='*50}")

    data = {}

    # 睡眠
    # print("\n🌙 睡眠")
    data['sleep_hours'] = ask_float("  睡眠时长(小时)", default=7.5)
    data['sleep_quality'] = ask_int("  睡眠质量(1-5, 5=极好)", default=3)

    # 运动
    # print("\n🏃 运动")
    data['steps'] = ask_int("  步数", default=8000)
    data['exercise_minutes'] = ask_int("  运动时长(分钟)", default=0)
    data['exercise_type'] = ask_str("  运动类型(如:跑步/游泳/瑜伽/无)", default="")

    # 精力
    # print("\n⚡ 精力")
    data['energy_morning'] = ask_int("  早晨精力(1-10)", default=7)
    data['energy_afternoon'] = ask_int("  午后精力(1-10)", default=6)
    data['energy_evening'] = ask_int("  晚间精力(1-10)", default=5)
    data['stress_level'] = ask_int("  压力水平(1-5, 5=极高)", default=3)
    data['focus_hours'] = ask_float("  有效专注时长(小时)", default=4.0)

    # 营养
    # print("\n🥗 营养")
    data['water_cups'] = ask_int("  饮水杯数(每杯~250ml)", default=8)
    data['caffeine_count'] = ask_int("  咖啡因次数(咖啡/茶)", default=1)
    data['meals_regular'] = 1 if ask_str("  三餐是否规律?(y/n)", default="y").lower() == "y" else 0

    # 身体指标
    # print("\n📏 身体指标（可选，留空跳过）")
    data['weight'] = ask_float_optional("  体重(kg)")
    data['resting_hr'] = ask_int_optional("  静息心率(bpm)")
    data['hrv'] = ask_float_optional("  HRV(ms)")
    data['supplements'] = ask_str("  补剂(如:维D/鱼油/综合)", default="")

    # 备注
    data['notes'] = ask_str("  备注", default="")

    # 写入数据库
    columns = ', '.join(data.keys() + ['date'])
    placeholders = ', '.join(['?' for _ in data] + ['?'])
    values = list(data.values()) + [today]

    if existing:
        # UPDATE
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        c.execute(f"UPDATE daily_records SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE date = ?",
                  list(data.values()) + [today])
    else:
        # INSERT
        c.execute(f"INSERT INTO daily_records (date, {', '.join(data.keys())}) VALUES ({placeholders})",
                  values)

    conn.commit()
    conn.close()
    # print(f"\n✅ 今日数据已保存！")

    # 立即检测预警
    check_alerts(today, data)


def ask_float(prompt, default=None):
    val = input(f"{prompt} [{default}]: ").strip()
    if not val:
        return default
    try:
        return float(val)
    except ValueError:
        # print(f"  ⚠️ 无效输入，使用默认值 {default}")
        return default


def ask_int(prompt, default=None):
    val = input(f"{prompt} [{default}]: ").strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        # print(f"  ⚠️ 无效输入，使用默认值 {default}")
        return default


def ask_str(prompt, default=None):
    val = input(f"{prompt} [{default}]: ").strip()
    if not val:
        return default
    return val


def ask_float_optional(prompt):
    val = input(f"{prompt} [跳过]: ").strip()
    if not val:
        return None
    try:
        return float(val)
    except ValueError:
        # print(f"  ⚠️ 无效输入，跳过")
        return None


def ask_int_optional(prompt):
    val = input(f"{prompt} [跳过]: ").strip()
    if not val:
        return None
    try:
        return int(val)
    except ValueError:
        # print(f"  ⚠️ 无效输入，跳过")
        return None


# ==================== 数据分析 ====================

def check_alerts(date, data):
    """检查健康预警条件"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    alerts = []

    # 睡眠预警
    if data.get('sleep_hours') and data['sleep_hours'] < HEALTH_BENCHMARKS['sleep_hours_min']:
        alerts.append(('yellow', 'sleep_hours',
                       f"{data['sleep_hours']}h",
                       f"≥{HEALTH_BENCHMARKS['sleep_hours_min']}h",
                       "⚠️ 睡眠不足，建议今晚早睡"))

    # 连续睡眠不足检测（查过去3天）
    c.execute('''SELECT COUNT(*) FROM daily_records 
                 WHERE date >= date(?, '-2 days') 
                 AND sleep_hours < ?''',
              (date, HEALTH_BENCHMARKS['sleep_hours_min']))
    if c.fetchone()[0] >= 3:
        alerts.append(('red', 'sleep_hours_3days',
                       "连续3天不足",
                       "需连续≥6h",
                       "🔴 连续3天睡眠不足！请安排休息"))

    # 运动预警
    if data.get('exercise_minutes') is not None and data['exercise_minutes'] < HEALTH_BENCHMARKS['exercise_min_min']:
        alerts.append(('yellow', 'exercise',
                       f"{data['exercise_minutes']}min",
                       f"≥{HEALTH_BENCHMARKS['exercise_min_min']}min",
                       "⚠️ 运动量不足，建议活动30分钟"))

    # 压力预警
    if data.get('stress_level') and data['stress_level'] > HEALTH_BENCHMARKS['stress_max']:
        alerts.append(('yellow', 'stress',
                       f"L{data['stress_level']}",
                       f"≤L{HEALTH_BENCHMARKS['stress_max']}",
                       "⚠️ 压力偏高，建议深呼吸/冥想5分钟"))

    # 饮水预警
    if data.get('water_cups') and data['water_cups'] < HEALTH_BENCHMARKS['water_cups_min']:
        alerts.append(('yellow', 'water',
                       f"{data['water_cups']}杯",
                       f"≥{HEALTH_BENCHMARKS['water_cups_min']}杯",
                       "⚠️ 饮水不足，请再喝杯水"))

    # 精力预警
    energy_vals = [v for v in [data.get('energy_morning'), data.get('energy_afternoon'), data.get('energy_evening')] if v]
    if energy_vals:
        avg_energy = statistics.mean(energy_vals)
        if avg_energy < HEALTH_BENCHMARKS['energy_min']:
            alerts.append(('red', 'energy_low',
                           f"均分{avg_energy:.1f}",
                           f"≥{HEALTH_BENCHMARKS['energy_min']}",
                           "🔴 全天精力低迷，请适当休息"))

    # 记录预警
    for level, metric, value, threshold, message in alerts:
        c.execute('''INSERT INTO alerts (date, level, metric, value, threshold, message) 
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (date, level, metric, value, threshold, message))

    conn.commit()

    # 打印预警
    if alerts:
        # print(f"\n{'='*40}")
        # print("🔔 健康预警")
        # print(f"{'='*40}")
        for level, metric, value, threshold, message in alerts:
            emoji = "🔴" if level == "red" else "🟡"
            # print(f"  {emoji} {message}")
            # print(f"     指标: {value} (基准: {threshold})")
        # print()
    else:
        # print("\n✅ 所有指标正常，状态良好！\n")

    conn.close()


def get_trend(days=7):
    """获取最近N天的趋势分析"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''SELECT * FROM daily_records 
                 WHERE date >= date('now', ?) 
                 ORDER BY date''', (f'-{days} days',))
    rows = [dict(row) for row in c.fetchall()]
    conn.close()

    if not rows:
        # print("📭 暂无数据，请先记录几天数据。")
        return

    # print(f"\n{'='*50}")
    # print(f"📈 {days}日健康趋势")
    # print(f"{'='*50}")

    # 计算均值
    metrics = {
        '睡眠时长': ('sleep_hours', 'h', 1),
        '睡眠质量': ('sleep_quality', '/5', 0),
        '步数': ('steps', '步', 0),
        '运动时长': ('exercise_minutes', 'min', 0),
        '晨间精力': ('energy_morning', '/10', 0),
        '午后精力': ('energy_afternoon', '/10', 0),
        '晚间精力': ('energy_evening', '/10', 0),
        '压力水平': ('stress_level', '/5', 0),
        '专注时长': ('focus_hours', 'h', 1),
        '饮水': ('water_cups', '杯', 0),
    }

    # print(f"\n{'指标':<12} {'均值':>8} {'最低':>8} {'最高':>8} {'趋势':>8}")
    # print("-" * 50)

    for name, (key, unit, precision) in metrics.items():
        vals = [r[key] for r in rows if r.get(key) is not None]
        if not vals:
            continue
        avg = statistics.mean(vals)
        mn = min(vals)
        mx = max(vals)
        # 简单趋势判断
        if len(vals) >= 3:
            first_half = statistics.mean(vals[:len(vals)//2])
            second_half = statistics.mean(vals[len(vals)//2:])
            if second_half > first_half * 1.1:
                trend = "📈 ↑"
            elif second_half < first_half * 0.9:
                trend = "📉 ↓"
            else:
                trend = "➡️ →"
        else:
            trend = "➡️ →"

        fmt = f"{{:.{precision}f}}"
        # print(f"{name:<12} {fmt.format(avg):>6}{unit} {fmt.format(mn):>6}{unit} {fmt.format(mx):>6}{unit} {trend:>8}")

    # print()


# ==================== 报告生成 ====================

def generate_weekly_report():
    """生成并保存每周健康报告"""
    today = datetime.now()
    # 计算本周周一
    week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
    week_end = today.strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''SELECT * FROM daily_records 
                 WHERE date >= ? AND date <= ? 
                 ORDER BY date''', (week_start, week_end))
    rows = [dict(row) for row in c.fetchall()]

    if len(rows) < 3:
        # print(f"📭 本周数据不足（仅{len(rows)}天），建议积累更多数据后生成周报。")
        conn.close()
        return

    # 计算统计值
    def avg_val(key):
        vals = [r[key] for r in rows if r.get(key) is not None]
        return statistics.mean(vals) if vals else None

    def sum_val(key):
        vals = [r[key] for r in rows if r.get(key) is not None]
        return sum(vals) if vals else None

    report = {
        'week_start': week_start,
        'week_end': week_end,
        'avg_sleep': avg_val('sleep_hours'),
        'avg_sleep_quality': avg_val('sleep_quality'),
        'total_steps': sum_val('steps'),
        'total_exercise': sum_val('exercise_minutes'),
        'avg_energy_morning': avg_val('energy_morning'),
        'avg_energy_afternoon': avg_val('energy_afternoon'),
        'avg_energy_evening': avg_val('energy_evening'),
        'avg_stress': avg_val('stress_level'),
        'avg_focus': avg_val('focus_hours'),
        'avg_water': avg_val('water_cups'),
        'avg_weight': avg_val('weight'),
        'avg_resting_hr': avg_val('resting_hr'),
    }

    # 预警统计
    c.execute('''SELECT level, COUNT(*) FROM alerts 
                 WHERE date >= ? AND date <= ? 
                 GROUP BY level''', (week_start, week_end))
    alert_counts = dict(c.fetchall())
    report['red_alerts'] = alert_counts.get('red', 0)
    report['yellow_alerts'] = alert_counts.get('yellow', 0)

    # 生成摘要
    summary = generate_summary(report, rows)
    report['summary'] = summary

    # 保存到数据库
    c.execute('''INSERT OR REPLACE INTO weekly_reports 
                 (week_start, week_end, avg_sleep, avg_sleep_quality, total_steps, total_exercise,
                  avg_energy_morning, avg_energy_afternoon, avg_energy_evening, avg_stress,
                  avg_focus, avg_water, avg_weight, avg_resting_hr, red_alerts, yellow_alerts, summary)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (report['week_start'], report['week_end'],
               report['avg_sleep'], report['avg_sleep_quality'],
               report['total_steps'], report['total_exercise'],
               report['avg_energy_morning'], report['avg_energy_afternoon'], report['avg_energy_evening'],
               report['avg_stress'], report['avg_focus'], report['avg_water'],
               report['avg_weight'], report['avg_resting_hr'],
               report['red_alerts'], report['yellow_alerts'], summary))
    conn.commit()
    conn.close()

    # 打印报告
    print_weekly_report(report, rows)


def generate_summary(report, rows):
    """生成智能健康摘要"""
    lines = []

    if report['avg_sleep'] and report['avg_sleep'] >= 7.0:
        lines.append("✅ 睡眠充足，平均%.1f小时" % report['avg_sleep'])
    elif report['avg_sleep']:
        lines.append("⚠️ 睡眠偏少，平均%.1f小时" % report['avg_sleep'])

    if report['total_exercise'] and report['total_exercise'] >= 150:
        lines.append("✅ 运动达标，本周累计%g分钟" % report['total_exercise'])
    elif report['total_exercise']:
        lines.append("⚠️ 运动不足，本周仅%g分钟" % report['total_exercise'])

    avg_energy = statistics.mean([
        v for v in [report['avg_energy_morning'], report['avg_energy_afternoon'], report['avg_energy_evening']]
        if v
    ]) if any([report['avg_energy_morning'], report['avg_energy_afternoon'], report['avg_energy_evening']]) else None

    if avg_energy:
        if avg_energy >= 6:
            lines.append("✅ 精力良好，日均%.1f/10" % avg_energy)
        else:
            lines.append("⚠️ 精力偏低，日均%.1f/10" % avg_energy)

    if report['red_alerts'] > 0:
        lines.append("🔴 本周%d次红色预警，需重点关注" % report['red_alerts'])

    return "; ".join(lines)


def print_weekly_report(report, rows):
    """格式化打印周报"""
    # print(f"\n{'='*55}")
    # print(f"📋 健康周报 | {report['week_start']} ~ {report['week_end']}")
    # print(f"{'='*55}")

    # print(f"\n🌙 睡眠")
    if report['avg_sleep']:
        status = "✅" if report['avg_sleep'] >= 7.0 else "⚠️"
        # print(f"  {status} 平均 {report['avg_sleep']:.1f}h (质量 {report['avg_sleep_quality']:.1f}/5)")

    # print(f"\n🏃 运动")
    if report['total_exercise'] is not None:
        status = "✅" if report['total_exercise'] >= 150 else "⚠️"
        # print(f"  {status} 累计 {report['total_exercise']}min | 步数 {report['total_steps'] or 0:,}")

    # print(f"\n⚡ 精力")
    for label, key in [('晨间', 'avg_energy_morning'), ('午后', 'avg_energy_afternoon'), ('晚间', 'avg_energy_evening')]:
        if report[key]:
            # print(f"  {label}: {report[key]:.1f}/10")
    if report['avg_stress']:
        status = "⚠️" if report['avg_stress'] > 3 else "✅"
        # print(f"  {status} 压力: {report['avg_stress']:.1f}/5")

    # print(f"\n🥗 营养")
    if report['avg_water']:
        status = "✅" if report['avg_water'] >= 8 else "⚠️"
        # print(f"  {status} 饮水: {report['avg_water']:.1f}杯/日")
    if report['avg_focus']:
        # print(f"  专注: {report['avg_focus']:.1f}h/日")

    if report['avg_weight']:
        # print(f"\n📏 体重: {report['avg_weight']:.1f}kg")
    if report['avg_resting_hr']:
        # print(f"  静息心率: {report['avg_resting_hr']:.0f}bpm")

    # print(f"\n🔔 预警: 🔴{report['red_alerts']}次  🟡{report['yellow_alerts']}次")

    # print(f"\n📝 摘要: {report.get('summary', 'N/A')}")
    # print(f"\n{'='*55}\n")


# ==================== 命令行入口 ====================

def main():
    init_db()

    if len(sys.argv) < 2:
        # 默认：记录今日数据
        record_today()
        return

    cmd = sys.argv[1]

    if cmd == 'record' or cmd == '-r':
        record_today()
    elif cmd == 'trend' or cmd == '-t':
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        get_trend(days)
    elif cmd == 'weekly-report' or cmd == '-w':
        generate_weekly_report()
    elif cmd == 'status' or cmd == '-s':
        # 快速状态查看
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM daily_records")
        total = c.fetchone()[0]
        c.execute("SELECT MAX(date) FROM daily_records")
        last = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM alerts WHERE level = 'red'")
        red = c.fetchone()[0]
        conn.close()
        # print(f"\n📊 健康追踪状态")
        # print(f"  总记录: {total} 天")
        # print(f"  最后记录: {last or '无'}")
        # print(f"  红色预警: {red} 次")
        # print()
    elif cmd == 'help' or cmd == '-h':
        # print("""
健康指标追踪系统 v1.0
=====================

用法:
  python3 health_tracker.py              # 记录今日数据
  python3 health_tracker.py record       # 同上
  python3 health_tracker.py trend [N]    # 查看最近N天趋势(默认7)
  python3 health_tracker.py weekly-report # 生成周报
  python3 health_tracker.py status       # 查看系统状态
  python3 health_tracker.py help         # 显示帮助
        """)
    else:
        # print(f"❌ 未知命令: {cmd}")
        # print("使用 'help' 查看可用命令")


if __name__ == "__main__":
    main()

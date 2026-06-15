#!/usr/bin/env python3
"""
每日健康打卡脚本 - daily_health_check.py
用法: python3 daily_health_check.py [--weekly]

功能：
1. 命令行交互式录入每日健康数据
2. 数据存储到本地 SQLite（轻量，无需网络）
3. 自动生成周报（--weekly模式）

作者: Dudu (OpenClaw)
日期: 2026-04-26
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# 数据库设置 - 本地 SQLite，保护隐私
# ============================================================
DB_DIR = Path.home() / ".openclaw" / "workspace" / "health_data"
DB_FILE = DB_DIR / "health_tracker.db"

def init_db():
    """初始化数据库表"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_FILE))
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS daily_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE NOT NULL,
        morning_energy INTEGER,
        morning_focus INTEGER,
        afternoon_energy INTEGER,
        sleep_quality INTEGER,
        stress_level INTEGER,
        weight REAL,
        resting_heart_rate INTEGER,
        blood_oxygen REAL,
        steps INTEGER,
        exercise_minutes INTEGER,
        sleep_hours REAL,
        water_cups INTEGER,
        screen_time_hours REAL,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS weekly_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week_start TEXT UNIQUE NOT NULL,
        avg_morning_energy REAL,
        avg_afternoon_energy REAL,
        avg_sleep_quality REAL,
        avg_stress REAL,
        avg_steps REAL,
        avg_sleep_hours REAL,
        alerts TEXT,
        recommendations TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()
    return str(DB_FILE)


# ============================================================
# 每日打卡
# ============================================================
def daily_check():
    """交互式每日健康打卡"""
    today = datetime.now().strftime("%Y-%m-%d")

    # print(f"\n{'='*50}")
    # print(f"🏥  每日健康打卡 — {today}")
    # print(f"{'='*50}\n")

    # 检查是否已经打卡
    conn = sqlite3.connect(str(DB_FILE))
    c = conn.cursor()
    c.execute("SELECT id FROM daily_entries WHERE date = ?", (today,))
    if c.fetchone():
        # print("⚠️  今日已打卡，将更新记录。\n")

    # 精力指标
    # print("--- 精力指标 (1-10分) ---")
    morning_energy = get_int_input("  晨起精力: ", 1, 10)
    morning_focus = get_int_input("  上午专注度 (9-12点): ", 1, 10)
    afternoon_energy = get_int_input("  下午精力 (14-17点): ", 1, 10)
    sleep_quality = get_int_input("  睡眠质量: ", 1, 10)
    stress_level = get_int_input("  压力水平 (1最低): ", 1, 10)

    # 生理指标（可选）
    # print("\n--- 生理指标 (选填, 直接回车跳过) ---")
    weight = get_float_input("  体重 (kg): ")
    resting_heart_rate = get_int_input("  静息心率 (bpm): ", 40, 150)
    blood_oxygen = get_float_input("  血氧 (%): ", 85, 100)

    # 行为指标
    # print("\n--- 行为指标 (选填) ---")
    steps = get_int_input("  步数: ")
    exercise_minutes = get_int_input("  运动时长 (分钟): ")
    sleep_hours = get_float_input("  睡眠时长 (小时): ", 0, 24)
    water_cups = get_int_input("  喝水杯数: ")
    screen_time = get_float_input("  屏幕时间 (小时): ", 0, 24)

    notes = input("\n📝 备注 (可选): ").strip()

    # 保存数据
    c.execute('''INSERT OR REPLACE INTO daily_entries
        (date, morning_energy, morning_focus, afternoon_energy,
         sleep_quality, stress_level, weight, resting_heart_rate,
         blood_oxygen, steps, exercise_minutes, sleep_hours,
         water_cups, screen_time_hours, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (today, morning_energy, morning_focus, afternoon_energy,
         sleep_quality, stress_level, weight, resting_heart_rate,
         blood_oxygen, steps, exercise_minutes, sleep_hours,
         water_cups, screen_time, notes))

    conn.commit()
    conn.close()

    # 即时反馈
    # print(f"\n{'='*50}")
    # print("✅ 打卡完成！")
    # print(f"{'='*50}")
    give_instant_feedback(morning_energy, afternoon_energy, sleep_quality,
                          stress_level, sleep_hours, steps, water_cups)


def give_instant_feedback(morning_energy, afternoon_energy, sleep_quality,
                          stress_level, sleep_hours=None, steps=None, water_cups=None):
    """根据今日数据给出即时反馈"""
    alerts = []

    if morning_energy and morning_energy <= 3:
        alerts.append("⚠️ 晨起精力偏低，建议今晚早睡")
    if afternoon_energy and afternoon_energy <= 3:
        alerts.append("⚠️ 下午精力不足，考虑午休15-20分钟")
    if sleep_quality and sleep_quality <= 3:
        alerts.append("⚠️ 睡眠质量差，建议减少睡前屏幕时间")
    if stress_level and stress_level >= 8:
        alerts.append("🔴 压力过高！建议安排放松活动（散步/冥想）")
    if sleep_hours and sleep_hours < 6:
        alerts.append("⚠️ 睡眠不足6小时，身体需要恢复")
    if steps and steps < 5000:
        alerts.append("📉 步数偏少，建议适当活动")
    if water_cups and water_cups < 6:
        alerts.append("💧 喝水偏少，记得补充水分")

    if alerts:
        # print("\n📊 即时反馈：")
        for a in alerts:
            # print(f"  {a}")
    else:
        # print("\n🎉 各项指标正常，继续保持！")


# ============================================================
# 周报生成
# ============================================================
def generate_weekly_report():
    """生成上周健康周报"""
    today = datetime.now()
    week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
    week_end = (today + timedelta(days=6-today.weekday())).strftime("%Y-%m-%d")

    conn = sqlite3.connect(str(DB_FILE))
    c = conn.cursor()

    # 获取本周数据
    c.execute('''SELECT
        AVG(morning_energy), AVG(afternoon_energy), AVG(sleep_quality),
        AVG(stress_level), AVG(steps), AVG(sleep_hours),
        AVG(weight), AVG(resting_heart_rate)
        FROM daily_entries
        WHERE date >= ? AND date <= ?''', (week_start, week_end))

    row = c.fetchone()
    if not row or all(v is None for v in row):
        # print("❌ 本周暂无数据，无法生成周报")
        conn.close()
        return

    avg_morning, avg_afternoon, avg_sleep_q, avg_stress, avg_steps, avg_sleep_h, avg_weight, avg_rhr = row

    # 检测警报
    alerts = []
    if avg_morning and avg_morning < 4:
        alerts.append("🔴 晨起精力持续偏低")
    if avg_stress and avg_stress > 7:
        alerts.append("🔴 平均压力过高")
    if avg_sleep_h and avg_sleep_h < 6:
        alerts.append("🔴 平均睡眠不足6小时")
    if avg_steps and avg_steps < 5000:
        alerts.append("⚠️ 平均步数不足")
    if avg_rhr and avg_rhr > 80:
        alerts.append("⚠️ 静息心率偏高")

    # 生成建议
    recommendations = []
    if avg_morning and avg_morning < 6:
        recommendations.append("建议提前30分钟就寝，改善晨起状态")
    if avg_stress and avg_stress > 5:
        recommendations.append("建议每天安排15分钟冥想/深呼吸")
    if (avg_steps or 0) < 8000:
        recommendations.append("建议每天增加步行，目标8000步")
    if not recommendations:
        recommendations.append("各项指标正常，继续保持当前节奏")

    # 保存周报
    alerts_str = "\n".join(alerts) if alerts else "无异常"
    recs_str = "\n".join(recommendations)

    c.execute('''INSERT OR REPLACE INTO weekly_reports
        (week_start, avg_morning_energy, avg_afternoon_energy,
         avg_sleep_quality, avg_stress, avg_steps, avg_sleep_hours,
         alerts, recommendations)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (week_start, avg_morning, avg_afternoon, avg_sleep_q,
         avg_stress, avg_steps, avg_sleep_h, alerts_str, recs_str))

    conn.commit()
    conn.close()

    # 打印周报
    # print(f"\n{'='*50}")
    # print(f"📊 周健康报告 ({week_start} ~ {week_end})")
    # print(f"{'='*50}")
    # print(f"  晨起精力: {avg_morning:.1f}/10 {'✅' if (avg_morning or 0) >= 6 else '⚠️'}")
    # print(f"  下午精力: {avg_afternoon:.1f}/10 {'✅' if (avg_afternoon or 0) >= 5 else '⚠️'}")
    # print(f"  睡眠质量: {avg_sleep_q:.1f}/10 {'✅' if (avg_sleep_q or 0) >= 6 else '⚠️'}")
    # print(f"  压力水平: {avg_stress:.1f}/10 {'⚠️' if (avg_stress or 0) > 7 else '✅'}")
    # print(f"  平均步数: {avg_steps:.0f} {'✅' if (avg_steps or 0) >= 8000 else '⚠️'}")
    # print(f"  平均睡眠: {avg_sleep_h:.1f}h {'✅' if (avg_sleep_h or 0) >= 6.5 else '⚠️'}")

    if alerts:
        # print(f"\n🚨 警报:")
        for a in alerts:
            # print(f"  {a}")

    # print(f"\n💡 建议:")
    for r in recommendations:
        # print(f"  → {r}")

    # print()


# ============================================================
# 历史数据查看
# ============================================================
def show_history(days=7):
    """显示最近N天的健康数据"""
    conn = sqlite3.connect(str(DB_FILE))
    c = conn.cursor()

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    c.execute('''SELECT date, morning_energy, afternoon_energy, sleep_quality,
                  stress_level, steps, sleep_hours
                  FROM daily_entries
                  WHERE date >= ? ORDER BY date DESC''', (cutoff,))

    rows = c.fetchall()
    conn.close()

    if not rows:
        # print("📭 暂无历史数据")
        return

    # print(f"\n{'='*60}")
    # print(f"📋 最近{days}天健康记录")
    # print(f"{'='*60}")
    # print(f"{'日期':>12} {'晨精力':>5} {'午精力':>5} {'睡眠':>5} {'压力':>5} {'步数':>6} {'睡眠h':>5}")
    # print(f"{'-'*60}")
    for r in rows:
        date, me, ae, sq, st, steps, sh = r
        # print(f"{date:>12} {str(me or '-'):>5} {str(ae or '-'):>5} {str(sq or '-'):>5} {str(st or '-'):>5} {str(steps or '-'):>6} {str(sh or '-'):>5}")
    # print()


# ============================================================
# 辅助函数
# ============================================================
def get_int_input(prompt, min_val=None, max_val=None):
    """获取整数输入，支持跳过"""
    while True:
        val = input(prompt).strip()
        if not val:
            return None
        try:
            num = int(val)
            if min_val is not None and num < min_val:
                # print(f"    最小值: {min_val}")
                continue
            if max_val is not None and num > max_val:
                # print(f"    最大值: {max_val}")
                continue
            return num
        except ValueError:
            # print("    请输入有效数字")


def get_float_input(prompt, min_val=None, max_val=None):
    """获取浮点数输入，支持跳过"""
    while True:
        val = input(prompt).strip()
        if not val:
            return None
        try:
            num = float(val)
            if min_val is not None and num < min_val:
                # print(f"    最小值: {min_val}")
                continue
            if max_val is not None and num > max_val:
                # print(f"    最大值: {max_val}")
                continue
            return num
        except ValueError:
            # print("    请输入有效数字")


# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    init_db()

    if "--weekly" in sys.argv:
        generate_weekly_report()
    elif "--history" in sys.argv:
        days = 7
        for i, arg in enumerate(sys.argv):
            if arg == "--history" and i + 1 < len(sys.argv):
                try:
                    days = int(sys.argv[i + 1])
                except ValueError:
                    pass
        show_history(days)
    else:
        daily_check()

    # print("💚 健康管理，贵在坚持。祝您身体健康！")

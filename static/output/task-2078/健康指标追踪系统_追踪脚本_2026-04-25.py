#!/usr/bin/env python3
import csv
import sys
from pathlib import Path
from statistics import mean

FIELDS = [
    'date','sleep_hours','sleep_quality','resting_hr','weight_kg','exercise_minutes','steps',
    'energy_am','energy_pm','mood','stress','focus_hours','caffeine_cups','alcohol','bp_sys','bp_dia','notes'
]

NUMERIC_FIELDS = [
    'sleep_hours','sleep_quality','resting_hr','weight_kg','exercise_minutes','steps',
    'energy_am','energy_pm','mood','stress','focus_hours','caffeine_cups','alcohol','bp_sys','bp_dia'
]

def to_float(v):
    if v is None:
        return None
    v = str(v).strip()
    if v == '':
        return None
    try:
        return float(v)
    except ValueError:
        return None

def load_rows(path):
    rows = []
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed = {k: row.get(k, '') for k in FIELDS}
            for k in NUMERIC_FIELDS:
                parsed[k] = to_float(parsed.get(k))
            rows.append(parsed)
    return rows

def avg(rows, field):
    vals = [r[field] for r in rows if r.get(field) is not None]
    return round(mean(vals), 2) if vals else None

def count_if(rows, fn):
    return sum(1 for r in rows if fn(r))

def fmt(v):
    return '-' if v is None else str(v)

def analyze(rows):
    if not rows:
        return '无数据，请先填写 CSV。'

    recent = rows[-7:]
    sleep_avg = avg(recent, 'sleep_hours')
    sleep_quality_avg = avg(recent, 'sleep_quality')
    hr_avg = avg(recent, 'resting_hr')
    weight_avg = avg(recent, 'weight_kg')
    ex_total = sum(r['exercise_minutes'] or 0 for r in recent)
    focus_total = round(sum(r['focus_hours'] or 0 for r in recent), 2)
    energy_am_avg = avg(recent, 'energy_am')
    energy_pm_avg = avg(recent, 'energy_pm')
    stress_avg = avg(recent, 'stress')
    low_sleep_days = count_if(recent, lambda r: (r.get('sleep_hours') or 0) < 6.5)
    high_stress_days = count_if(recent, lambda r: (r.get('stress') or 0) >= 4)
    low_energy_days = count_if(recent, lambda r: (r.get('energy_am') or 5) <= 2 or (r.get('energy_pm') or 5) <= 2)

    alerts = []
    if sleep_avg is not None and sleep_avg < 6.5:
        alerts.append('最近7天平均睡眠不足，建议优先修复作息。')
    if low_sleep_days >= 3:
        alerts.append('最近7天中至少3天睡眠不足。')
    if high_stress_days >= 4:
        alerts.append('最近7天高压天数较多，建议降低事务堆叠。')
    if energy_am_avg is not None and energy_pm_avg is not None and (energy_am_avg + energy_pm_avg) / 2 < 2.8:
        alerts.append('最近整体精力偏低，应减少高负荷安排。')
    if ex_total < 90:
        alerts.append('最近7天运动总量不足90分钟，建议补足基础活动。')

    lines = []
    lines.append('=== 健康指标周分析 ===')
    lines.append(f'记录天数（最近7天窗口）: {len(recent)}')
    lines.append(f'平均睡眠时长: {fmt(sleep_avg)} 小时')
    lines.append(f'平均睡眠质量: {fmt(sleep_quality_avg)} / 5')
    lines.append(f'平均静息心率: {fmt(hr_avg)} bpm')
    lines.append(f'平均体重: {fmt(weight_avg)} kg')
    lines.append(f'每周总运动时长: {round(ex_total, 2)} 分钟')
    lines.append(f'上午平均精力: {fmt(energy_am_avg)} / 5')
    lines.append(f'下午平均精力: {fmt(energy_pm_avg)} / 5')
    lines.append(f'平均压力: {fmt(stress_avg)} / 5')
    lines.append(f'总专注时长: {focus_total} 小时')
    lines.append(f'睡眠不足天数: {low_sleep_days}')
    lines.append(f'高压天数: {high_stress_days}')
    lines.append(f'低精力天数: {low_energy_days}')
    lines.append('')
    lines.append('=== 异常提醒 ===')
    if alerts:
        for a in alerts:
            lines.append(f'- {a}')
    else:
        lines.append('- 本周无明显异常，继续保持。')

    lines.append('')
    lines.append('=== 建议动作 ===')
    if sleep_avg is not None and sleep_avg < 6.5:
        lines.append('- 下周优先把晚间收工时间提前30-60分钟。')
    if ex_total < 90:
        lines.append('- 安排3次20-30分钟快走或轻度有氧。')
    if high_stress_days >= 4:
        lines.append('- 将会议和事务按必须/可延期/可委派重新排序。')
    if not alerts:
        lines.append('- 保持当前节奏，每周持续观察趋势即可。')

    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        # print('用法: python3 health_tracker.py <csv文件路径>')
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.exists():
        # print(f'文件不存在: {path}')
        sys.exit(1)
    rows = load_rows(path)
    # print(analyze(rows))

if __name__ == '__main__':
    main()

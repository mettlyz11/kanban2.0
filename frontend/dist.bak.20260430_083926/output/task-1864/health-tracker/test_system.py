#!/usr/bin/env python3
"""系统测试脚本"""
from datetime import datetime
import sys

# 测试健康评分
from health_score import HealthScoreCalculator

import os
config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
calc = HealthScoreCalculator(config_path)

test_metrics = {
    'date': datetime.now().date().isoformat(),
    'steps': 12500,
    'active_calories': 520,
    'resting_heart_rate': 62,
    'avg_heart_rate': 70,
    'max_heart_rate': 145,
    'sleep_hours': 7.5,
    'sleep_deep_hours': 1.8,
    'stand_hours': 11,
}

scores = calc.calculate_daily_score(test_metrics)
print(f"总分: {scores['total']} ({scores['grade']})")
print(f"运动: {scores['activity']}, 睡眠: {scores['sleep']}")
print(f"心率: {scores['heart_rate']}, 精力: {scores['energy']}")

report = calc.generate_daily_report(test_metrics, scores)
print(f"\n{report}")
print("\n✅ 系统测试通过")

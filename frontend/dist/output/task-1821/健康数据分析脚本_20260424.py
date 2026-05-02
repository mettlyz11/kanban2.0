#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可穿戴设备健康数据分析脚本
功能：睡眠质量评分、运动效果评估、综合健康指数计算
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['PingFang SC', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False


class SleepScorer:
    """睡眠质量评分模型"""
    
    def __init__(self, age: int = 35):
        self.age = age
        self._set_sleep_recommendations()
    
    def _set_sleep_recommendations(self):
        """根据年龄设置推荐睡眠时间"""
        if self.age < 26:
            self.sleep_min, self.sleep_max = 7, 9
        elif self.age < 65:
            self.sleep_min, self.sleep_max = 7, 9
        else:
            self.sleep_min, self.sleep_max = 7, 8
        self.optimal_sleep = (self.sleep_min + self.sleep_max) / 2
    
    def calculate_duration_score(self, sleep_hours: float) -> float:
        """计算睡眠时间充足度得分"""
        deviation = abs(sleep_hours - self.optimal_sleep)
        if deviation <= 0.5:
            score = 100
        elif deviation <= 1:
            score = 90
        elif deviation <= 1.5:
            score = 75
        elif deviation <= 2:
            score = 60
        else:
            score = max(0, 60 - (deviation - 2) * 20)
        return score * 0.30
    
    def calculate_structure_score(self, stages: Dict[str, float]) -> float:
        """计算睡眠结构得分"""
        total = sum(stages.values())
        if total == 0:
            return 0
        
        scores = []
        
        # 深睡评分 (理想: 15-25%)
        deep_ratio = stages.get('deep', 0) / total
        if 0.15 <= deep_ratio <= 0.25:
            scores.append(100 * 0.40)
        else:
            deviation = abs(deep_ratio - 0.20)
            scores.append(max(0, 100 - deviation * 400) * 0.40)
        
        # REM睡眠评分 (理想: 20-25%)
        rem_ratio = stages.get('rem', 0) / total
        if 0.20 <= rem_ratio <= 0.25:
            scores.append(100 * 0.30)
        else:
            deviation = abs(rem_ratio - 0.225)
            scores.append(max(0, 100 - deviation * 400) * 0.30)
        
        # 浅睡评分 (理想: 45-55%)
        light_ratio = stages.get('light', 0) / total
        if 0.45 <= light_ratio <= 0.55:
            scores.append(100 * 0.20)
        else:
            deviation = abs(light_ratio - 0.50)
            scores.append(max(0, 100 - deviation * 250) * 0.20)
        
        # 清醒时间评分 (理想: <5%)
        awake_ratio = stages.get('awake', 0) / total
        if awake_ratio <= 0.05:
            scores.append(100 * 0.10)
        else:
            scores.append(max(0, 100 - (awake_ratio - 0.05) * 500) * 0.10)
        
        return sum(scores) * 0.25
    
    def calculate_continuity_score(self, awakenings: int, 
                                    total_minutes: float, 
                                    awake_minutes: float) -> float:
        """计算睡眠连续性得分"""
        # 夜间醒来次数评分
        awakening_score = max(0, 100 - awakenings * 15)
        
        # 睡眠效率评分
        sleep_efficiency = (total_minutes - awake_minutes) / total_minutes if total_minutes > 0 else 0
        efficiency_score = min(100, sleep_efficiency * 100)
        
        return (awakening_score * 0.5 + efficiency_score * 0.5) * 0.20
    
    def calculate_regularity_score(self, bedtimes: List[datetime], 
                                    wakeup_times: List[datetime]) -> float:
        """计算睡眠规律性得分"""
        if len(bedtimes) < 3:
            return 15  # 数据不足时给中等分数
        
        # 计算入睡时间标准差（分钟）
        bedtime_minutes = [t.hour * 60 + t.minute for t in bedtimes]
        bedtime_std = np.std(bedtime_minutes)
        bedtime_score = max(0, 100 - bedtime_std * 1.5)
        
        # 计算起床时间标准差
        wakeup_minutes = [t.hour * 60 + t.minute for t in wakeup_times]
        wakeup_std = np.std(wakeup_minutes)
        wakeup_score = max(0, 100 - wakeup_std * 1.5)
        
        return (bedtime_score + wakeup_score) / 2 * 0.15
    
    def calculate_recovery_score(self, resting_hr: float, 
                                  baseline_hr: float, 
                                  hrv: float) -> float:
        """计算恢复指标得分"""
        # 静息心率恢复评分
        hr_recovery = max(0, 100 - abs(resting_hr - baseline_hr) * 3)
        
        # HRV评分 (假设正常范围30-80ms)
        hrv_score = min(100, hrv / 0.8)
        
        return (hr_recovery + hrv_score) / 2 * 0.10
    
    def calculate_total_sleep_score(self, sleep_data: Dict) -> Tuple[float, Dict]:
        """计算综合睡眠得分"""
        sleep_hours = sleep_data['total_minutes'] / 60
        duration_score = self.calculate_duration_score(sleep_hours)
        
        structure_score = self.calculate_structure_score(sleep_data['stages'])
        
        continuity_score = self.calculate_continuity_score(
            sleep_data['awakenings'],
            sleep_data['total_minutes'],
            sleep_data['stages'].get('awake', 0)
        )
        
        regularity_score = self.calculate_regularity_score(
            sleep_data.get('recent_bedtimes', []),
            sleep_data.get('recent_wakeup_times', [])
        )
        
        recovery_score = self.calculate_recovery_score(
            sleep_data.get('resting_hr', 65),
            sleep_data.get('baseline_hr', 65),
            sleep_data.get('hrv', 50)
        )
        
        total = duration_score + structure_score + continuity_score + \
                regularity_score + recovery_score
        
        breakdown = {
            'duration': round(duration_score / 0.30, 1),
            'structure': round(structure_score / 0.25, 1),
            'continuity': round(continuity_score / 0.20, 1),
            'regularity': round(regularity_score / 0.15, 1),
            'recovery': round(recovery_score / 0.10, 1),
            'total': round(total, 1)
        }
        
        return round(total, 1), breakdown


class ActivityScorer:
    """运动效果评估模型"""
    
    def __init__(self, age: int = 35, gender: str = 'male'):
        self.age = age
        self.gender = gender
        self.max_hr = 220 - age
        self.resting_hr = 60  # 假设基线静息心率
    
    def calculate_volume_score(self, moderate_minutes: float, 
                                vigorous_minutes: float, 
                                period_days: int = 7) -> float:
        """计算运动量达标得分"""
        equivalent_minutes = moderate_minutes + vigorous_minutes * 2
        target = 150 * (period_days / 7)
        
        if equivalent_minutes >= target:
            score = 100
        else:
            score = (equivalent_minutes / target) * 80
        
        return score * 0.35
    
    def calculate_intensity_score(self, hr_zones: List[float]) -> float:
        """计算运动强度分布得分"""
        if sum(hr_zones) == 0:
            return 0
        
        ideal = [0.20, 0.40, 0.25, 0.10, 0.05]
        actual = np.array(hr_zones) / sum(hr_zones)
        
        # 计算分布相似度
        similarity = 0
        for i in range(5):
            similarity += min(actual[i], ideal[i])
        
        return similarity * 100 * 0.25
    
    def calculate_diversity_score(self, activity_types: List[str]) -> float:
        """计算运动多样性得分"""
        type_values = {
            'walking': 0.8,
            'running': 1.0,
            'cycling': 1.0,
            'swimming': 1.1,
            'strength': 1.2,
            'yoga': 0.8,
            'hiit': 1.1,
            'basketball': 1.0,
            'tennis': 1.0,
            'other': 0.7
        }
        
        total_value = sum(type_values.get(t, 0.7) for t in set(activity_types))
        score = min(100, total_value * 20)
        
        return score * 0.20
    
    def calculate_balance_score(self, activity_days: int, 
                                 rest_days: int,
                                 hr_recovery: float = 80) -> float:
        """计算恢复与平衡得分"""
        # 运动天数合理性 (每周3-5天最佳)
        optimal_days = 4.5
        day_deviation = abs(activity_days - optimal_days)
        day_score = max(0, 100 - day_deviation * 20)
        
        return (day_score * 0.5 + hr_recovery * 0.5) * 0.20
    
    def calculate_trimp(self, avg_hr: float, duration_minutes: float) -> float:
        """计算训练负荷TRIMP"""
        reserve_hr = self.max_hr - self.resting_hr
        hr_ratio = (avg_hr - self.resting_hr) / reserve_hr if reserve_hr > 0 else 0
        
        k = 1.92 if self.gender == 'male' else 1.67
        trimp = duration_minutes * hr_ratio * 0.64 * np.exp(k * hr_ratio)
        
        return trimp
    
    def calculate_total_activity_score(self, activity_data: Dict) -> Tuple[float, Dict]:
        """计算综合运动得分"""
        volume_score = self.calculate_volume_score(
            activity_data.get('moderate_minutes', 0),
            activity_data.get('vigorous_minutes', 0),
            activity_data.get('period_days', 7)
        )
        
        intensity_score = self.calculate_intensity_score(
            activity_data.get('hr_zones', [0, 0, 0, 0, 0])
        )
        
        diversity_score = self.calculate_diversity_score(
            activity_data.get('activity_types', [])
        )
        
        balance_score = self.calculate_balance_score(
            activity_data.get('activity_days', 3),
            activity_data.get('rest_days', 4),
            activity_data.get('hr_recovery', 80)
        )
        
        total = volume_score + intensity_score + diversity_score + balance_score
        
        breakdown = {
            'volume': round(volume_score / 0.35, 1),
            'intensity': round(intensity_score / 0.25, 1),
            'diversity': round(diversity_score / 0.20, 1),
            'balance': round(balance_score / 0.20, 1),
            'total': round(total, 1)
        }
        
        return round(total, 1), breakdown


class StressCalculator:
    """压力指数计算模型"""
    
    def __init__(self, age: int = 35):
        self.age = age
    
    def calculate_stress_index(self, hrv_rmssd: float, 
                                hrv_sdnn: float, 
                                resting_hr: float) -> float:
        """计算压力指数 0-100"""
        # HRV RMSSD评分
        rmssd_norm = min(100, hrv_rmssd / 50 * 100)
        
        # HRV SDNN评分
        sdnn_norm = min(100, hrv_sdnn / 80 * 100)
        
        # 静息心率评分
        optimal_hr = 60 + self.age * 0.2
        hr_score = max(0, 100 - abs(resting_hr - optimal_hr) * 2)
        
        # 综合压力指数（反向）
        stress_raw = 100 - (rmssd_norm * 0.4 + sdnn_norm * 0.3 + hr_score * 0.3)
        
        return min(100, max(0, round(stress_raw, 1)))
    
    def get_stress_level(self, stress_index: float) -> str:
        """获取压力等级描述"""
        if stress_index <= 25:
            return "放松"
        elif stress_index <= 50:
            return "轻度压力"
        elif stress_index <= 75:
            return "中度压力"
        else:
            return "高度压力"


def generate_sample_data() -> Dict:
    """生成示例数据用于测试"""
    return {
        'sleep': {
            'total_minutes': 480,  # 8小时
            'stages': {
                'deep': 96,      # 20%
                'rem': 108,      # 22.5%
                'light': 240,    # 50%
                'awake': 36      # 7.5%
            },
            'awakenings': 2,
            'resting_hr': 58,
            'baseline_hr': 62,
            'hrv': 55,
            'recent_bedtimes': [
                datetime(2026, 4, d, 23, 15) for d in range(18, 25)
            ],
            'recent_wakeup_times': [
                datetime(2026, 4, d+1, 7, 15) for d in range(18, 25)
            ]
        },
        'activity': {
            'moderate_minutes': 120,
            'vigorous_minutes': 45,
            'period_days': 7,
            'hr_zones': [60, 120, 75, 30, 15],
            'activity_types': ['running', 'strength', 'walking', 'yoga'],
            'activity_days': 5,
            'rest_days': 2,
            'hr_recovery': 85
        },
        'stress': {
            'hrv_rmssd': 45,
            'hrv_sdnn': 70,
            'resting_hr': 60
        }
    }


def main():
    print("=" * 50)
    print("可穿戴设备健康数据分析系统")
    print("=" * 50)
    
    # 初始化分析器
    sleep_scorer = SleepScorer(age=35)
    activity_scorer = ActivityScorer(age=35, gender='male')
    stress_calc = StressCalculator(age=35)
    
    # 生成示例数据
    sample_data = generate_sample_data()
    
    # 睡眠分析
    print("\n【睡眠质量分析】")
    sleep_score, sleep_breakdown = sleep_scorer.calculate_total_sleep_score(sample_data['sleep'])
    print(f"睡眠总评分: {sleep_score} 分")
    print(f"  - 睡眠时间: {sleep_breakdown['duration']} 分")
    print(f"  - 睡眠结构: {sleep_breakdown['structure']} 分")
    print(f"  - 睡眠连续性: {sleep_breakdown['continuity']} 分")
    print(f"  - 睡眠规律性: {sleep_breakdown['regularity']} 分")
    print(f"  - 身体恢复: {sleep_breakdown['recovery']} 分")
    
    # 运动分析
    print("\n【运动效果分析】")
    activity_score, activity_breakdown = activity_scorer.calculate_total_activity_score(sample_data['activity'])
    print(f"运动总评分: {activity_score} 分")
    print(f"  - 运动量达标: {activity_breakdown['volume']} 分")
    print(f"  - 强度分布合理性: {activity_breakdown['intensity']} 分")
    print(f"  - 运动多样性: {activity_breakdown['diversity']} 分")
    print(f"  - 恢复平衡: {activity_breakdown['balance']} 分")
    
    # 压力分析
    print("\n【压力指数分析】")
    stress_index = stress_calc.calculate_stress_index(**sample_data['stress'])
    stress_level = stress_calc.get_stress_level(stress_index)
    print(f"压力指数: {stress_index} ({stress_level})")
    
    # 综合健康指数
    print("\n【综合健康活力指数】")
    body_score = 85  # 假设有身体组成数据
    vitality = (sleep_score * 0.30 + 
                 activity_score * 0.30 + 
                 (100 - stress_index) * 0.20 + 
                 body_score * 0.20)
    print(f"综合活力指数: {round(vitality, 1)}")
    
    # 生成JSON报告
    report = {
        'generated_at': datetime.now().isoformat(),
        'sleep': {
            'score': sleep_score,
            'breakdown': sleep_breakdown
        },
        'activity': {
            'score': activity_score,
            'breakdown': activity_breakdown
        },
        'stress': {
            'index': stress_index,
            'level': stress_level
        },
        'vitality': round(vitality, 1),
        'recommendations': []
    }
    
    # 生成建议
    recommendations = []
    if sleep_score < 70:
        recommendations.append("建议调整作息，保证充足且规律的睡眠时间")
    if activity_score < 70:
        recommendations.append("建议增加运动量，注意运动类型多样化")
    if stress_index > 50:
        recommendations.append("压力较大，建议进行放松活动，保证充足休息")
    
    report['recommendations'] = recommendations
    
    print("\n【健康建议】")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")
    
    if not recommendations:
        print("各项指标良好，继续保持当前生活方式！")
    
    # 保存报告
    with open('health_analysis_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 分析报告已保存到 health_analysis_report.json")
    
    return report


if __name__ == '__main__':
    main()

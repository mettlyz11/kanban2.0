#!/usr/bin/env python3
"""
健康评分算法模块
评分维度：运动 30% + 睡眠 30% + 心率 20% + 精力 20%
"""

import yaml
from datetime import datetime, timedelta
import numpy as np

class HealthScoreCalculator:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.weights = self.config['health']['weights']
        self.targets = self.config['health']['targets']
        self.alerts = self.config['health']['alerts']
    
    def calculate_daily_score(self, metrics):
        """
        计算每日健康评分 (0-100)
        
        参数:
            metrics: dict 包含 steps, active_calories, sleep_hours, 
                     resting_heart_rate, avg_heart_rate 等
        
        返回:
            dict: 包含总分和各维度得分
        """
        scores = {}
        
        # 1. 运动评分 (30%) - 基于步数和活跃卡路里
        activity_score = self._calculate_activity_score(metrics)
        scores['activity'] = round(activity_score, 1)
        
        # 2. 睡眠评分 (30%) - 基于睡眠时长和质量
        sleep_score = self._calculate_sleep_score(metrics)
        scores['sleep'] = round(sleep_score, 1)
        
        # 3. 心率评分 (20%) - 基于静息心率稳定性
        hr_score = self._calculate_heart_rate_score(metrics)
        scores['heart_rate'] = round(hr_score, 1)
        
        # 4. 精力评分 (20%) - 基于心率变异性 proxy（用最大/平均心率比估算）
        energy_score = self._calculate_energy_score(metrics)
        scores['energy'] = round(energy_score, 1)
        
        # 加权总分
        total_score = (
            scores['activity'] * self.weights['activity'] +
            scores['sleep'] * self.weights['sleep'] +
            scores['heart_rate'] * self.weights['heart_rate'] +
            scores['energy'] * self.weights['energy']
        )
        
        scores['total'] = round(total_score, 1)
        scores['grade'] = self._score_to_grade(total_score)
        scores['alerts'] = self._check_alerts(metrics)
        
        return scores
    
    def _calculate_activity_score(self, metrics):
        """运动评分：步数目标达成率 + 活跃卡路里"""
        steps_ratio = min(metrics.get('steps', 0) / self.targets['steps'], 1.5)
        cal_ratio = min(metrics.get('active_calories', 0) / self.targets['active_calories'], 1.5)
        
        # 步数权重 60%，卡路里权重 40%
        score = (steps_ratio * 0.6 + cal_ratio * 0.4) * 100
        return min(score, 100)
    
    def _calculate_sleep_score(self, metrics):
        """睡眠评分：基于睡眠时长和结构"""
        sleep_hours = metrics.get('sleep_hours', 0)
        target = self.targets['sleep_hours']
        
        if sleep_hours >= target:
            base_score = 100
        elif sleep_hours >= 6:
            # 6-7.5小时之间线性递减
            base_score = 70 + (sleep_hours - 6) / (target - 6) * 30
        elif sleep_hours >= 5:
            base_score = 50 + (sleep_hours - 5) / (6 - 5) * 20
        else:
            base_score = max(0, sleep_hours / 5 * 50)
        
        # 深度睡眠比例加成
        deep_ratio = metrics.get('sleep_deep_hours', 0) / max(sleep_hours, 1)
        if deep_ratio >= 0.2:
            bonus = 5
        elif deep_ratio >= 0.15:
            bonus = 2
        else:
            bonus = 0
        
        return min(base_score + bonus, 100)
    
    def _calculate_heart_rate_score(self, metrics):
        """心率评分：静息心率越接近目标值越好"""
        rhr = metrics.get('resting_heart_rate', 70)
        target = self.targets['resting_heart_rate']
        
        # 最佳区间 55-75
        if 55 <= rhr <= 75:
            score = 100 - abs(rhr - target) * 2
        elif 50 <= rhr < 55 or 75 < rhr <= 85:
            score = 85 - abs(rhr - target) * 1.5
        else:
            score = max(0, 70 - abs(rhr - target))
        
        return min(max(score, 0), 100)
    
    def _calculate_energy_score(self, metrics):
        """精力评分：基于心率恢复能力和日间活跃度"""
        avg_hr = metrics.get('avg_heart_rate', 75)
        max_hr = metrics.get('max_heart_rate', 140)
        stand_hours = metrics.get('stand_hours', 8)
        
        # 心率储备（max/avg 比例越大说明恢复越好）
        hr_reserve = min(max_hr / max(avg_hr, 1), 2.0)
        hr_score = min((hr_reserve - 1.0) / 0.5 * 50 + 50, 100)
        
        # 站立时间目标 12 小时
        stand_score = min(stand_hours / 12 * 100, 100)
        
        return hr_score * 0.6 + stand_score * 0.4
    
    def _score_to_grade(self, score):
        """分数转等级"""
        if score >= 90: return 'A+'
        if score >= 85: return 'A'
        if score >= 80: return 'A-'
        if score >= 75: return 'B+'
        if score >= 70: return 'B'
        if score >= 65: return 'B-'
        if score >= 60: return 'C+'
        if score >= 55: return 'C'
        return 'D'
    
    def _check_alerts(self, metrics):
        """检查异常指标"""
        alerts = []
        
        rhr = metrics.get('resting_heart_rate', 70)
        if rhr > self.alerts['resting_hr_high']:
            alerts.append({
                'type': 'warning',
                'metric': 'resting_heart_rate',
                'message': f'静息心率偏高: {rhr} bpm（正常 <{self.alerts["resting_hr_high"]}）',
                'severity': 'medium'
            })
        elif rhr < self.alerts['resting_hr_low']:
            alerts.append({
                'type': 'warning',
                'metric': 'resting_heart_rate',
                'message': f'静息心率偏低: {rhr} bpm（正常 >{self.alerts["resting_hr_low"]}）',
                'severity': 'low'
            })
        
        sleep = metrics.get('sleep_hours', 0)
        if sleep < self.alerts['sleep_hours_low']:
            alerts.append({
                'type': 'warning',
                'metric': 'sleep',
                'message': f'睡眠不足: {sleep} 小时（建议 ≥{self.alerts["sleep_hours_low"]}）',
                'severity': 'high'
            })
        
        return alerts
    
    def calculate_trend(self, historical_scores):
        """计算趋势变化"""
        if len(historical_scores) < 7:
            return {'trend': 'insufficient_data', 'change': 0}
        
        recent = np.mean([s['total'] for s in historical_scores[-7:]])
        previous = np.mean([s['total'] for s in historical_scores[-14:-7]])
        change = recent - previous
        
        if change > 3:
            trend = 'improving'
        elif change < -3:
            trend = 'declining'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'change': round(change, 1),
            'recent_avg': round(recent, 1),
            'previous_avg': round(previous, 1)
        }
    
    def generate_daily_report(self, metrics, scores, trend=None):
        """生成每日健康简报"""
        lines = [
            f"📊 每日健康报告 ({metrics['date']})",
            f"",
            f"🏆 综合评分: {scores['total']} 分 ({scores['grade']})",
            f"",
            f"📈 各维度得分:",
            f"  • 运动 ({self.weights['activity']*100:.0f}%): {scores['activity']}",
            f"  • 睡眠 ({self.weights['sleep']*100:.0f}%): {scores['sleep']}",
            f"  • 心率 ({self.weights['heart_rate']*100:.0f}%): {scores['heart_rate']}",
            f"  • 精力 ({self.weights['energy']*100:.0f}%): {scores['energy']}",
            f"",
            f"📋 关键指标:",
            f"  • 步数: {metrics.get('steps', 0):,} / {self.targets['steps']:,}",
            f"  • 睡眠: {metrics.get('sleep_hours', 0)} 小时",
            f"  • 静息心率: {metrics.get('resting_heart_rate', '--')} bpm",
            f"  • 消耗: {metrics.get('active_calories', 0)} kcal",
        ]
        
        if trend:
            lines.extend([
                f"",
                f"📉 7日趋势: {trend['trend']} (变化: {trend['change']:+.1f})",
            ])
        
        if scores['alerts']:
            lines.extend([f"", f"⚠️ 异常提醒:"])
            for alert in scores['alerts']:
                icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(alert['severity'], '⚪')
                lines.append(f"  {icon} {alert['message']}")
        
        return "\n".join(lines)


if __name__ == "__main__":
    calc = HealthScoreCalculator()
    
    # 测试数据
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
    print(f"\n=== 健康评分测试 ===")
    print(f"总分: {scores['total']} ({scores['grade']})")
    print(f"运动: {scores['activity']}, 睡眠: {scores['sleep']}")
    print(f"心率: {scores['heart_rate']}, 精力: {scores['energy']}")
    
    report = calc.generate_daily_report(test_metrics, scores)
    print(f"\n{report}")

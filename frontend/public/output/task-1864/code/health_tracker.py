#!/usr/bin/env python3
"""
Apple Watch Health Data Quantification System
健康数据量化系统 - 主程序
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from dataclasses import dataclass
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class HealthMetrics:
    """健康数据指标"""
    date: str
    steps: int = 0
    active_energy: float = 0.0
    exercise_minutes: int = 0
    heart_rate_resting: float = 0.0
    heart_rate_avg: float = 0.0
    heart_rate_variability: float = 0.0
    sleep_total: float = 0.0
    sleep_deep: float = 0.0
    sleep_core: float = 0.0
    sleep_rem: float = 0.0
    sleep_awake: float = 0.0
    energy_basal: float = 0.0
    energy_active: float = 0.0

class HealthScorer:
    """健康评分算法"""
    
    @staticmethod
    def calculate_steps_score(steps: int) -> float:
        """步数评分 (0-100) - 目标10000步"""
        if steps >= 12000:
            return 100.0
        elif steps >= 8000:
            return 70 + (steps - 8000) / 4000 * 30
        elif steps >= 5000:
            return 40 + (steps - 5000) / 3000 * 30
        elif steps >= 2000:
            return 10 + (steps - 2000) / 3000 * 30
        else:
            return max(0, steps / 2000 * 10)
    
    @staticmethod
    def calculate_sleep_score(sleep_total: float, sleep_deep: float = 0) -> float:
        """睡眠评分 (0-100) - 目标7-9小时"""
        # 总睡眠时长评分
        if 7 <= sleep_total <= 9:
            duration_score = 100
        elif 6 <= sleep_total < 7 or 9 < sleep_total <= 10:
            duration_score = 80
        elif 5 <= sleep_total < 6 or 10 < sleep_total <= 11:
            duration_score = 60
        elif 4 <= sleep_total < 5 or 11 < sleep_total <= 12:
            duration_score = 40
        else:
            duration_score = 20
        
        # 深度睡眠占比评分 (目标20-30%)
        if sleep_total > 0:
            deep_ratio = sleep_deep / sleep_total
            if 0.2 <= deep_ratio <= 0.3:
                deep_score = 100
            elif 0.15 <= deep_ratio < 0.2 or 0.3 < deep_ratio <= 0.35:
                deep_score = 80
            elif 0.1 <= deep_ratio < 0.15 or 0.35 < deep_ratio <= 0.4:
                deep_score = 60
            else:
                deep_score = 40
        else:
            deep_score = 50
        
        return duration_score * 0.7 + deep_score * 0.3
    
    @staticmethod
    def calculate_heart_rate_score(resting_hr: float, avg_hr: float = 0) -> float:
        """心率评分 (0-100) - 静息心率目标55-65"""
        if resting_hr <= 0:
            return 50
        
        # 静息心率评分
        if 55 <= resting_hr <= 65:
            resting_score = 100
        elif 50 <= resting_hr < 55 or 65 < resting_hr <= 75:
            resting_score = 85
        elif 45 <= resting_hr < 50 or 75 < resting_hr <= 85:
            resting_score = 70
        elif resting_hr < 45 or 85 < resting_hr <= 95:
            resting_score = 50
        else:
            resting_score = 30
        
        return resting_score
    
    @staticmethod
    def calculate_energy_score(exercise_minutes: int, active_energy: float) -> float:
        """精力/活动评分 (0-100)"""
        # 运动时长评分 (目标30分钟+)
        if exercise_minutes >= 45:
            exercise_score = 100
        elif exercise_minutes >= 30:
            exercise_score = 85
        elif exercise_minutes >= 20:
            exercise_score = 70
        elif exercise_minutes >= 10:
            exercise_score = 50
        else:
            exercise_score = 30
        
        # 活动能量评分 (目标300kcal+)
        if active_energy >= 500:
            energy_score = 100
        elif active_energy >= 300:
            energy_score = 80
        elif active_energy >= 200:
            energy_score = 65
        elif active_energy >= 100:
            energy_score = 50
        else:
            energy_score = 35
        
        return exercise_score * 0.6 + energy_score * 0.4
    
    @staticmethod
    def calculate_total_health_score(metrics: HealthMetrics) -> Dict[str, float]:
        """计算综合健康评分"""
        exercise_score = HealthScorer.calculate_energy_score(
            metrics.exercise_minutes, metrics.active_energy
        )
        sleep_score = HealthScorer.calculate_sleep_score(
            metrics.sleep_total, metrics.sleep_deep
        )
        heart_score = HealthScorer.calculate_heart_rate_score(
            metrics.heart_rate_resting, metrics.heart_rate_avg
        )
        energy_score = HealthScorer.calculate_steps_score(metrics.steps)
        
        # 加权总分
        total_score = (
            exercise_score * 0.30 +
            sleep_score * 0.30 +
            heart_score * 0.20 +
            energy_score * 0.20
        )
        
        return {
            'total': round(total_score, 1),
            'exercise': round(exercise_score, 1),
            'sleep': round(sleep_score, 1),
            'heart': round(heart_score, 1),
            'energy': round(energy_score, 1)
        }

class AnomalyDetector:
    """异常检测模块"""
    
    def __init__(self, baseline_window: int = 7):
        self.baseline_window = baseline_window
    
    def detect_anomalies(self, history: List[Dict]) -> List[Dict]:
        """检测健康异常"""
        anomalies = []
        
        if len(history) < self.baseline_window:
            return anomalies
        
        df = pd.DataFrame(history)
        
        # 1. 静息心率持续升高检测
        recent_hr = df['heart_rate_resting'].tail(3).mean()
        baseline_hr = df['heart_rate_resting'].head(-3).tail(self.baseline_window).mean()
        if baseline_hr > 0 and recent_hr > baseline_hr * 1.15:
            anomalies.append({
                'type': 'heart_rate_elevation',
                'severity': 'warning',
                'message': f'静息心率异常升高: 近期{recent_hr:.1f} bpm vs 基线{baseline_hr:.1f} bpm',
                'recommendation': '建议监测身体疲劳度或炎症反应'
            })
        
        # 2. 睡眠质量下降检测
        recent_sleep = df['sleep_total'].tail(3).mean()
        baseline_sleep = df['sleep_total'].head(-3).tail(self.baseline_window).mean()
        if baseline_sleep > 0 and recent_sleep < baseline_sleep * 0.7:
            anomalies.append({
                'type': 'sleep_quality_decline',
                'severity': 'warning',
                'message': f'睡眠时长显著下降: 近期{recent_sleep:.1f}h vs 基线{baseline_sleep:.1f}h',
                'recommendation': '建议调整作息，避免熬夜'
            })
        
        # 3. 活动量骤降检测
        recent_steps = df['steps'].tail(3).mean()
        baseline_steps = df['steps'].head(-3).tail(self.baseline_window).mean()
        if baseline_steps > 0 and recent_steps < baseline_steps * 0.5:
            anomalies.append({
                'type': 'activity_drop',
                'severity': 'info',
                'message': f'活动量显著下降: 近期{recent_steps:.0f}步 vs 基线{baseline_steps:.0f}步',
                'recommendation': '建议增加轻度活动'
            })
        
        return anomalies

class TrendAnalyzer:
    """趋势分析模块"""
    
    def generate_weekly_report(self, data: List[Dict]) -> Dict:
        """生成周报告"""
        df = pd.DataFrame(data)
        
        return {
            'period': 'weekly',
            'start_date': df['date'].min(),
            'end_date': df['date'].max(),
            'avg_total_score': df['score_total'].mean(),
            'avg_steps': df['steps'].mean(),
            'avg_sleep': df['sleep_total'].mean(),
            'avg_heart_rate': df['heart_rate_resting'].mean(),
            'best_day': df.loc[df['score_total'].idxmax(), 'date'],
            'worst_day': df.loc[df['score_total'].idxmin(), 'date'],
            'trend': self._calculate_trend(df['score_total']),
            'key_insights': self._generate_insights(df)
        }
    
    def generate_monthly_report(self, data: List[Dict]) -> Dict:
        """生成月度报告"""
        df = pd.DataFrame(data)
        
        weekly_breakdown = []
        for i in range(0, len(df), 7):
            week_df = df.iloc[i:i+7]
            if len(week_df) >= 5:
                weekly_breakdown.append({
                    'week': i // 7 + 1,
                    'avg_score': week_df['score_total'].mean(),
                    'avg_steps': week_df['steps'].mean()
                })
        
        return {
            'period': 'monthly',
            'start_date': df['date'].min(),
            'end_date': df['date'].max(),
            'days_analyzed': len(df),
            'avg_total_score': round(df['score_total'].mean(), 1),
            'score_std': round(df['score_total'].std(), 1),
            'avg_steps': round(df['steps'].mean(), 0),
            'avg_sleep': round(df['sleep_total'].mean(), 1),
            'avg_heart_rate': round(df['heart_rate_resting'].mean(), 1),
            'score_distribution': {
                'excellent': len(df[df['score_total'] >= 85]),
                'good': len(df[(df['score_total'] >= 70) & (df['score_total'] < 85)]),
                'fair': len(df[(df['score_total'] >= 55) & (df['score_total'] < 70)]),
                'poor': len(df[df['score_total'] < 55])
            },
            'weekly_breakdown': weekly_breakdown,
            'key_insights': self._generate_insights(df),
            'recommendations': self._generate_recommendations(df)
        }
    
    def _calculate_trend(self, series: pd.Series) -> str:
        """计算趋势方向"""
        if len(series) < 7:
            return 'insufficient_data'
        
        first_half = series.head(len(series)//2).mean()
        second_half = series.tail(len(series)//2).mean()
        change = (second_half - first_half) / first_half
        
        if change > 0.05:
            return 'improving'
        elif change < -0.05:
            return 'declining'
        else:
            return 'stable'
    
    def _generate_insights(self, df: pd.DataFrame) -> List[str]:
        """生成关键洞察"""
        insights = []
        
        avg_score = df['score_total'].mean()
        if avg_score >= 80:
            insights.append(f"整体健康状态优秀，平均得分{avg_score:.1f}分")
        elif avg_score >= 65:
            insights.append(f"整体健康状态良好，平均得分{avg_score:.1f}分")
        else:
            insights.append(f"健康状态需要关注，平均得分{avg_score:.1f}分")
        
        if df['sleep_total'].mean() >= 7:
            insights.append("睡眠充足，继续保持")
        else:
            insights.append("睡眠时长不足，建议提前入睡时间")
        
        if df['steps'].mean() >= 8000:
            insights.append("活动量充足，每日步数达标")
        else:
            insights.append("活动量偏低，建议增加日常步行")
        
        return insights
    
    def _generate_recommendations(self, df: pd.DataFrame) -> List[str]:
        """生成建议"""
        recommendations = []
        
        if df['sleep_total'].mean() < 6.5:
            recommendations.append("🎯 优先目标：将每日睡眠时间提升至7小时以上，建议23:00前入睡")
        
        if df['steps'].mean() < 6000:
            recommendations.append("🚶 增加活动量：工作日利用午休散步，周末安排户外活动")
        
        if df['score_total'].std() > 15:
            recommendations.append("⚖️ 保持作息规律：健康得分波动较大，建议稳定日常作息")
        
        if df['heart_rate_resting'].mean() > 75:
            recommendations.append("❤️ 关注心血管健康：静息心率偏高，建议增加有氧运动")
        
        return recommendations

class DataExporter:
    """数据导出模块 - 模拟HealthKit数据导入"""
    
    @staticmethod
    def generate_sample_data(days: int = 30) -> List[HealthMetrics]:
        """生成示例健康数据"""
        data = []
        base_date = datetime.now() - timedelta(days=days)
        
        np.random.seed(42)
        
        for i in range(days):
            current_date = base_date + timedelta(days=i)
            date_str = current_date.strftime('%Y-%m-%d')
            
            # 模拟工作日/周末差异
            is_weekend = current_date.weekday() >= 5
            
            # 添加一些波动和趋势
            trend_factor = 1 + (i / days) * 0.1  # 轻微改善趋势
            noise = np.random.normal(1, 0.15)
            
            metrics = HealthMetrics(
                date=date_str,
                steps=int(np.random.normal(8000 if is_weekend else 10000, 2500) * trend_factor * noise),
                exercise_minutes=int(np.random.normal(35 if is_weekend else 45, 15) * trend_factor * noise),
                active_energy=float(np.random.normal(350, 100) * trend_factor * noise),
                heart_rate_resting=float(np.random.normal(62, 5) / trend_factor),
                heart_rate_avg=float(np.random.normal(75, 8) / trend_factor),
                heart_rate_variability=float(np.random.normal(45, 10) * trend_factor),
                sleep_total=float(np.random.normal(7.2 if is_weekend else 6.8, 1.0) * trend_factor),
                sleep_deep=float(np.random.normal(1.8, 0.5) * trend_factor),
                sleep_core=float(np.random.normal(3.5, 0.8) * trend_factor),
                sleep_rem=float(np.random.normal(1.5, 0.4) * trend_factor),
                sleep_awake=float(np.random.normal(0.5, 0.2)),
                energy_basal=float(np.random.normal(1800, 100)),
                energy_active=float(np.random.normal(500, 150) * trend_factor * noise)
            )
            
            # 确保数值合理
            metrics.steps = max(1000, metrics.steps)
            metrics.sleep_total = max(3, metrics.sleep_total)
            metrics.heart_rate_resting = max(45, min(95, metrics.heart_rate_resting))
            
            data.append(metrics)
        
        return data
    
    @staticmethod
    def export_to_json(data: List[Dict], filepath: str):
        """导出JSON格式"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def export_to_csv(data: List[Dict], filepath: str):
        """导出CSV格式"""
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')

def main():
    """主程序入口"""
    print("=" * 60)
    print("Apple Watch 健康数据量化系统 v1.0")
    print("=" * 60)
    
    # 1. 生成/导入数据
    print("\n[1/5] 导入健康数据...")
    exporter = DataExporter()
    raw_data = exporter.generate_sample_data(days=30)
    
    # 2. 计算健康评分
    print("[2/5] 计算健康评分...")
    scorer = HealthScorer()
    scored_data = []
    for metrics in raw_data:
        scores = scorer.calculate_total_health_score(metrics)
        scored_data.append({
            'date': metrics.date,
            'steps': metrics.steps,
            'exercise_minutes': metrics.exercise_minutes,
            'active_energy': metrics.active_energy,
            'heart_rate_resting': metrics.heart_rate_resting,
            'heart_rate_avg': metrics.heart_rate_avg,
            'sleep_total': metrics.sleep_total,
            'sleep_deep': metrics.sleep_deep,
            'score_total': scores['total'],
            'score_exercise': scores['exercise'],
            'score_sleep': scores['sleep'],
            'score_heart': scores['heart'],
            'score_energy': scores['energy']
        })
    
    # 3. 异常检测
    print("[3/5] 异常检测...")
    detector = AnomalyDetector()
    anomalies = detector.detect_anomalies(scored_data)
    print(f"  检测到 {len(anomalies)} 个异常预警")
    
    # 4. 趋势分析
    print("[4/5] 生成趋势报告...")
    analyzer = TrendAnalyzer()
    monthly_report = analyzer.generate_monthly_report(scored_data)
    
    # 5. 导出数据
    print("[5/5] 导出数据...")
    output_dir = Path('/Users/mettlyz/.openclaw/workspace/output/task-1864')
    exporter.export_to_json(scored_data, output_dir / 'data' / 'health_data.json')
    exporter.export_to_csv(scored_data, output_dir / 'data' / 'health_data.csv')
    exporter.export_to_json(monthly_report, output_dir / 'reports' / 'monthly_report.json')
    
    print("\n✅ 系统初始化完成！")
    print(f"📊 分析天数: {len(scored_data)} 天")
    print(f"🏆 平均健康评分: {monthly_report['avg_total_score']}")
    print(f"💡 建议数量: {len(monthly_report['recommendations'])} 条")
    
    return {
        'status': 'success',
        'data_points': len(scored_data),
        'anomalies': anomalies,
        'monthly_report': monthly_report
    }

if __name__ == '__main__':
    main()

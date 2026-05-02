#!/usr/bin/env python3
"""
Apple Health 数据导出与解析模块
支持真实 HealthKit XML 导出和模拟数据两种模式
"""

import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import yaml
import random

class HealthDataExporter:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.use_mock = self.config['apple_health']['use_mock']
        self.export_path = Path(self.config['apple_health']['export_path']).expanduser()
    
    def get_daily_summary(self, date=None):
        """获取指定日期的健康数据摘要"""
        if date is None:
            date = datetime.now().date()
        
        if self.use_mock:
            return self._generate_mock_data(date)
        else:
            return self._parse_health_export(date)
    
    def _generate_mock_data(self, date):
        """生成模拟健康数据（用于测试）"""
        random.seed(date.toordinal())
        
        # 模拟趋势：工作日运动量较高，周末波动
        weekday = date.weekday()
        base_steps = 8000 + (500 if weekday < 5 else -1000)
        base_sleep = 7.2 + (0.3 if weekday >= 5 else 0)
        
        return {
            'date': date.isoformat(),
            'steps': int(base_steps + random.gauss(0, 1500)),
            'distance_km': round((base_steps * 0.00075) + random.gauss(0, 0.3), 2),
            'active_calories': int(450 + random.gauss(0, 100)),
            'resting_heart_rate': int(65 + random.gauss(0, 4)),
            'avg_heart_rate': int(72 + random.gauss(0, 6)),
            'max_heart_rate': int(140 + random.gauss(0, 15)),
            'sleep_hours': round(max(4.5, base_sleep + random.gauss(0, 0.8)), 2),
            'sleep_deep_hours': round(max(1.0, base_sleep * 0.2 + random.gauss(0, 0.3)), 2),
            'sleep_rem_hours': round(max(0.5, base_sleep * 0.25 + random.gauss(0, 0.3)), 2),
            'stand_hours': int(max(4, 10 + random.gauss(0, 2))),
            'flights_climbed': int(max(0, 5 + random.gauss(0, 3))),
            'source': 'mock'
        }
    
    def _parse_health_export(self, date):
        """解析 Apple Health 导出 XML"""
        if not self.export_path.exists():
            raise FileNotFoundError(
                f"Health export not found: {self.export_path}\n"
                "请在 iPhone 上导出健康数据，或设置 use_mock: true"
            )
        
        tree = ET.parse(self.export_path)
        root = tree.getroot()
        
        date_str = date.isoformat()
        
        # 解析各类健康指标
        records = root.findall('.//Record')
        
        metrics = {
            'date': date_str,
            'steps': self._sum_records(records, 'HKQuantityTypeIdentifierStepCount', date),
            'distance_km': self._sum_records(records, 'HKQuantityTypeIdentifierDistanceWalkingRunning', date) / 1000,
            'active_calories': self._sum_records(records, 'HKQuantityTypeIdentifierActiveEnergyBurned', date),
            'resting_heart_rate': self._avg_records(records, 'HKQuantityTypeIdentifierRestingHeartRate', date),
            'avg_heart_rate': self._avg_records(records, 'HKQuantityTypeIdentifierHeartRate', date),
            'max_heart_rate': self._max_records(records, 'HKQuantityTypeIdentifierHeartRate', date),
            'sleep_hours': self._calculate_sleep(records, date),
            'stand_hours': self._count_records(records, 'HKCategoryTypeIdentifierAppleStandHour', date),
            'flights_climbed': self._sum_records(records, 'HKQuantityTypeIdentifierFlightsClimbed', date),
            'source': 'apple_health'
        }
        
        return metrics
    
    def _sum_records(self, records, record_type, date):
        total = 0
        for r in records:
            if r.get('type') == record_type:
                try:
                    value = float(r.get('value', 0))
                    total += value
                except (ValueError, TypeError):
                    continue
        return total
    
    def _avg_records(self, records, record_type, date):
        values = []
        for r in records:
            if r.get('type') == record_type:
                try:
                    values.append(float(r.get('value', 0)))
                except (ValueError, TypeError):
                    continue
        return sum(values) / len(values) if values else 0
    
    def _max_records(self, records, record_type, date):
        values = []
        for r in records:
            if r.get('type') == record_type:
                try:
                    values.append(float(r.get('value', 0)))
                except (ValueError, TypeError):
                    continue
        return max(values) if values else 0
    
    def _calculate_sleep(self, records, date):
        """计算睡眠时长（简化版）"""
        sleep_records = [r for r in records if 'SleepAnalysis' in r.get('type', '')]
        total_seconds = len(sleep_records) * 60  # 简化为每分钟一条记录
        return round(total_seconds / 3600, 2)
    
    def _count_records(self, records, record_type, date):
        return sum(1 for r in records if r.get('type') == record_type)
    
    def get_historical_data(self, days=30):
        """获取过去 N 天的历史数据"""
        data = []
        for i in range(days):
            date = datetime.now().date() - timedelta(days=i)
            try:
                daily = self.get_daily_summary(date)
                data.append(daily)
            except Exception as e:
                print(f"Error getting data for {date}: {e}")
        
        return pd.DataFrame(data)


if __name__ == "__main__":
    exporter = HealthDataExporter()
    
    # 打印今日数据
    today = exporter.get_daily_summary()
    print("=== 今日健康数据 ===")
    for k, v in today.items():
        print(f"{k}: {v}")
    
    # 获取30天历史
    print("\n=== 近30天趋势 ===")
    df = exporter.get_historical_data(30)
    print(df[['date', 'steps', 'sleep_hours', 'resting_heart_rate']].head(10))

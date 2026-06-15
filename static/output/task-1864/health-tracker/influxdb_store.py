#!/usr/bin/env python3
"""
InfluxDB 时序数据存储模块
用于存储和查询健康指标数据
"""

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import yaml
from datetime import datetime, timedelta
from pathlib import Path

class HealthInfluxDB:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        influx_cfg = self.config['influxdb']
        self.client = InfluxDBClient(
            url=influx_cfg['url'],
            token=influx_cfg['token'],
            org=influx_cfg['org']
        )
        self.bucket = influx_cfg['bucket']
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()
    
    def save_daily_metrics(self, metrics, scores):
        """保存每日健康指标和评分"""
        date = datetime.fromisoformat(metrics['date'])
        
        # 原始指标数据点
        point_metrics = Point("health_metrics")\
            .tag("source", metrics.get('source', 'unknown'))\
            .field("steps", int(metrics.get('steps', 0)))\
            .field("distance_km", float(metrics.get('distance_km', 0)))\
            .field("active_calories", int(metrics.get('active_calories', 0)))\
            .field("resting_heart_rate", int(metrics.get('resting_heart_rate', 0)))\
            .field("avg_heart_rate", int(metrics.get('avg_heart_rate', 0)))\
            .field("max_heart_rate", int(metrics.get('max_heart_rate', 0)))\
            .field("sleep_hours", float(metrics.get('sleep_hours', 0)))\
            .field("sleep_deep_hours", float(metrics.get('sleep_deep_hours', 0)))\
            .field("sleep_rem_hours", float(metrics.get('sleep_rem_hours', 0)))\
            .field("stand_hours", int(metrics.get('stand_hours', 0)))\
            .field("flights_climbed", int(metrics.get('flights_climbed', 0)))\
            .time(date)
        
        # 评分数据点
        point_scores = Point("health_scores")\
            .field("total", float(scores.get('total', 0)))\
            .field("activity", float(scores.get('activity', 0)))\
            .field("sleep", float(scores.get('sleep', 0)))\
            .field("heart_rate", float(scores.get('heart_rate', 0)))\
            .field("energy", float(scores.get('energy', 0)))\
            .field("grade", str(scores.get('grade', '')))\
            .time(date)
        
        self.write_api.write(bucket=self.bucket, record=[point_metrics, point_scores])
        return True
    
    def query_recent(self, days=7):
        """查询最近 N 天的数据"""
        start_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: {start_time})
            |> filter(fn: (r) => r._measurement == "health_metrics" or r._measurement == "health_scores")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            |> sort(columns: ["_time"], desc: false)
        '''
        
        tables = self.query_api.query(query)
        results = []
        for table in tables:
            for record in table.records:
                results.append(record.values)
        return results
    
    def query_aggregated(self, days=30, aggregation='mean'):
        """查询聚合统计数据"""
        start_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: {start_time})
            |> filter(fn: (r) => r._measurement == "health_metrics")
            |> aggregateWindow(every: 1d, fn: {aggregation}, createEmpty: false)
            |> yield(name: "{aggregation}")
        '''
        
        tables = self.query_api.query(query)
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    'time': record.get_time().isoformat(),
                    'field': record.get_field(),
                    'value': record.get_value()
                })
        return results
    
    def close(self):
        self.client.close()


if __name__ == "__main__":
    db = HealthInfluxDB()
    
    # 测试写入
    test_metrics = {
        'date': datetime.now().date().isoformat(),
        'steps': 10000,
        'active_calories': 500,
        'resting_heart_rate': 65,
        'sleep_hours': 7.5,
        'source': 'mock'
    }
    test_scores = {
        'total': 85.5,
        'activity': 90,
        'sleep': 85,
        'heart_rate': 80,
        'energy': 88,
        'grade': 'A'
    }
    
    db.save_daily_metrics(test_metrics, test_scores)
    # print("✅ 测试数据已写入 InfluxDB")
    db.close()

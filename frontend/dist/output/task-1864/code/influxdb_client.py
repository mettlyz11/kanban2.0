#!/usr/bin/env python3
"""
InfluxDB 时序数据库客户端
用于存储和查询健康数据
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import asdict
import logging

logger = logging.getLogger(__name__)

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS
    INFLUX_AVAILABLE = True
except ImportError:
    INFLUX_AVAILABLE = False
    logger.warning("InfluxDB client not installed, using file-based storage")

class HealthInfluxDB:
    """健康数据InfluxDB客户端"""
    
    def __init__(self, 
                 url: str = "http://localhost:8086",
                 token: str = None,
                 org: str = "health",
                 bucket: str = "health_metrics"):
        
        self.url = url
        self.token = token or os.getenv("INFLUXDB_TOKEN", "my-token")
        self.org = org
        self.bucket = bucket
        self.client = None
        self.write_api = None
        self.query_api = None
        
        if INFLUX_AVAILABLE:
            self._init_client()
        else:
            self._init_file_storage()
    
    def _init_client(self):
        """初始化InfluxDB客户端"""
        try:
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org
            )
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()
            logger.info(f"InfluxDB client initialized: {self.url}")
        except Exception as e:
            logger.warning(f"Failed to connect to InfluxDB: {e}, using file storage")
            self._init_file_storage()
    
    def _init_file_storage(self):
        """初始化文件存储（备选方案）"""
        self.file_storage_path = "/Users/mettlyz/.openclaw/workspace/output/task-1864/data/influxdb_mock.json"
        os.makedirs(os.path.dirname(self.file_storage_path), exist_ok=True)
        if not os.path.exists(self.file_storage_path):
            with open(self.file_storage_path, 'w') as f:
                json.dump([], f)
        logger.info("Using file-based storage for health metrics")
    
    def write_health_metrics(self, metrics: Dict) -> bool:
        """写入健康指标数据"""
        if self.client and self.write_api:
            return self._write_to_influxdb(metrics)
        else:
            return self._write_to_file(metrics)
    
    def _write_to_influxdb(self, metrics: Dict) -> bool:
        """写入真实InfluxDB"""
        try:
            point = Point("health_metrics") \
                .tag("source", "apple_watch") \
                .field("steps", float(metrics.get('steps', 0))) \
                .field("exercise_minutes", float(metrics.get('exercise_minutes', 0))) \
                .field("active_energy", float(metrics.get('active_energy', 0))) \
                .field("heart_rate_resting", float(metrics.get('heart_rate_resting', 0))) \
                .field("heart_rate_avg", float(metrics.get('heart_rate_avg', 0))) \
                .field("sleep_total", float(metrics.get('sleep_total', 0))) \
                .field("sleep_deep", float(metrics.get('sleep_deep', 0))) \
                .field("score_total", float(metrics.get('score_total', 0))) \
                .field("score_exercise", float(metrics.get('score_exercise', 0))) \
                .field("score_sleep", float(metrics.get('score_sleep', 0))) \
                .field("score_heart", float(metrics.get('score_heart', 0))) \
                .field("score_energy", float(metrics.get('score_energy', 0))) \
                .time(metrics.get('date', datetime.now().isoformat()))
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug(f"Wrote metrics for {metrics.get('date')}")
            return True
        except Exception as e:
            logger.error(f"Error writing to InfluxDB: {e}")
            return False
    
    def _write_to_file(self, metrics: Dict) -> bool:
        """写入文件存储"""
        try:
            with open(self.file_storage_path, 'r') as f:
                data = json.load(f)
            
            metrics['timestamp'] = datetime.now().isoformat()
            data.append(metrics)
            
            with open(self.file_storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error writing to file: {e}")
            return False
    
    def query_metrics(self, start_date: str, end_date: str = None) -> List[Dict]:
        """查询指标数据"""
        if self.client and self.query_api:
            return self._query_from_influxdb(start_date, end_date)
        else:
            return self._query_from_file(start_date, end_date)
    
    def _query_from_influxdb(self, start_date: str, end_date: str = None) -> List[Dict]:
        """从InfluxDB查询数据"""
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: {start_date}, stop: {end_date or 'now()'})
          |> filter(fn: (r) => r["_measurement"] == "health_metrics")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        result = self.query_api.query(query)
        return [record.values for table in result for record in table.records]
    
    def _query_from_file(self, start_date: str, end_date: str = None) -> List[Dict]:
        """从文件查询数据"""
        with open(self.file_storage_path, 'r') as f:
            data = json.load(f)
        
        filtered = [
            item for item in data
            if start_date <= item.get('date', '') <= (end_date or '9999-12-31')
        ]
        return filtered
    
    def batch_write(self, metrics_list: List[Dict]) -> int:
        """批量写入数据"""
        success_count = 0
        for metrics in metrics_list:
            if self.write_health_metrics(metrics):
                success_count += 1
        logger.info(f"Batch write completed: {success_count}/{len(metrics_list)} successful")
        return success_count
    
    def close(self):
        """关闭连接"""
        if self.client:
            self.client.close()

# Docker Compose 配置文件
DOCKER_COMPOSE_CONFIG = """
version: '3.8'

services:
  influxdb:
    image: influxdb:2.7
    container_name: health-influxdb
    ports:
      - "8086:8086"
    volumes:
      - influxdb_data:/var/lib/influxdb2
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_PASSWORD=admin123456
      - DOCKER_INFLUXDB_INIT_ORG=health
      - DOCKER_INFLUXDB_INIT_BUCKET=health_metrics
      - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=my-token
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.2.0
    container_name: health-grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on:
      - influxdb
    restart: unless-stopped

volumes:
  influxdb_data:
  grafana_data:
"""

GRAFANA_DATASOURCE_CONFIG = """
apiVersion: 1

datasources:
  - name: InfluxDB
    type: influxdb
    access: proxy
    url: http://influxdb:8086
    jsonData:
      version: Flux
      organization: health
      defaultBucket: health_metrics
      tlsSkipVerify: true
    secureJsonData:
      token: my-token
    isDefault: true
    editable: true
"""

def generate_docker_configs(output_dir: str):
    """生成Docker配置文件"""
    config_dir = f"{output_dir}/docker"
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(f"{config_dir}/grafana/provisioning/datasources", exist_ok=True)
    
    with open(f"{config_dir}/docker-compose.yml", 'w') as f:
        f.write(DOCKER_COMPOSE_CONFIG)
    
    with open(f"{config_dir}/grafana/provisioning/datasources/influxdb.yml", 'w') as f:
        f.write(GRAFANA_DATASOURCE_CONFIG)
    
    logger.info(f"Docker configs generated in {config_dir}")

if __name__ == '__main__':
    # 生成Docker配置
    generate_docker_configs("/Users/mettlyz/.openclaw/workspace/output/task-1864")
    print("✅ Docker配置文件已生成")

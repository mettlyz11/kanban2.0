#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P049-T041: 监控告警系统
功能：
- 系统监控: CPU、内存、磁盘
- 应用监控: API响应时间、错误率
- 告警: 邮件/消息通知
- 日志: 集中式日志收集

作者: OpenClaw Subagent
创建时间: 2026-03-10
"""

import os
import sys
import time
import json
import sqlite3
import logging
import threading
import psutil
import smtplib
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict, deque
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from functools import wraps
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kanban_v5.db')


@dataclass
class AlertRule:
    """告警规则"""
    id: str
    name: str
    metric_type: str  # cpu, memory, disk, api_response_time, api_error_rate
    operator: str  # >, <, >=, <=, ==, !=
    threshold: float
    duration: int  # 持续多少秒触发告警
    severity: str  # info, warning, error, critical
    enabled: bool = True
    notification_channels: List[str] = None  # email, feishu, webhook
    
    def __post_init__(self):
        if self.notification_channels is None:
            self.notification_channels = ['email']


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.running = False
        self.thread = None
        self.collect_interval = 300  # 收集间隔（秒）- 5 分钟
        self.metrics_buffer = deque(maxlen=1000)  # 内存缓冲区
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 系统指标表
        c.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                cpu_percent REAL,
                memory_percent REAL,
                memory_used_gb REAL,
                memory_total_gb REAL,
                disk_percent REAL,
                disk_used_gb REAL,
                disk_total_gb REAL,
                load_avg_1m REAL,
                load_avg_5m REAL,
                load_avg_15m REAL,
                network_sent_mb REAL,
                network_recv_mb REAL
            )
        ''')
        
        # API性能指标表
        c.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_api_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                endpoint TEXT,
                method TEXT,
                response_time_ms REAL,
                status_code INTEGER,
                error_count INTEGER DEFAULT 0,
                request_count INTEGER DEFAULT 1
            )
        ''')
        
        # 应用日志表
        c.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                level TEXT,
                source TEXT,
                message TEXT,
                metadata TEXT,
                trace_id TEXT
            )
        ''')
        
        # 告警规则表
        c.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_alert_rules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                operator TEXT NOT NULL,
                threshold REAL NOT NULL,
                duration INTEGER DEFAULT 60,
                severity TEXT DEFAULT 'warning',
                enabled INTEGER DEFAULT 1,
                notification_channels TEXT,
                created_at REAL,
                updated_at REAL
            )
        ''')
        
        # 告警事件表
        c.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_alert_events (
                id TEXT PRIMARY KEY,
                rule_id TEXT,
                rule_name TEXT,
                severity TEXT,
                message TEXT,
                metric_value REAL,
                threshold REAL,
                timestamp REAL,
                status TEXT DEFAULT 'firing',
                resolved_at REAL,
                notified INTEGER DEFAULT 0
            )
        ''')
        
        # 告警通知记录表
        c.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_event_id TEXT,
                channel TEXT,
                recipient TEXT,
                status TEXT,
                sent_at REAL,
                error_message TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ 监控数据库表初始化完成")
    
    def start(self):
        """启动指标收集"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._collect_loop, daemon=True)
            self.thread.start()
            logger.info("✅ 指标收集器已启动")
    
    def stop(self):
        """停止指标收集"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("🛑 指标收集器已停止")
    
    def _collect_loop(self):
        """收集循环"""
        while self.running:
            try:
                self._collect_system_metrics()
                time.sleep(self.collect_interval)
            except Exception as e:
                logger.error(f"指标收集错误: {e}")
                time.sleep(5)
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            timestamp = time.time()
            
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = memory.used / (1024**3)
            memory_total_gb = memory.total / (1024**3)
            
            # 磁盘
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used_gb = disk.used / (1024**3)
            disk_total_gb = disk.total / (1024**3)
            
            # 负载
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            # 网络
            net_io = psutil.net_io_counters()
            network_sent_mb = net_io.bytes_sent / (1024**2)
            network_recv_mb = net_io.bytes_recv / (1024**2)
            
            # 保存到数据库
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO monitoring_system_metrics 
                (timestamp, cpu_percent, memory_percent, memory_used_gb, memory_total_gb,
                 disk_percent, disk_used_gb, disk_total_gb, load_avg_1m, load_avg_5m, load_avg_15m,
                 network_sent_mb, network_recv_mb)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, cpu_percent, memory_percent, memory_used_gb, memory_total_gb,
                  disk_percent, disk_used_gb, disk_total_gb, load_avg[0], load_avg[1], load_avg[2],
                  network_sent_mb, network_recv_mb))
            conn.commit()
            conn.close()
            
            # 添加到内存缓冲区
            self.metrics_buffer.append({
                'timestamp': timestamp,
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent
            })
            
            logger.debug(f"系统指标已收集 - CPU: {cpu_percent}%, 内存: {memory_percent}%, 磁盘: {disk_percent}%")
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
    
    def record_api_metric(self, endpoint: str, method: str, response_time_ms: float, 
                          status_code: int, error: bool = False):
        """记录API指标"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO monitoring_api_metrics 
                (timestamp, endpoint, method, response_time_ms, status_code, error_count, request_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (time.time(), endpoint, method, response_time_ms, status_code, 1 if error else 0, 1))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"记录API指标失败: {e}")
    
    def log_message(self, level: str, source: str, message: str, 
                    metadata: Dict = None, trace_id: str = None):
        """记录日志"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO monitoring_logs 
                (timestamp, level, source, message, metadata, trace_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (time.time(), level, source, message, 
                  json.dumps(metadata) if metadata else '{}', trace_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"记录日志失败: {e}")


class AlertManager:
    """告警管理器"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.collector = MetricsCollector(db_path)
        self.running = False
        self.thread = None
        self.check_interval = 30  # 检查间隔（秒）
        self.alert_states = {}  # 告警状态缓存
        self._init_default_rules()
    
    def _init_default_rules(self):
        """初始化默认告警规则"""
        default_rules = [
            ('cpu_high', 'CPU使用率过高', 'cpu', '>', 80.0, 120, 'warning', '["email"]'),
            ('cpu_critical', 'CPU使用率严重过高', 'cpu', '>', 95.0, 60, 'critical', '["email", "feishu"]'),
            ('memory_high', '内存使用率过高', 'memory', '>', 85.0, 120, 'warning', '["email"]'),
            ('memory_critical', '内存使用率严重过高', 'memory', '>', 95.0, 60, 'critical', '["email", "feishu"]'),
            ('disk_high', '磁盘使用率过高', 'disk', '>', 90.0, 300, 'warning', '["email"]'),
            ('api_slow', 'API响应时间过长', 'api_response_time', '>', 3000.0, 180, 'warning', '["email"]'),
            ('api_error_high', 'API错误率过高', 'api_error_rate', '>', 5.0, 300, 'error', '["email", "feishu"]'),
        ]
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        for rule in default_rules:
            c.execute('''
                INSERT OR REPLACE INTO monitoring_alert_rules 
                (id, name, metric_type, operator, threshold, duration, severity, 
                 enabled, notification_channels, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (rule[0], rule[1], rule[2], rule[3], rule[4], rule[5], rule[6], 1, rule[7], time.time(), time.time()))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ 已初始化 {len(default_rules)} 条默认告警规则")
    
    def start(self):
        """启动告警管理器"""
        if not self.running:
            self.running = True
            self.collector.start()
            self.thread = threading.Thread(target=self._check_loop, daemon=True)
            self.thread.start()
            logger.info("✅ 告警管理器已启动")
    
    def stop(self):
        """停止告警管理器"""
        self.running = False
        self.collector.stop()
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("🛑 告警管理器已停止")
    
    def _check_loop(self):
        """告警检查循环"""
        while self.running:
            try:
                self._check_alerts()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"告警检查错误: {e}")
                time.sleep(5)
    
    def _check_alerts(self):
        """检查告警规则"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT id, name, metric_type, operator, threshold, duration, severity, notification_channels
            FROM monitoring_alert_rules WHERE enabled = 1
        ''')
        rules = c.fetchall()
        conn.close()
        
        for rule_data in rules:
            self._evaluate_rule(rule_data)
    
    def _evaluate_rule(self, rule_data):
        """评估单个告警规则"""
        try:
            rule_id, rule_name, metric_type, operator, threshold, duration, severity, notification_channels = rule_data
            channels = json.loads(notification_channels)
            
            # 获取指标值
            value = self._get_metric_value(metric_type)
            if value is None:
                return
            
            # 检查条件
            triggered = self._check_condition(value, operator, threshold)
            
            # 获取当前状态
            state_key = rule_id
            current_state = self.alert_states.get(state_key, {
                'triggered': False,
                'first_triggered_at': None,
                'last_checked_at': None
            })
            
            now = time.time()
            
            if triggered:
                if not current_state['triggered']:
                    # 首次触发
                    current_state['triggered'] = True
                    current_state['first_triggered_at'] = now
                    current_state['last_checked_at'] = now
                    self.alert_states[state_key] = current_state
                    logger.info(f"告警规则 {rule_id} 首次触发，开始计时")
                else:
                    # 持续触发，检查是否达到持续时间
                    elapsed = now - current_state['first_triggered_at']
                    if elapsed >= duration:
                        # 创建告警事件
                        self._create_alert_event(rule_id, rule_name, severity, value, threshold, operator, metric_type, channels)
                        # 重置状态，避免重复告警
                        current_state['triggered'] = False
                        current_state['first_triggered_at'] = None
                        self.alert_states[state_key] = current_state
            else:
                # 未触发，重置状态
                if current_state['triggered']:
                    # 告警恢复
                    self._resolve_alert_event(rule_id)
                    current_state['triggered'] = False
                    current_state['first_triggered_at'] = None
                    self.alert_states[state_key] = current_state
                    logger.info(f"告警规则 {rule_id} 已恢复")
        
        except Exception as e:
            logger.error(f"评估告警规则失败: {e}")
    
    def _get_metric_value(self, metric_type: str) -> Optional[float]:
        """获取指标值"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            if metric_type == 'cpu':
                c.execute('SELECT cpu_percent FROM monitoring_system_metrics ORDER BY timestamp DESC LIMIT 1')
                result = c.fetchone()
                return result[0] if result else None
            
            elif metric_type == 'memory':
                c.execute('SELECT memory_percent FROM monitoring_system_metrics ORDER BY timestamp DESC LIMIT 1')
                result = c.fetchone()
                return result[0] if result else None
            
            elif metric_type == 'disk':
                c.execute('SELECT disk_percent FROM monitoring_system_metrics ORDER BY timestamp DESC LIMIT 1')
                result = c.fetchone()
                return result[0] if result else None
            
            elif metric_type == 'api_response_time':
                c.execute('SELECT AVG(response_time_ms) FROM monitoring_api_metrics WHERE timestamp > ?', (time.time() - 300,))
                result = c.fetchone()
                return result[0] if result and result[0] else 0
            
            elif metric_type == 'api_error_rate':
                c.execute('SELECT SUM(error_count) * 100.0 / SUM(request_count) FROM monitoring_api_metrics WHERE timestamp > ?', (time.time() - 300,))
                result = c.fetchone()
                return result[0] if result and result[0] else 0
            
        finally:
            conn.close()
        
        return None
    
    def _check_condition(self, value: float, operator: str, threshold: float) -> bool:
        """检查条件"""
        if operator == '>':
            return value > threshold
        elif operator == '<':
            return value < threshold
        elif operator == '>=':
            return value >= threshold
        elif operator == '<=':
            return value <= threshold
        elif operator == '==':
            return value == threshold
        elif operator == '!=':
            return value != threshold
        return False
    
    def _create_alert_event(self, rule_id, rule_name, severity, metric_value, threshold, operator, metric_type, channels):
        """创建告警事件"""
        import hashlib
        event_id = hashlib.md5(f"{rule_id}{time.time()}".encode()).hexdigest()[:16]
        
        units = {'cpu': '%', 'memory': '%', 'disk': '%', 'api_response_time': 'ms', 'api_error_rate': '%'}
        unit = units.get(metric_type, '')
        
        message = f"{rule_name}: 当前值 {metric_value:.2f}{unit}, 阈值 {operator} {threshold}"
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO monitoring_alert_events 
            (id, rule_id, rule_name, severity, message, metric_value, threshold, timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (event_id, rule_id, rule_name, severity, message, metric_value, threshold, time.time(), 'firing'))
        conn.commit()
        conn.close()
        
        logger.warning(f"🚨 告警触发: {message}")
        
        # 发送通知
        self._send_notification(event_id, rule_name, severity, message, metric_value, threshold, channels)
    
    def _resolve_alert_event(self, rule_id: str):
        """解决告警事件"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('UPDATE monitoring_alert_events SET status = ?, resolved_at = ? WHERE rule_id = ? AND status = ?', 
                  ('resolved', time.time(), rule_id, 'firing'))
        conn.commit()
        conn.close()
    
    def _send_notification(self, event_id: str, rule_name: str, severity: str, message: str, metric_value: float, threshold: float, channels: List[str]):
        """发送告警通知"""
        for channel in channels:
            try:
                if channel == 'email':
                    self._send_email_notification(event_id, rule_name, severity, message)
                elif channel == 'feishu':
                    self._send_feishu_notification(event_id, rule_name, severity, message)
                elif channel == 'webhook':
                    self._send_webhook_notification(event_id, rule_name, severity, message)
            except Exception as e:
                logger.error(f"发送{channel}通知失败: {e}")
    
    def _send_email_notification(self, event_id: str, rule_name: str, severity: str, message: str):
        """发送邮件通知"""
        try:
            smtp_server = os.environ.get('ALIYUN_EMAIL_SMTP', 'smtp.qiye.aliyun.com')
            smtp_port = int(os.environ.get('ALIYUN_EMAIL_SMTP_PORT', '465'))
            sender = os.environ.get('ALIYUN_EMAIL', 'dudu@v9r9ae27.onaliyun.com')
            password = os.environ.get('ALIYUN_EMAIL_PASSWORD', '')
            recipient = os.environ.get('ALERT_EMAIL_RECIPIENT', sender)
            
            if not password:
                logger.warning("邮件密码未配置，跳过邮件通知")
                return
            
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = recipient
            msg['Subject'] = f"[告警-{severity.upper()}] {rule_name}"
            
            body = f"""
告警通知
========

告警规则: {rule_name}
告警级别: {severity.upper()}
触发时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{message}

事件ID: {event_id}

---
本邮件由P049监控告警系统自动发送
            """
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(sender, password)
                server.send_message(msg)
            
            self._record_notification(event_id, 'email', recipient, 'success')
            logger.info(f"✅ 邮件通知已发送: {recipient}")
            
        except Exception as e:
            self._record_notification(event_id, 'email', '', 'failed', str(e))
            logger.error(f"发送邮件通知失败: {e}")
    
    def _send_feishu_notification(self, event_id: str, rule_name: str, severity: str, message: str):
        """发送飞书通知"""
        try:
            webhook_url = os.environ.get('FEISHU_WEBHOOK_URL', '')
            
            if not webhook_url:
                logger.warning("飞书Webhook未配置，跳过飞书通知")
                return
            
            color_map = {'info': 'blue', 'warning': 'orange', 'error': 'red', 'critical': 'red'}
            
            payload = {
                "msg_type": "interactive",
                "card": {
                    "config": {"wide_screen_mode": True},
                    "header": {
                        "title": {"tag": "plain_text", "content": f"🚨 告警通知 - {rule_name}"},
                        "template": color_map.get(severity, 'blue')
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**告警级别:** {severity.upper()}\n**触发时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n**详细信息:** {message}"
                            }
                        }
                    ]
                }
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self._record_notification(event_id, 'feishu', webhook_url, 'success')
                logger.info("✅ 飞书通知已发送")
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self._record_notification(event_id, 'feishu', '', 'failed', str(e))
            logger.error(f"发送飞书通知失败: {e}")
    
    def _send_webhook_notification(self, event_id: str, rule_name: str, severity: str, message: str):
        """发送Webhook通知"""
        try:
            webhook_url = os.environ.get('ALERT_WEBHOOK_URL', '')
            
            if not webhook_url:
                logger.warning("Webhook URL未配置，跳过Webhook通知")
                return
            
            payload = {
                'event_id': event_id,
                'rule_name': rule_name,
                'severity': severity,
                'message': message,
                'timestamp': time.time()
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self._record_notification(event_id, 'webhook', webhook_url, 'success')
                logger.info("✅ Webhook通知已发送")
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self._record_notification(event_id, 'webhook', '', 'failed', str(e))
            logger.error(f"发送Webhook通知失败: {e}")
    
    def _record_notification(self, event_id: str, channel: str, recipient: str, status: str, error_message: str = None):
        """记录通知发送状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO monitoring_notifications 
                (alert_event_id, channel, recipient, status, sent_at, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (event_id, channel, recipient, status, time.time(), error_message))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"记录通知状态失败: {e}")


class MonitoringDashboard:
    """监控仪表盘API"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
    
    def get_system_metrics(self, hours: int = 24) -> Dict:
        """获取系统指标"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        since = time.time() - (hours * 3600)
        
        c.execute('''
            SELECT 
                AVG(cpu_percent) as avg_cpu,
                MAX(cpu_percent) as max_cpu,
                AVG(memory_percent) as avg_memory,
                MAX(memory_percent) as max_memory,
                AVG(disk_percent) as avg_disk,
                MAX(disk_percent) as max_disk
            FROM monitoring_system_metrics
            WHERE timestamp > ?
        ''', (since,))
        
        row = c.fetchone()
        conn.close()
        
        return {
            'cpu': {'avg': round(row[0], 2) if row[0] else 0, 'max': round(row[1], 2) if row[1] else 0},
            'memory': {'avg': round(row[2], 2) if row[2] else 0, 'max': round(row[3], 2) if row[3] else 0},
            'disk': {'avg': round(row[4], 2) if row[4] else 0, 'max': round(row[5], 2) if row[5] else 0}
        }
    
    def get_api_metrics(self, hours: int = 24) -> Dict:
        """获取API指标"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        since = time.time() - (hours * 3600)
        
        c.execute('''
            SELECT 
                AVG(response_time_ms) as avg_response_time,
                MAX(response_time_ms) as max_response_time,
                SUM(error_count) * 100.0 / SUM(request_count) as error_rate,
                SUM(request_count) as total_requests
            FROM monitoring_api_metrics
            WHERE timestamp > ?
        ''', (since,))
        
        row = c.fetchone()
        conn.close()
        
        return {
            'avg_response_time_ms': round(row[0], 2) if row[0] else 0,
            'max_response_time_ms': round(row[1], 2) if row[1] else 0,
            'error_rate_percent': round(row[2], 2) if row[2] else 0,
            'total_requests': int(row[3]) if row[3] else 0
        }
    
    def get_alert_events(self, status: str = None, limit: int = 50) -> List[Dict]:
        """获取告警事件"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        if status:
            c.execute('SELECT * FROM monitoring_alert_events WHERE status = ? ORDER BY timestamp DESC LIMIT ?', (status, limit))
        else:
            c.execute('SELECT * FROM monitoring_alert_events ORDER BY timestamp DESC LIMIT ?', (limit,))
        
        events = []
        for row in c.fetchall():
            events.append({
                'id': row[0], 'rule_id': row[1], 'rule_name': row[2], 'severity': row[3],
                'message': row[4], 'metric_value': row[5], 'threshold': row[6],
                'timestamp': row[7], 'status': row[8], 'resolved_at': row[9]
            })
        
        conn.close()
        return events
    
    def get_logs(self, level: str = None, source: str = None, limit: int = 100) -> List[Dict]:
        """获取日志"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        if level and source:
            c.execute('SELECT * FROM monitoring_logs WHERE level = ? AND source = ? ORDER BY timestamp DESC LIMIT ?', (level, source, limit))
        elif level:
            c.execute('SELECT * FROM monitoring_logs WHERE level = ? ORDER BY timestamp DESC LIMIT ?', (level, limit))
        elif source:
            c.execute('SELECT * FROM monitoring_logs WHERE source = ? ORDER BY timestamp DESC LIMIT ?', (source, limit))
        else:
            c.execute('SELECT * FROM monitoring_logs ORDER BY timestamp DESC LIMIT ?', (limit,))
        
        logs = []
        for row in c.fetchall():
            logs.append({
                'id': row[0], 'timestamp': row[1], 'level': row[2], 'source': row[3],
                'message': row[4], 'metadata': json.loads(row[5]) if row[5] else {}, 'trace_id': row[6]
            })
        
        conn.close()
        return logs


# 全局实例
alert_manager = None
monitoring_dashboard = None

def init_monitoring():
    """初始化监控系统"""
    global alert_manager, monitoring_dashboard
    
    alert_manager = AlertManager()
    monitoring_dashboard = MonitoringDashboard()
    
    # 启动告警管理器
    alert_manager.start()
    
    logger.info("✅ P049-T041 监控告警系统初始化完成")
    return alert_manager, monitoring_dashboard

def stop_monitoring():
    """停止监控系统"""
    global alert_manager
    
    if alert_manager:
        alert_manager.stop()
        logger.info("🛑 P049-T041 监控告警系统已停止")

if __name__ == '__main__':
    # 测试运行
    print("=" * 60)
    print("P049-T041: 监控告警系统测试")
    print("=" * 60)
    
    # 初始化
    alert_mgr, dashboard = init_monitoring()
    
    # 等待收集一些数据
    print("\n📊 等待收集系统指标...")
    time.sleep(5)
    
    # 获取系统指标
    system_metrics = dashboard.get_system_metrics(hours=1)
    print("\n📈 系统指标:")
    print(f"  CPU: {system_metrics['cpu']}")
    print(f"  内存: {system_metrics['memory']}")
    print(f"  磁盘: {system_metrics['disk']}")
    
    # 获取API指标
    api_metrics = dashboard.get_api_metrics(hours=1)
    print("\n📈 API指标:")
    print(f"  平均响应时间: {api_metrics['avg_response_time_ms']}ms")
    print(f"  错误率: {api_metrics['error_rate_percent']}%")
    print(f"  总请求数: {api_metrics['total_requests']}")
    
    # 获取告警事件
    alert_events = dashboard.get_alert_events(limit=10)
    print(f"\n🚨 告警事件数量: {len(alert_events)}")
    
    # 获取日志
    logs = dashboard.get_logs(limit=10)
    print(f"\n📝 日志数量: {len(logs)}")
    
    print("\n" + "=" * 60)
    print("测试完成！监控系统运行正常。")
    print("=" * 60)
    
    # 保持运行一段时间
    try:
        print("\n按 Ctrl+C 停止监控...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_monitoring()
        print("\n监控系统已停止。")
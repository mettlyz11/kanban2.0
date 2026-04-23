#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
感知Agent (Perception Agent) - 智能监听与分析系统

功能：实时监控系统日志、错误、性能指标和用户行为，
      智能分析并触发相应的响应动作。
"""

import os
import re
import sys
import time
import json
import hashlib
import threading
import subprocess
import traceback
from datetime import datetime, timedelta
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple
import logging

# 尝试导入yaml

try:
    import yaml
except ImportError:
    yaml = None

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('PerceptionAgent')


# =============================================================================
# 事件定义
# =============================================================================

class EventType:
    LOG_ERROR = "log_error"
    API_ERROR = "api_error"
    METRIC_ALERT = "metric_alert"
    BEHAVIOR_PATTERN = "behavior_pattern"
    EXTERNAL_UPDATE = "external_update"


class SeverityLevel:
    CRITICAL = "critical"  # 立即触发
    HIGH = "high"          # 1小时内触发
    MEDIUM = "medium"      # 每日汇总
    LOW = "low"            # 周度改进


class PerceptionEvent:
    """感知事件"""
    def __init__(self, event_type: str, severity: str, source: str,
                 message: str, data: Dict = None, timestamp=None):
        self.id = hashlib.md5(f"{time.time()}{message}".encode()).hexdigest()[:12]
        self.type = event_type
        self.severity = severity
        self.source = source
        self.message = message
        self.data = data or {}
        self.timestamp = timestamp or datetime.now()
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """计算事件哈希（用于去重）"""
        content = f"{self.type}:{self.source}:{self.message}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "severity": self.severity,
            "source": self.source,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "hash": self.hash
        }

    def __repr__(self):
        return f"<PerceptionEvent {self.type}:{self.severity} from {self.source}>"


# =============================================================================
# 基础监听器类
# =============================================================================

class BaseListener:
    """监听器基类"""
    def __init__(self, name: str, config: Dict = None):
        self.name = name
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
        self.running = False
        self.thread = None
        self._callbacks: List[Callable] = []

    def on_event(self, callback: Callable):
        """注册事件回调"""
        self._callbacks.append(callback)
        return self

    def emit(self, event: PerceptionEvent):
        """触发事件"""
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def start(self):
        """启动监听器"""
        if not self.enabled or self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"Listener '{self.name}' started")

    def stop(self):
        """停止监听器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info(f"Listener '{self.name}' stopped")

    def _run(self):
        """子类需要实现的运行逻辑"""
        raise NotImplementedError


# =============================================================================
# 日志监听器
# =============================================================================

class LogListener(BaseListener):
    """日志文件监听器"""

    def __init__(self, config: Dict = None):
        super().__init__("LogListener", config)
        self.files = self.config.get('files', [])
        self.patterns = self.config.get('patterns', [])
        self._file_positions: Dict[str, int] = {}
        self._compiled_patterns: List[Tuple[re.Pattern, Dict]] = []

    def _compile_patterns(self):
        """编译正则表达式"""
        self._compiled_patterns = []
        for pattern in self.patterns:
            regex = pattern.get('regex', '')
            try:
                compiled = re.compile(regex, re.IGNORECASE)
                self._compiled_patterns.append((compiled, pattern))
            except re.error as e:
                logger.error(f"Invalid regex pattern '{regex}': {e}")

    def _run(self):
        """监控日志文件"""
        self._compile_patterns()
        poll_interval = self.config.get('poll_interval', 2)

        # 初始化文件位置
        for filepath in self.files:
            if os.path.exists(filepath):
                self._file_positions[filepath] = os.path.getsize(filepath)

        while self.running:
            for filepath in self.files:
                if not os.path.exists(filepath):
                    continue

                try:
                    self._check_file(filepath)
                except Exception as e:
                    logger.error(f"Error reading {filepath}: {e}")

            time.sleep(poll_interval)

    def _check_file(self, filepath: str):
        """检查单个文件的新内容"""
        current_size = os.path.getsize(filepath)
        last_position = self._file_positions.get(filepath, 0)

        if current_size < last_position:
            # 文件被轮转
            last_position = 0

        if current_size == last_position:
            return

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(last_position)
            new_lines = f.readlines()
            self._file_positions[filepath] = f.tell()

        for line in new_lines:
            self._process_line(filepath, line.strip())

    def _process_line(self, source: str, line: str):
        """处理单行日志"""
        for pattern, config in self._compiled_patterns:
            if pattern.search(line):
                severity = config.get('severity', 'medium')
                event = PerceptionEvent(
                    event_type=EventType.LOG_ERROR,
                    severity=severity,
                    source=os.path.basename(source),
                    message=line[:500],  # 限制长度
                    data={
                        'filepath': source,
                        'matched_pattern': config.get('regex'),
                        'action': config.get('action', 'log')
                    }
                )
                self.emit(event)
                break  # 一行只匹配一个模式


# =============================================================================
# 错误监听器
# =============================================================================

class ErrorListener(BaseListener):
    """API和系统错误监听器"""

    def __init__(self, config: Dict = None):
        super().__init__("ErrorListener", config)
        self.dedup_window = self.config.get('dedup_window', 3600)
        self._error_history: deque = deque(maxlen=1000)
        self._lock = threading.Lock()

    def _run(self):
        """错误监听器主要通过外部调用记录错误"""
        # 此监听器被动接收错误，不需要主动轮询
        while self.running:
            time.sleep(10)

    def record_error(self, error_type: str, message: str, data: Dict = None,
                     severity: str = SeverityLevel.HIGH):
        """记录错误（供外部调用）"""
        event = PerceptionEvent(
            event_type=EventType.API_ERROR,
            severity=severity,
            source=error_type,
            message=message,
            data=data or {}
        )

        # 检查是否重复
        if self._is_duplicate(event.hash):
            logger.debug(f"Duplicate error ignored: {event.hash}")
            return False

        with self._lock:
            self._error_history.append({
                'hash': event.hash,
                'timestamp': datetime.now()
            })

        self.emit(event)
        return True

    def _is_duplicate(self, error_hash: str) -> bool:
        """检查错误是否重复"""
        cutoff_time = datetime.now() - timedelta(seconds=self.dedup_window)

        with self._lock:
            for record in self._error_history:
                if record['hash'] == error_hash and record['timestamp'] > cutoff_time:
                    return True
        return False

    def record_api_error(self, status_code: int, endpoint: str,
                         error_message: str = None, request_data: Dict = None):
        """记录API错误"""
        severity = SeverityLevel.CRITICAL if status_code >= 500 else SeverityLevel.HIGH

        self.record_error(
            error_type="api_error",
            message=f"API Error {status_code}: {endpoint} - {error_message or 'Unknown'}",
            data={
                'status_code': status_code,
                'endpoint': endpoint,
                'error_message': error_message,
                'request_data': request_data
            },
            severity=severity
        )


# =============================================================================
# 性能指标监听器
# =============================================================================

class MetricListener(BaseListener):
    """系统性能指标监听器"""

    def __init__(self, config: Dict = None):
        super().__init__("MetricListener", config)
        self.metrics = self.config.get('metrics', [])
        self._metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._alert_states: Dict[str, bool] = {}

    def _run(self):
        """定期采集系统指标"""
        poll_interval = self.config.get('poll_interval', 30)

        while self.running:
            try:
                self._collect_metrics()
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")

            time.sleep(poll_interval)

    def _collect_metrics(self):
        """采集系统指标"""
        # CPU使用率
        cpu_usage = self._get_cpu_usage()
        self._check_metric('cpu_usage', cpu_usage)

        # 内存使用率
        memory_usage = self._get_memory_usage()
        self._check_metric('memory_usage', memory_usage)

        # 磁盘使用率
        disk_usage = self._get_disk_usage()
        self._check_metric('disk_usage', disk_usage)

    def _get_cpu_usage(self) -> float:
        """获取CPU使用率"""
        try:
            if sys.platform == 'darwin':  # macOS
                result = subprocess.run(['top', '-l', '1', '-n', '0'],
                                        capture_output=True, text=True)
                # 解析 macOS top 输出
                for line in result.stdout.split('\n'):
                    if 'CPU usage' in line:
                        # 格式: "CPU usage: 10.0% user, 5.0% sys, 85.0% idle"
                        match = re.search(r'(\d+\.?\d*)%\s*idle', line)
                        if match:
                            idle = float(match.group(1))
                            return round(100 - idle, 2)
            else:  # Linux
                result = subprocess.run(['top', '-bn1'],
                                        capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if '%Cpu' in line or 'Cpu(s)' in line:
                        match = re.search(r'(\d+\.?\d*)\s*id', line)
                        if match:
                            idle = float(match.group(1))
                            return round(100 - idle, 2)
        except Exception as e:
            logger.warning(f"Failed to get CPU usage: {e}")

        return 0.0

    def _get_memory_usage(self) -> float:
        """获取内存使用率"""
        try:
            if sys.platform == 'darwin':  # macOS
                result = subprocess.run(['vm_stat'],
                                        capture_output=True, text=True)
                # 解析 vm_stat 输出
                page_size = 4096
                pages_free = 0
                pages_active = 0
                pages_inactive = 0
                pages_wired = 0

                for line in result.stdout.split('\n'):
                    if 'Pages free' in line:
                        pages_free = int(re.search(r'(\d+)', line).group(1))
                    elif 'Pages active' in line:
                        pages_active = int(re.search(r'(\d+)', line).group(1))
                    elif 'Pages inactive' in line:
                        pages_inactive = int(re.search(r'(\d+)', line).group(1))
                    elif 'Pages wired down' in line:
                        pages_wired = int(re.search(r'(\d+)', line).group(1))

                total_pages = pages_free + pages_active + pages_inactive + pages_wired
                used_pages = pages_active + pages_inactive + pages_wired

                if total_pages > 0:
                    return round((used_pages / total_pages) * 100, 2)
            else:  # Linux
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()

                total = int(re.search(r'MemTotal:\s*(\d+)', meminfo).group(1))
                available = int(re.search(r'MemAvailable:\s*(\d+)', meminfo).group(1))
                used = total - available

                return round((used / total) * 100, 2)
        except Exception as e:
            logger.warning(f"Failed to get memory usage: {e}")

        return 0.0

    def _get_disk_usage(self) -> float:
        """获取磁盘使用率"""
        try:
            result = subprocess.run(['df', '-h', '/'],
                                    capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                # 格式: /dev/disk1s1  466Gi  200Gi  266Gi  43%  /
                parts = lines[1].split()
                if len(parts) >= 5:
                    usage_str = parts[4].replace('%', '')
                    return float(usage_str)
        except Exception as e:
            logger.warning(f"Failed to get disk usage: {e}")

        return 0.0

    def _check_metric(self, name: str, value: float):
        """检查指标是否超过阈值"""
        self._metric_history[name].append({
            'value': value,
            'timestamp': datetime.now()
        })

        # 查找对应的配置
        metric_config = None
        for m in self.metrics:
            if m.get('name') == name:
                metric_config = m
                break

        if not metric_config:
            return

        threshold = metric_config.get('threshold', 80)
        duration = metric_config.get('duration', 300)

        # 检查持续时间
        cutoff_time = datetime.now() - timedelta(seconds=duration)
        recent_values = [
            r['value'] for r in self._metric_history[name]
            if r['timestamp'] > cutoff_time
        ]

        if len(recent_values) < 3:  # 需要至少3个数据点
            return

        # 检查是否持续超过阈值
        all_above_threshold = all(v > threshold for v in recent_values[-5:])
        was_alerting = self._alert_states.get(name, False)

        if all_above_threshold and not was_alerting:
            # 触发告警
            self._alert_states[name] = True
            event = PerceptionEvent(
                event_type=EventType.METRIC_ALERT,
                severity=SeverityLevel.HIGH,
                source=f"metric:{name}",
                message=f"{name}持续超过阈值: {value}% (阈值: {threshold}%)",
                data={
                    'metric_name': name,
                    'current_value': value,
                    'threshold': threshold,
                    'duration': duration,
                    'recent_values': recent_values[-5:]
                }
            )
            self.emit(event)

        elif not all_above_threshold and was_alerting:
            # 告警恢复
            self._alert_states[name] = False
            logger.info(f"Metric {name} recovered")


# =============================================================================
# 行为监听器
# =============================================================================

class BehaviorListener(BaseListener):
    """用户行为监听器"""

    def __init__(self, config: Dict = None):
        super().__init__("BehaviorListener", config)
        self.patterns = self.config.get('patterns', [])
        self._action_history: deque = deque(maxlen=1000)
        self._lock = threading.Lock()

    def _run(self):
        """行为监听器被动接收数据"""
        while self.running:
            time.sleep(10)

    def record_action(self, user_id: str, action: str, target: str = None,
                      metadata: Dict = None):
        """记录用户操作（供外部调用）"""
        record = {
            'user_id': user_id,
            'action': action,
            'target': target,
            'metadata': metadata or {},
            'timestamp': datetime.now()
        }

        with self._lock:
            self._action_history.append(record)

        # 检查行为模式
        self._check_patterns(record)

    def _check_patterns(self, last_action: Dict):
        """检查行为模式"""
        user_id = last_action['user_id']
        action = last_action['action']

        for pattern in self.patterns:
            if pattern.get('name') == 'repeated_action':
                self._check_repeated_action(user_id, action, pattern)

    def _check_repeated_action(self, user_id: str, action: str, pattern: Dict):
        """检查重复操作"""
        window = pattern.get('window', 300)
        count_threshold = pattern.get('count', 3)

        cutoff_time = datetime.now() - timedelta(seconds=window)

        with self._lock:
            recent_count = sum(
                1 for r in self._action_history
                if r['user_id'] == user_id
                and r['action'] == action
                and r['timestamp'] > cutoff_time
            )

        if recent_count >= count_threshold:
            event = PerceptionEvent(
                event_type=EventType.BEHAVIOR_PATTERN,
                severity=SeverityLevel.LOW,
                source="behavior:repeated_action",
                message=f"用户 {user_id[:8]}... 在短时间内重复执行 '{action}' {recent_count} 次",
                data={
                    'user_id': user_id,
                    'action': action,
                    'count': recent_count,
                    'window': window,
                    'suggestion': '可能可以考虑添加批量操作功能'
                }
            )
            self.emit(event)


# =============================================================================
# 外部监听器
# =============================================================================

class ExternalListener(BaseListener):
    """外部源监听器（GitHub, arXiv等）"""

    def __init__(self, config: Dict = None):
        super().__init__("ExternalListener", config)
        self.sources = self.config.get('sources', [])

    def _run(self):
        """轮询外部源"""
        while self.running:
            for source in self.sources:
                if not source.get('enabled', True):
                    continue

                try:
                    self._poll_source(source)
                except Exception as e:
                    logger.error(f"Error polling {source.get('name')}: {e}")

            # 使用配置中的最小间隔
            min_interval = min(
                (s.get('interval', 300) for s in self.sources if s.get('enabled', True)),
                default=300
            )
            time.sleep(min_interval)

    def _poll_source(self, source: Dict):
        """轮询单个外部源"""
        name = source.get('name')

        if name == 'github':
            self._poll_github(source)
        elif name == 'arxiv':
            self._poll_arxiv(source)

    def _poll_github(self, source: Dict):
        """轮询GitHub通知"""
        # 实现简化版，实际需要OAuth认证
        pass

    def _poll_arxiv(self, source: Dict):
        """轮询arXiv论文"""
        # 实现简化版
        pass


# =============================================================================
# 事件处理器
# =============================================================================

class EventProcessor:
    """事件处理器 - 过滤、分析、触发"""

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self._dedup_cache: Dict[str, datetime] = {}
        self._dedup_lock = threading.Lock()
        self._action_handlers: Dict[str, Callable] = {}

        # 注册默认处理器
        self._register_default_handlers()

    def _register_default_handlers(self):
        """注册默认处理器"""
        self._action_handlers['immediate_reflection'] = self._handle_immediate_reflection
        self._action_handlers['delayed_reflection'] = self._handle_delayed_reflection
        self._action_handlers['daily_summary'] = self._handle_daily_summary
        self._action_handlers['weekly_improvement'] = self._handle_weekly_improvement
        self._action_handlers['suggest_optimization'] = self._handle_suggest_optimization
        self._action_handlers['alert'] = self._handle_alert
        self._action_handlers['log'] = self._handle_log

    def process(self, event: PerceptionEvent) -> bool:
        """处理事件"""
        # 1. 过滤
        if not self._filter(event):
            return False

        # 2. 分析
        event = self._analyze(event)

        # 3. 触发响应
        self._trigger(event)

        return True

    def _filter(self, event: PerceptionEvent) -> bool:
        """过滤事件"""
        # 去重检查
        with self._dedup_lock:
            if event.hash in self._dedup_cache:
                last_time = self._dedup_cache[event.hash]
                if datetime.now() - last_time < timedelta(seconds=300):
                    return False
            self._dedup_cache[event.hash] = datetime.now()

        return True

    def _analyze(self, event: PerceptionEvent) -> PerceptionEvent:
        """分析事件"""
        # 可以在这里添加更复杂的分析逻辑
        # 例如：模式匹配、趋势分析等
        return event

    def _trigger(self, event: PerceptionEvent):
        """触发响应"""
        action = event.data.get('action', 'log')
        handler = self._action_handlers.get(action, self._handle_log)

        try:
            handler(event)
        except Exception as e:
            logger.error(f"Error handling action '{action}': {e}")

    def _handle_immediate_reflection(self, event: PerceptionEvent):
        """处理立即长思考"""
        logger.critical(f"🚨 IMMEDIATE REFLECTION REQUIRED: {event.message}")
        # TODO: 创建长思考任务
        self._log_to_file(event, 'critical')

    def _handle_delayed_reflection(self, event: PerceptionEvent):
        """处理延迟反思"""
        logger.warning(f"⏰ DELAYED REFLECTION SCHEDULED: {event.message}")
        # TODO: 创建延迟反思任务
        self._log_to_file(event, 'high')

    def _handle_daily_summary(self, event: PerceptionEvent):
        """处理每日汇总"""
        logger.info(f"📊 DAILY SUMMARY ITEM: {event.message}")
        self._log_to_file(event, 'medium')

    def _handle_weekly_improvement(self, event: PerceptionEvent):
        """处理周度改进"""
        logger.info(f"📈 WEEKLY IMPROVEMENT ITEM: {event.message}")
        self._log_to_file(event, 'low')

    def _handle_suggest_optimization(self, event: PerceptionEvent):
        """处理优化建议"""
        logger.info(f"💡 OPTIMIZATION SUGGESTION: {event.message}")
        self._log_to_file(event, 'low')

    def _handle_alert(self, event: PerceptionEvent):
        """处理告警"""
        logger.warning(f"🔔 ALERT: {event.message}")
        self._log_to_file(event, 'alert')

    def _handle_log(self, event: PerceptionEvent):
        """仅记录日志"""
        logger.info(f"📋 LOG: [{event.type}:{event.severity}] {event.message}")

    def _log_to_file(self, event: PerceptionEvent, category: str):
        """记录到文件"""
        log_dir = Path.home() / '.openclaw' / 'workspace' / 'logs' / 'perception'
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f'{category}_{datetime.now().strftime("%Y%m")}.log'

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + '\n')


# =============================================================================
# 感知Agent主类
# =============================================================================

class PerceptionAgent:
    """感知Agent主类"""

    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.listeners: Dict[str, BaseListener] = {}
        self.processor = EventProcessor(self.config.get('processor', {}))
        self.running = False
        self._event_count = 0
        self._start_time = None

        self._init_listeners()

    def _load_config(self, config_path: str = None) -> Dict:
        """加载配置文件"""
        if config_path and os.path.exists(config_path):
            if yaml:
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f) or {}
            else:
                logger.warning("PyYAML not installed, using default config")

        # 默认配置
        return self._default_config()

    def _default_config(self) -> Dict:
        """默认配置"""
        workspace = Path.home() / '.openclaw' / 'workspace'

        return {
            'listeners': {
                'log_watcher': {
                    'enabled': True,
                    'files': [
                        str(workspace / 'kanban-react' / 'server.log'),
                        str(workspace / 'logs' / 'kanban_v5.log'),
                        str(workspace / 'logs' / 'cloudflared.log'),
                    ],
                    'patterns': [
                        {'regex': 'ERROR|CRITICAL|FATAL|Exception|Traceback',
                         'severity': 'critical', 'action': 'immediate_reflection'},
                        {'regex': '5\\d{2}',
                         'severity': 'high', 'action': 'delayed_reflection'},
                        {'regex': 'WARNING|Warn',
                         'severity': 'medium', 'action': 'log'},
                    ],
                    'poll_interval': 2
                },
                'error_watcher': {
                    'enabled': True,
                    'sources': ['api_errors', 'database_errors', 'network_errors'],
                    'dedup_window': 3600
                },
                'metric_watcher': {
                    'enabled': True,
                    'metrics': [
                        {'name': 'cpu_usage', 'threshold': 80, 'duration': 300},
                        {'name': 'memory_usage', 'threshold': 85, 'duration': 300},
                    ],
                    'poll_interval': 30
                },
                'behavior_watcher': {
                    'enabled': True,
                    'patterns': [
                        {'name': 'repeated_action', 'window': 300, 'count': 3,
                         'action': 'suggest_optimization'}
                    ]
                }
            },
            'processor': {
                'dedup_window': 300
            }
        }

    def _init_listeners(self):
        """初始化监听器"""
        listeners_config = self.config.get('listeners', {})

        # 日志监听器
        log_config = listeners_config.get('log_watcher', {})
        if log_config.get('enabled', True):
            listener = LogListener(log_config)
            listener.on_event(self._on_event)
            self.listeners['log'] = listener

        # 错误监听器
        error_config = listeners_config.get('error_watcher', {})
        if error_config.get('enabled', True):
            listener = ErrorListener(error_config)
            listener.on_event(self._on_event)
            self.listeners['error'] = listener

        # 指标监听器
        metric_config = listeners_config.get('metric_watcher', {})
        if metric_config.get('enabled', True):
            listener = MetricListener(metric_config)
            listener.on_event(self._on_event)
            self.listeners['metric'] = listener

        # 行为监听器
        behavior_config = listeners_config.get('behavior_watcher', {})
        if behavior_config.get('enabled', True):
            listener = BehaviorListener(behavior_config)
            listener.on_event(self._on_event)
            self.listeners['behavior'] = listener

        # 外部监听器
        external_config = listeners_config.get('external_watcher', {})
        if external_config.get('enabled', False):
            listener = ExternalListener(external_config)
            listener.on_event(self._on_event)
            self.listeners['external'] = listener

    def _on_event(self, event: PerceptionEvent):
        """事件回调"""
        self._event_count += 1
        self.processor.process(event)

    def start(self):
        """启动感知Agent"""
        if self.running:
            return

        self.running = True
        self._start_time = datetime.now()

        for name, listener in self.listeners.items():
            listener.start()

        logger.info(f"🎯 PerceptionAgent started with {len(self.listeners)} listeners")

    def stop(self):
        """停止感知Agent"""
        self.running = False

        for listener in self.listeners.values():
            listener.stop()

        logger.info("🛑 PerceptionAgent stopped")

    def get_status(self) -> Dict:
        """获取Agent状态"""
        uptime = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0

        return {
            'running': self.running,
            'uptime_seconds': int(uptime),
            'event_count': self._event_count,
            'listeners': {
                name: {
                    'enabled': listener.enabled,
                    'running': listener.running
                }
                for name, listener in self.listeners.items()
            }
        }

    def record_api_error(self, *args, **kwargs):
        """记录API错误（供外部调用）"""
        if 'error' in self.listeners:
            self.listeners['error'].record_api_error(*args, **kwargs)

    def record_action(self, *args, **kwargs):
        """记录用户行为（供外部调用）"""
        if 'behavior' in self.listeners:
            self.listeners['behavior'].record_action(*args, **kwargs)


# =============================================================================
# 全局实例
# =============================================================================

_agent: Optional[PerceptionAgent] = None


def init_agent(config_path: str = None) -> PerceptionAgent:
    """初始化感知Agent"""
    global _agent
    if _agent is None:
        _agent = PerceptionAgent(config_path)
    return _agent


def get_agent() -> Optional[PerceptionAgent]:
    """获取感知Agent实例"""
    return _agent


def start_agent(config_path: str = None):
    """启动感知Agent"""
    agent = init_agent(config_path)
    agent.start()
    return agent


def stop_agent():
    """停止感知Agent"""
    global _agent
    if _agent:
        _agent.stop()
        _agent = None


# =============================================================================
# 命令行入口
# =============================================================================

if __name__ == '__main__':
    import signal

    agent = start_agent()

    def signal_handler(sig, frame):
        print('\n正在停止感知Agent...')
        stop_agent()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    print("感知Agent已启动，按 Ctrl+C 停止")

    # 保持运行
    while True:
        time.sleep(1)

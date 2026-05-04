#!/usr/bin/env python3
"""
SDS可观测性Dashboard (Observability Dashboard)
功能：提供系统运行状态的可视化展示和实时监控
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# 添加lib路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from lib.db_connector import get_db_connection, execute_query, execute_update
from config_loader import get_config

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(get_config('paths.logs') + '/sds-dashboard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ObservabilityDashboard')


class MetricsCollector:
    """指标收集器 - 收集系统运行的关键指标"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        """连接数据库"""
        try:
            self.conn = get_db_connection()
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
    
    def collect_task_metrics(self) -> Dict:
        """收集任务相关指标"""
        metrics = {}
        
        # 各状态任务数量
        sql1 = """
            SELECT status, COUNT(*) as count
            FROM tasks
            GROUP BY status
        """
        results1 = execute_query(sql1)
        
        status_counts = {
            'pending': 0,
            'in_progress': 0,
            'completed': 0,
            'failed': 0,
            'archived': 0
        }
        
        for row in results1:
            status = row['status'].lower()
            if status in status_counts:
                status_counts[status] = row['count']
        
        metrics['status_distribution'] = status_counts
        
        # 24小时统计
        sql2 = """
            SELECT 
                SUM(CASE WHEN status = 'completed' AND updated_at >= NOW() - INTERVAL 24 HOUR THEN 1 ELSE 0 END) as completed_24h,
                SUM(CASE WHEN status = 'completed' AND updated_at >= NOW() - INTERVAL 7 DAY THEN 1 ELSE 0 END) as completed_7d,
                SUM(CASE WHEN created_at >= NOW() - INTERVAL 24 HOUR THEN 1 ELSE 0 END) as created_24h,
                SUM(CASE WHEN created_at >= NOW() - INTERVAL 7 DAY THEN 1 ELSE 0 END) as created_7d
            FROM tasks
        """
        results2 = execute_query(sql2)
        if results2:
            metrics['throughput'] = results2[0]
        
        # 自动生成任务统计
        sql3 = """
            SELECT 
                COUNT(*) as total_auto_generated,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as auto_completed,
                SUM(CASE WHEN status IN ('pending', 'in_progress') THEN 1 ELSE 0 END) as auto_active
            FROM tasks
            WHERE task_type = 'auto_generated'
        """
        results3 = execute_query(sql3)
        if results3:
            metrics['auto_generated'] = results3[0]
        
        return metrics
    
    def collect_quality_metrics(self) -> Dict:
        """收集质量指标"""
        metrics = {}
        
        # 任务完成质量
        sql1 = """
            SELECT 
                COUNT(*) as total_completed,
                SUM(CASE WHEN CHAR_LENGTH(task_summary) >= 200 THEN 1 ELSE 0 END) as good_summary,
                SUM(CASE WHEN CHAR_LENGTH(execution_log) >= 200 THEN 1 ELSE 0 END) as good_log,
                SUM(CASE WHEN sds_verified = 1 THEN 1 ELSE 0 END) as sds_verified
            FROM tasks
            WHERE status = 'completed'
        """
        results1 = execute_query(sql1)
        if results1:
            m = results1[0]
            total = m['total_completed'] or 1
            
            metrics['completion_quality'] = {
                'total_completed': m['total_completed'],
                'good_summary_rate': round(m['good_summary'] / total * 100, 2),
                'good_log_rate': round(m['good_log'] / total * 100, 2),
                'sds_verified_rate': round(m['sds_verified'] / total * 100, 2)
            }
        
        # 附件统计
        sql2 = """
            SELECT 
                COUNT(*) as total_attachments,
                COUNT(DISTINCT entity_id) as tasks_with_attachments,
                AVG(size) as avg_size_bytes
            FROM attachments
            WHERE entity_type = 'task'
        """
        results2 = execute_query(sql2)
        if results2:
            metrics['attachments'] = results2[0]
        
        return metrics
    
    def collect_system_metrics(self) -> Dict:
        """收集系统指标"""
        metrics = {}
        
        try:
            import psutil
            
            # CPU
            metrics['cpu'] = {
                'percent': psutil.cpu_percent(interval=0.5),
                'cores': psutil.cpu_count()
            }
            
            # 内存
            mem = psutil.virtual_memory()
            metrics['memory'] = {
                'total_gb': round(mem.total / (1024**3), 2),
                'available_gb': round(mem.available / (1024**3), 2),
                'percent_used': mem.percent
            }
            
            # 磁盘
            disk = psutil.disk_usage('/')
            metrics['disk'] = {
                'total_gb': round(disk.total / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'percent_used': disk.percent
            }
            
            # 日志文件大小
            log_dir = get_config('paths.logs')
            if os.path.exists(log_dir):
                log_size = sum(os.path.getsize(os.path.join(log_dir, f)) 
                              for f in os.listdir(log_dir) 
                              if os.path.isfile(os.path.join(log_dir, f)))
                metrics['logs'] = {
                    'total_size_mb': round(log_size / (1024**2), 2),
                    'file_count': len([f for f in os.listdir(log_dir) if os.path.isfile(os.path.join(log_dir, f))])
                }
        
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
        
        return metrics
    
    def collect_all_metrics(self) -> Dict:
        """收集所有指标"""
        if not self.connect():
            return {'error': '数据库连接失败'}
        
        try:
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'tasks': self.collect_task_metrics(),
                'quality': self.collect_quality_metrics(),
                'system': self.collect_system_metrics()
            }
            
            return metrics
        finally:
            self.close()


class DashboardGenerator:
    """Dashboard生成器 - 生成HTML格式的可视化仪表盘"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
    
    def generate_html_dashboard(self, metrics: Dict) -> str:
        """生成HTML仪表盘"""
        
        status = metrics.get('tasks', {}).get('status_distribution', {})
        throughput = metrics.get('tasks', {}).get('throughput', {})
        quality = metrics.get('quality', {}).get('completion_quality', {})
        system = metrics.get('system', {})
        auto_gen = metrics.get('tasks', {}).get('auto_generated', {})
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SDS 自我驱动系统 - 可观测性仪表盘</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ text-align: center; margin-bottom: 30px; font-size: 2em; }}
        .timestamp {{ text-align: center; color: #8892b0; margin-bottom: 30px; }}
        .grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px; 
            margin-bottom: 30px;
        }}
        .card {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .card h2 {{ 
            font-size: 1.2em; 
            margin-bottom: 20px; 
            color: #64ffda;
            border-bottom: 2px solid rgba(100, 255, 218, 0.3);
            padding-bottom: 10px;
        }}
        .metric {{ margin-bottom: 15px; }}
        .metric-label {{ color: #8892b0; font-size: 0.9em; margin-bottom: 5px; }}
        .metric-value {{ font-size: 1.8em; font-weight: bold; }}
        .metric-bar {{
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            margin-top: 8px;
            overflow: hidden;
        }}
        .metric-bar-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }}
        .status-pending {{ .metric-bar-fill {{ background: #ffd93d; }} }}
        .status-running {{ .metric-bar-fill {{ background: #6bcb77; }} }}
        .status-completed {{ .metric-bar-fill {{ background: #4d96ff; }} }}
        .status-warning {{ .metric-bar-fill {{ background: #ff6b6b; }} }}
        .progress-container {{ margin-top: 10px; }}
        .progress-bar {{
            height: 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            overflow: hidden;
            margin: 5px 0;
        }}
        .progress-fill {{
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 10px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        .health-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }}
        .health-ok {{ background: #6bcb77; }}
        .health-warning {{ background: #ffd93d; }}
        .health-critical {{ background: #ff6b6b; animation: pulse-critical 0.5s infinite; }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.6; }}
        }}
        @keyframes pulse-critical {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.3; }}
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}
        .stat-box {{
            text-align: center;
            padding: 15px;
            background: rgba(100, 255, 218, 0.1);
            border-radius: 10px;
        }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #64ffda; }}
        .stat-label {{ font-size: 0.85em; color: #8892b0; margin-top: 5px; }}
        .large-card {{ grid-column: span 2; }}
        @media (max-width: 768px) {{
            .large-card {{ grid-column: span 1; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 SDS 自我驱动系统 - 可观测性仪表盘</h1>
        <div class="timestamp">最后更新: {metrics.get('timestamp', 'N/A')}</div>
        
        <div class="grid">
            <!-- 任务状态卡片 -->
            <div class="card">
                <h2>📋 任务状态分布</h2>
                <div class="metric status-pending">
                    <div class="metric-label">等待执行 (Pending)</div>
                    <div class="metric-value">{status.get('pending', 0)}</div>
                    <div class="metric-bar">
                        <div class="metric-bar-fill" style="width: {min(status.get('pending', 0) * 5, 100)}%"></div>
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label">执行中 (In Progress)</div>
                    <div class="metric-value">{status.get('in_progress', 0)}</div>
                    <div class="metric-bar">
                        <div class="metric-bar-fill" style="width: {min(status.get('in_progress', 0) * 20, 100)}%; background: #6bcb77;"></div>
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label">已完成 (Completed)</div>
                    <div class="metric-value">{status.get('completed', 0)}</div>
                    <div class="metric-bar">
                        <div class="metric-bar-fill" style="width: {min(status.get('completed', 0), 100)}%; background: #4d96ff;"></div>
                    </div>
                </div>
                <div class="metric status-warning">
                    <div class="metric-label">失败 (Failed)</div>
                    <div class="metric-value">{status.get('failed', 0)}</div>
                </div>
            </div>
            
            <!-- 吞吐量卡片 -->
            <div class="card">
                <h2>📈 任务吞吐量</h2>
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="stat-value">{throughput.get('completed_24h', 0)}</div>
                        <div class="stat-label">24小时完成</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{throughput.get('completed_7d', 0)}</div>
                        <div class="stat-label">7天完成</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{throughput.get('created_24h', 0)}</div>
                        <div class="stat-label">24小时新建</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{throughput.get('created_7d', 0)}</div>
                        <div class="stat-label">7天新建</div>
                    </div>
                </div>
            </div>
            
            <!-- 自动生成任务 -->
            <div class="card">
                <h2>🤖 自动生成任务</h2>
                <div class="metric">
                    <div class="metric-label">总生成数</div>
                    <div class="metric-value">{auto_gen.get('total_auto_generated', 0)}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">已完成</div>
                    <div class="metric-value">{auto_gen.get('auto_completed', 0)}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">活跃中</div>
                    <div class="metric-value">{auto_gen.get('auto_active', 0)}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">自动生成率</div>
                    <div class="metric-value">{round(auto_gen.get('total_auto_generated', 0) / max(status.get('completed', 0) + status.get('pending', 0), 1) * 100, 1)}%</div>
                </div>
            </div>
            
            <!-- 质量指标 -->
            <div class="card">
                <h2>✅ 完成质量</h2>
                <div class="progress-container">
                    <div class="metric-label">Task Summary 达标率 (≥500字)</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {quality.get('good_summary_rate', 0)}%; background: linear-gradient(90deg, #4d96ff, #64ffda);">
                            {quality.get('good_summary_rate', 0)}%
                        </div>
                    </div>
                </div>
                <div class="progress-container">
                    <div class="metric-label">Execution Log 达标率 (≥200字)</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {quality.get('good_log_rate', 0)}%; background: linear-gradient(90deg, #4d96ff, #64ffda);">
                            {quality.get('good_log_rate', 0)}%
                        </div>
                    </div>
                </div>
                <div class="progress-container">
                    <div class="metric-label">SDS 验证通过率</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {quality.get('sds_verified_rate', 0)}%; background: linear-gradient(90deg, #4d96ff, #64ffda);">
                            {quality.get('sds_verified_rate', 0)}%
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 系统资源 -->
            <div class="card large-card">
                <h2>💻 系统资源监控</h2>
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="health-indicator {'health-ok' if system.get('cpu', {}).get('percent', 0) < 70 else 'health-warning' if system.get('cpu', {}).get('percent', 0) < 90 else 'health-critical'}"></div>
                        <span class="metric-label">CPU</span>
                        <div class="stat-value">{system.get('cpu', {}).get('percent', 0)}%</div>
                    </div>
                    <div class="stat-box">
                        <div class="health-indicator {'health-ok' if system.get('memory', {}).get('percent_used', 0) < 70 else 'health-warning' if system.get('memory', {}).get('percent_used', 0) < 85 else 'health-critical'}"></div>
                        <span class="metric-label">内存</span>
                        <div class="stat-value">{system.get('memory', {}).get('percent_used', 0)}%</div>
                        <div class="metric-label">{system.get('memory', {}).get('available_gb', 0)}GB 可用</div>
                    </div>
                    <div class="stat-box">
                        <div class="health-indicator {'health-ok' if system.get('disk', {}).get('percent_used', 0) < 75 else 'health-warning' if system.get('disk', {}).get('percent_used', 0) < 85 else 'health-critical'}"></div>
                        <span class="metric-label">磁盘</span>
                        <div class="stat-value">{system.get('disk', {}).get('percent_used', 0)}%</div>
                        <div class="metric-label">{system.get('disk', {}).get('free_gb', 0)}GB 可用</div>
                    </div>
                    <div class="stat-box">
                        <div class="metric-label">日志文件</div>
                        <div class="stat-value">{system.get('logs', {}).get('total_size_mb', 0)}MB</div>
                        <div class="metric-label">{system.get('logs', {}).get('file_count', 0)} 个文件</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div style="text-align: center; color: #8892b0; padding: 20px;">
            SDS 自我驱动系统 v1.0 | 自动监控 · 智能调度 · 持续优化
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    def generate_markdown_report(self, metrics: Dict) -> str:
        """生成Markdown格式的报告"""
        
        status = metrics.get('tasks', {}).get('status_distribution', {})
        throughput = metrics.get('tasks', {}).get('throughput', {})
        quality = metrics.get('quality', {}).get('completion_quality', {})
        system = metrics.get('system', {})
        auto_gen = metrics.get('tasks', {}).get('auto_generated', {})
        
        md = f"""# SDS 自我驱动系统 - 状态报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 任务概览

| 状态 | 数量 |
|------|------|
| 🟡 等待执行 | {status.get('pending', 0)} |
| 🟢 执行中 | {status.get('in_progress', 0)} |
| 🔵 已完成 | {status.get('completed', 0)} |
| 🔴 失败 | {status.get('failed', 0)} |

## 📈 吞吐量统计

| 时间范围 | 完成数 | 新建数 |
|----------|--------|--------|
| 24小时 | {throughput.get('completed_24h', 0)} | {throughput.get('created_24h', 0)} |
| 7天 | {throughput.get('completed_7d', 0)} | {throughput.get('created_7d', 0)} |

## 🤖 自动任务生成

- **总生成数**: {auto_gen.get('total_auto_generated', 0)}
- **已完成**: {auto_gen.get('auto_completed', 0)}
- **活跃中**: {auto_gen.get('auto_active', 0)}

## ✅ 完成质量

- **Task Summary 达标率**: {quality.get('good_summary_rate', 0)}%
- **Execution Log 达标率**: {quality.get('good_log_rate', 0)}%
- **SDS 验证通过率**: {quality.get('sds_verified_rate', 0)}%

## 💻 系统资源

- **CPU**: {system.get('cpu', {}).get('percent', 0)}%
- **内存**: {system.get('memory', {}).get('percent_used', 0)}% ({system.get('memory', {}).get('available_gb', 0)}GB 可用)
- **磁盘**: {system.get('disk', {}).get('percent_used', 0)}% ({system.get('disk', {}).get('free_gb', 0)}GB 可用)
- **日志大小**: {system.get('logs', {}).get('total_size_mb', 0)}MB

---

*本报告由 SDS 可观测性系统自动生成*
"""
        
        return md
    
    def update_dashboard(self) -> Dict:
        """更新仪表盘"""
        logger.info("更新可观测性仪表盘...")
        
        # 收集指标
        metrics = self.metrics_collector.collect_all_metrics()
        
        if 'error' in metrics:
            return metrics
        
        # 生成HTML仪表盘
        html = self.generate_html_dashboard(metrics)
        html_file = Path(get_config('paths.output') + "/task-1570/sds-dashboard.html")
        html_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(html_file, 'w') as f:
            f.write(html)
        
        logger.info(f"HTML仪表盘已更新: {html_file}")
        
        # 生成Markdown报告
        md = self.generate_markdown_report(metrics)
        md_file = Path(get_config('paths.output') + "/task-1570/sds-status-report.md")
        
        with open(md_file, 'w') as f:
            f.write(md)
        
        logger.info(f"Markdown报告已更新: {md_file}")
        
        # 保存原始指标数据 - 处理Decimal类型
        def decimal_default(obj):
            if hasattr(obj, '__class__') and obj.__class__.__name__ == 'Decimal':
                return float(obj)
            if hasattr(obj, 'isoformat'):  # datetime对象
                return obj.isoformat()
            raise TypeError
        
        metrics_file = Path(get_config('paths.logs') + "/sds-metrics-latest.json")
        
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False, default=decimal_default)
        
        return {
            'success': True,
            'html_file': str(html_file),
            'md_file': str(md_file),
            'metrics_file': str(metrics_file)
        }


if __name__ == "__main__":
    dashboard = DashboardGenerator()
    result = dashboard.update_dashboard()
    print(json.dumps(result, indent=2, ensure_ascii=False))

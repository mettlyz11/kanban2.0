#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS任务生成频率监控脚本 V4.3

【任务#2110】T1: AI助手优化 - 调度系统频率限制与去重机制升级

功能：
1. 实时监控任务生成速率
2. 检测异常高频生成并报警
3. 生成频率统计报告
4. 历史趋势分析

升级日期: 2026-04-27
版本: V4.3.0
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from lib.db_connector import execute_query

# 日志配置
LOG_DIR = Path("/Users/mettlyz/.openclaw/workspace/logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'sds-task-generation-monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TaskGenerationMonitor')


# ============================================================================
# 监控配置
# ============================================================================

class MonitorConfig:
    """监控配置"""
    # 阈值配置
    ALERT_THRESHOLD_PER_HOUR = 5      # 每小时超过5个任务报警
    WARNING_THRESHOLD_PER_HOUR = 3     # 每小时超过3个任务警告
    MAX_TASKS_PER_GOAL_PER_DAY = 2     # 每目标每天最多2个任务
    MAX_PENDING_PER_GOAL = 3            # 每目标最多3个pending任务
    
    # 时间范围
    DEFAULT_LOOKBACK_HOURS = 24
    
    # 报警级别
    ALERT_LEVELS = {
        'info': {'icon': 'ℹ️', 'color': 'blue'},
        'warning': {'icon': '⚠️', 'color': 'yellow'},
        'critical': {'icon': '🔴', 'color': 'red'}
    }


# ============================================================================
# 数据采集器
# ============================================================================

class TaskDataCollector:
    """任务数据采集器"""
    
    def __init__(self):
        self.cache = {}
        self.cache_time = None
    
    def get_task_generation_stats(self, hours: int = 24) -> Dict:
        """获取任务生成统计"""
        window_start = datetime.now() - timedelta(hours=hours)
        
        # 1. 总体统计
        sql_overall = """
            SELECT 
                COUNT(*) as total_tasks,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress_count,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                MIN(created_at) as earliest_time,
                MAX(created_at) as latest_time
            FROM tasks
            WHERE task_type LIKE 'auto_generated%%'
              AND created_at >= %s
        """
        
        result = execute_query(sql_overall, (window_start,))
        overall = result[0] if result else {}
        
        # 2. 按目标分组统计
        sql_by_goal = """
            SELECT 
                goal_id,
                COUNT(*) as total_tasks,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count,
                MIN(created_at) as earliest_time,
                MAX(created_at) as latest_time
            FROM tasks
            WHERE task_type LIKE 'auto_generated%%'
              AND created_at >= %s
            GROUP BY goal_id
            ORDER BY total_tasks DESC
        """
        
        by_goal = execute_query(sql_by_goal, (window_start,)) or []
        
        # 3. 每小时生成速率
        sql_hourly = """
            SELECT 
                DATE_FORMAT(created_at, '%%Y-%%m-%%d %%H:00') as hour,
                goal_id,
                COUNT(*) as count
            FROM tasks
            WHERE task_type LIKE 'auto_generated%%'
              AND created_at >= %s
            GROUP BY hour, goal_id
            ORDER BY hour, goal_id
        """
        
        hourly_data = execute_query(sql_hourly, (window_start,)) or []
        
        # 整理小时数据
        hourly_by_goal = defaultdict(lambda: defaultdict(int))
        hourly_total = defaultdict(int)
        for item in hourly_data:
            hour = item['hour']
            goal_id = item['goal_id'] or 0
            count = item['count']
            hourly_by_goal[hour][goal_id] = count
            hourly_total[hour] += count
        
        # 4. 重复任务检测
        sql_duplicates = """
            SELECT 
                LEFT(title, 15) as prefix,
                goal_id,
                COUNT(*) as dup_count,
                GROUP_CONCAT(id ORDER BY created_at SEPARATOR ', ') as task_ids,
                MIN(created_at) as first_created,
                MAX(created_at) as last_created
            FROM tasks
            WHERE status IN ('pending', 'in_progress', 'completed')
              AND created_at >= %s
            GROUP BY prefix, goal_id
            HAVING dup_count > 1
            ORDER BY dup_count DESC
            LIMIT 50
        """
        
        duplicates = execute_query(sql_duplicates, (window_start,)) or []
        
        return {
            'timestamp': datetime.now().isoformat(),
            'lookback_hours': hours,
            'window_start': window_start.isoformat(),
            'overall': overall,
            'by_goal': by_goal,
            'hourly': {
                'by_goal': dict(hourly_by_goal),
                'total': dict(hourly_total)
            },
            'duplicates': duplicates
        }
    
    def get_pending_watermark(self) -> Dict:
        """获取pending水位现状"""
        sql = """
            SELECT 
                goal_id,
                COUNT(*) as pending_count,
                GROUP_CONCAT(id SEPARATOR ', ') as task_ids,
                GROUP_CONCAT(title SEPARATOR ' || ') as titles
            FROM tasks
            WHERE status = 'pending'
            GROUP BY goal_id
            ORDER BY pending_count DESC
        """
        
        results = execute_query(sql) or []
        
        return {
            'timestamp': datetime.now().isoformat(),
            'pending_by_goal': results,
            'total_pending': sum(r['pending_count'] for r in results)
        }


# ============================================================================
# 警报检测器
# ============================================================================

class AlertDetector:
    """警报检测器"""
    
    def __init__(self, config: MonitorConfig = None):
        self.config = config or MonitorConfig()
        self.alerts = []
    
    def detect_all(self, stats: Dict, watermark: Dict) -> List[Dict]:
        """执行所有检测"""
        self.alerts = []
        
        # 1. 检测每小时频率异常
        self._detect_hourly_spikes(stats)
        
        # 2. 检测每目标日频率异常
        self._detect_goal_daily_exceed(stats)
        
        # 3. 检测pending水位异常
        self._detect_pending_watermark(watermark)
        
        # 4. 检测重复任务
        self._detect_duplicates(stats)
        
        # 按严重程度排序
        severity_order = {'critical': 0, 'warning': 1, 'info': 2}
        self.alerts.sort(key=lambda x: severity_order.get(x['level'], 99))
        
        return self.alerts
    
    def _add_alert(self, level: str, category: str, message: str, details: Dict = None):
        """添加警报"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'category': category,
            'message': message,
            'details': details or {},
            'icon': self.config.ALERT_LEVELS[level]['icon']
        }
        self.alerts.append(alert)
        logger.warning(f"{alert['icon']} [{level.upper()}] {category}: {message}")
    
    def _detect_hourly_spikes(self, stats: Dict):
        """检测每小时频率峰值"""
        hourly = stats.get('hourly', {}).get('total', {})
        
        for hour, count in hourly.items():
            if count >= self.config.ALERT_THRESHOLD_PER_HOUR:
                self._add_alert(
                    'critical',
                    'hourly_spike',
                    f"{hour} 生成了 {count} 个任务，超过警戒阈值 {self.config.ALERT_THRESHOLD_PER_HOUR}",
                    {'hour': hour, 'count': count, 'threshold': self.config.ALERT_THRESHOLD_PER_HOUR}
                )
            elif count >= self.config.WARNING_THRESHOLD_PER_HOUR:
                self._add_alert(
                    'warning',
                    'hourly_spike',
                    f"{hour} 生成了 {count} 个任务，超过警告阈值 {self.config.WARNING_THRESHOLD_PER_HOUR}",
                    {'hour': hour, 'count': count, 'threshold': self.config.WARNING_THRESHOLD_PER_HOUR}
                )
    
    def _detect_goal_daily_exceed(self, stats: Dict):
        """检测每目标日频率超限"""
        by_goal = stats.get('by_goal', [])
        
        for goal in by_goal:
            goal_id = goal['goal_id']
            count = goal['total_tasks']
            if count > self.config.MAX_TASKS_PER_GOAL_PER_DAY:
                self._add_alert(
                    'critical',
                    'goal_rate_exceed',
                    f"目标{goal_id} 过去{stats.get('lookback_hours', 24)}小时生成了 {count} 个任务，超过上限 {self.config.MAX_TASKS_PER_GOAL_PER_DAY}",
                    {'goal_id': goal_id, 'count': count, 'threshold': self.config.MAX_TASKS_PER_GOAL_PER_DAY}
                )
    
    def _detect_pending_watermark(self, watermark: Dict):
        """检测pending水位超限"""
        pending_by_goal = watermark.get('pending_by_goal', [])
        
        for item in pending_by_goal:
            goal_id = item['goal_id']
            count = item['pending_count']
            if count > self.config.MAX_PENDING_PER_GOAL:
                self._add_alert(
                    'warning',
                    'pending_watermark',
                    f"目标{goal_id} 当前有 {count} 个pending任务，超过水位线 {self.config.MAX_PENDING_PER_GOAL}",
                    {'goal_id': goal_id, 'count': count, 'threshold': self.config.MAX_PENDING_PER_GOAL}
                )
    
    def _detect_duplicates(self, stats: Dict):
        """检测重复任务"""
        duplicates = stats.get('duplicates', [])
        
        for dup in duplicates[:10]:  # 最多报告10个
            prefix = dup['prefix']
            goal_id = dup['goal_id']
            count = dup['dup_count']
            
            if count >= 5:
                level = 'critical'
            elif count >= 3:
                level = 'warning'
            else:
                level = 'info'
            
            self._add_alert(
                level,
                'duplicate_tasks',
                f"发现 {count} 个重复任务，前缀: '{prefix}' (目标{goal_id})",
                {
                    'prefix': prefix,
                    'goal_id': goal_id,
                    'count': count,
                    'task_ids': dup.get('task_ids', '')
                }
            )


# ============================================================================
# 报告生成器
# ============================================================================

class ReportGenerator:
    """报告生成器"""
    
    @staticmethod
    def generate_text_report(stats: Dict, watermark: Dict, alerts: List[Dict]) -> str:
        """生成文本报告"""
        lines = []
        
        # 标题
        lines.append("="*70)
        lines.append("  SDS任务生成频率监控报告 V4.3")
        lines.append("="*70)
        lines.append(f"生成时间: {stats.get('timestamp', 'N/A')}")
        lines.append(f"统计范围: 过去{stats.get('lookback_hours', 24)}小时")
        lines.append("")
        
        # 总体统计
        overall = stats.get('overall', {})
        lines.append("【总体统计】")
        lines.append(f"  总生成任务数: {overall.get('total_tasks', 0)}")
        lines.append(f"  Pending: {overall.get('pending_count', 0)}")
        lines.append(f"  In Progress: {overall.get('in_progress_count', 0)}")
        lines.append(f"  Completed: {overall.get('completed_count', 0)}")
        lines.append(f"  Failed: {overall.get('failed_count', 0)}")
        if overall.get('total_tasks', 0) > 0:
            rate = overall.get('total_tasks', 0) / stats.get('lookback_hours', 24)
            lines.append(f"  平均每小时: {rate:.2f} 个任务")
        lines.append("")
        
        # 按目标统计
        lines.append("【按目标统计】")
        by_goal = stats.get('by_goal', [])
        for goal in by_goal:
            goal_id = goal['goal_id'] or '未设置'
            lines.append(f"  目标{goal_id}:")
            lines.append(f"    生成总数: {goal['total_tasks']}")
            lines.append(f"    Pending: {goal['pending_count']}")
            lines.append(f"    Completed: {goal['completed_count']}")
            lines.append(f"    时间范围: {goal.get('earliest_time', 'N/A')} ~ {goal.get('latest_time', 'N/A')}")
        lines.append("")
        
        # 每小时速率（可视化）
        lines.append("【每小时生成速率】")
        hourly = stats.get('hourly', {}).get('total', {})
        hours = sorted(hourly.keys())
        max_count = max(hourly.values()) if hourly else 1
        
        for hour in hours:
            count = hourly[hour]
            bar_length = int((count / max_count) * 30)
            bar = '█' * bar_length
            lines.append(f"  {hour}: {count:3} {bar}")
        lines.append("")
        
        # Pending水位
        lines.append("【Pending水位现状】")
        lines.append(f"  总Pending: {watermark.get('total_pending', 0)}")
        for item in watermark.get('pending_by_goal', []):
            goal_id = item['goal_id']
            count = item['pending_count']
            status = '✅' if count <= MonitorConfig.MAX_PENDING_PER_GOAL else '⚠️'
            lines.append(f"  {status} 目标{goal_id}: {count} 个pending (上限{MonitorConfig.MAX_PENDING_PER_GOAL})")
        lines.append("")
        
        # 警报
        lines.append("【警报信息】")
        if alerts:
            for alert in alerts:
                lines.append(f"  {alert['icon']} [{alert['level'].upper()}] {alert['category']}")
                lines.append(f"     {alert['message']}")
        else:
            lines.append("  ✅ 系统运行正常，无警报")
        lines.append("")
        
        # 重复任务
        lines.append("【重复任务检测】")
        duplicates = stats.get('duplicates', [])
        if duplicates:
            lines.append(f"  发现 {len(duplicates)} 组重复任务:")
            for dup in duplicates[:10]:
                lines.append(f"    - '{dup['prefix']}' (目标{dup['goal_id']}): {dup['dup_count']}个重复")
        else:
            lines.append("  ✅ 未发现重复任务")
        lines.append("")
        
        lines.append("="*70)
        
        return '\n'.join(lines)
    
    @staticmethod
    def generate_json_report(stats: Dict, watermark: Dict, alerts: List[Dict]) -> Dict:
        """生成JSON报告"""
        return {
            'version': 'V4.3',
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_tasks': stats.get('overall', {}).get('total_tasks', 0),
                'total_pending': watermark.get('total_pending', 0),
                'alert_count': len(alerts),
                'critical_count': sum(1 for a in alerts if a['level'] == 'critical'),
                'warning_count': sum(1 for a in alerts if a['level'] == 'warning'),
                'duplicate_groups': len(stats.get('duplicates', []))
            },
            'stats': stats,
            'watermark': watermark,
            'alerts': alerts
        }
    
    @staticmethod
    def save_report(report: str, json_data: Dict, output_dir: str = None):
        """保存报告到文件"""
        if output_dir is None:
            output_dir = LOG_DIR
        
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        
        # 保存文本报告
        text_file = os.path.join(output_dir, f'sds-monitor-report-{timestamp}.txt')
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # 保存JSON报告
        json_file = os.path.join(output_dir, f'sds-monitor-report-{timestamp}.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"报告已保存: {text_file}")
        logger.info(f"JSON数据已保存: {json_file}")
        
        return text_file, json_file


# ============================================================================
# 监控器主类
# ============================================================================

class TaskGenerationMonitor:
    """任务生成监控器"""
    
    def __init__(self, lookback_hours: int = 24):
        self.lookback_hours = lookback_hours
        self.collector = TaskDataCollector()
        self.detector = AlertDetector()
        self.reporter = ReportGenerator()
        
        logger.info(f"TaskGenerationMonitor V4.3 initialized, lookback={lookback_hours}h")
    
    def run_check(self, save_report: bool = True) -> Tuple[str, Dict]:
        """运行一次完整检查"""
        logger.info("开始执行监控检查...")
        
        # 1. 采集数据
        stats = self.collector.get_task_generation_stats(self.lookback_hours)
        watermark = self.collector.get_pending_watermark()
        
        # 2. 检测警报
        alerts = self.detector.detect_all(stats, watermark)
        
        # 3. 生成报告
        text_report = self.reporter.generate_text_report(stats, watermark, alerts)
        json_report = self.reporter.generate_json_report(stats, watermark, alerts)
        
        # 4. 保存报告
        if save_report:
            self.reporter.save_report(text_report, json_report)
        
        logger.info(f"监控检查完成, 发现 {len(alerts)} 个警报")
        
        return text_report, json_report
    
    def print_summary(self, json_report: Dict):
        """打印摘要"""
        summary = json_report['summary']
        
        print("\n" + "="*70)
        print("  监控摘要")
        print("="*70)
        print(f"  总生成任务: {summary['total_tasks']}")
        print(f"  总Pending: {summary['total_pending']}")
        print(f"  警报数量: {summary['alert_count']}")
        if summary['alert_count'] > 0:
            print(f"    - Critical: {summary['critical_count']}")
            print(f"    - Warning: {summary['warning_count']}")
        print(f"  重复任务组: {summary['duplicate_groups']}")
        print("="*70)


# ============================================================================
# 便捷函数
# ============================================================================

def run_monitor_check(lookback_hours: int = 24, output_dir: str = None) -> Tuple[str, Dict]:
    """便捷函数：运行一次监控检查"""
    monitor = TaskGenerationMonitor(lookback_hours)
    text_report, json_report = monitor.run_check(save_report=True)
    monitor.print_summary(json_report)
    return text_report, json_report


def get_current_status() -> Dict:
    """获取当前系统状态"""
    monitor = TaskGenerationMonitor()
    _, json_report = monitor.run_check(save_report=False)
    return json_report


# ============================================================================
# 主程序入口
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='SDS任务生成频率监控 V4.3')
    parser.add_argument('--hours', type=int, default=24, help='统计过去N小时的数据')
    parser.add_argument('--no-save', action='store_true', help='不保存报告文件')
    parser.add_argument('--json-only', action='store_true', help='只输出JSON')
    
    args = parser.parse_args()
    
    monitor = TaskGenerationMonitor(lookback_hours=args.hours)
    text_report, json_report = monitor.run_check(save_report=not args.no_save)
    
    if args.json_only:
        print(json.dumps(json_report, indent=2, ensure_ascii=False))
    else:
        print(text_report)
        monitor.print_summary(json_report)

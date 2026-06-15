#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS任务频率监控脚本 - 任务 #2110交付物

功能：
1. 实时监控各目标任务生成频率
2. 生成每日频率报告
3. 发现异常高频生成并告警
4. 去重效果统计
5. 导出CSV/JSON报告

使用方式：
  python task_frequency_monitor.py                   # 默认24小时报告
  python task_frequency_monitor.py --hours 72        # 72小时报告
  python task_frequency_monitor.py --alerts          # 告警模式
  python task_frequency_monitor.py --export csv      # 导出CSV
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json
import csv
import argparse

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from lib.db_connector import execute_query

# 配置
REPORT_DIR = Path("/Users/mettlyz/.openclaw/workspace/output/task-2110/reports")
REPORT_DIR.mkdir(exist_ok=True, parents=True)

# 告警阈值
ALERT_RATE_THRESHOLD = 3  # 24小时超过3个任务告警
ALERT_PENDING_THRESHOLD = 4  # pending超过4个告警


class TaskFrequencyMonitor:
    """任务频率监控器"""
    
    def __init__(self):
        self.goal_names = {
            1: '法务纠纷处理',
            2: '和光智成商业化',
            3: '学术影响力建设',
            4: 'AI助手优化',
            5: '数据库治理',
            6: '产品与渠道',
            7: '团队与组织'
        }
    
    def get_task_stats(self, hours: int) -> Dict:
        """获取指定时间范围内的任务统计"""
        window_start = datetime.now() - timedelta(hours=hours)
        
        # 基础统计
        sql = """
            SELECT
                goal_id,
                COUNT(*) as total_tasks,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress_count,
                SUM(CASE WHEN task_type LIKE 'auto_generated%%' THEN 1 ELSE 0 END) as auto_generated_count,
                MIN(created_at) as first_task_time,
                MAX(created_at) as last_task_time
            FROM tasks
            WHERE created_at >= %s
            GROUP BY goal_id
            ORDER BY goal_id
        """
        results = execute_query(sql, (window_start,)) or []
        
        stats = {
            'period_hours': hours,
            'window_start': window_start.isoformat(),
            'report_time': datetime.now().isoformat(),
            'total_all_goals': sum(r['total_tasks'] for r in results),
            'total_auto_generated': sum(r['auto_generated_count'] for r in results),
            'by_goal': {},
            'alerts': []
        }
        
        for row in results:
            goal_id = row['goal_id']
            if goal_id is None:
                goal_id = 0
            
            total = row['total_tasks']
            pending = row['pending_count']
            auto_count = row['auto_generated_count']
            
            # 计算每小时生成率
            first_time = row['first_task_time']
            last_time = row['last_task_time']
            hourly_rate = 0.0
            if first_time and last_time and first_time != last_time:
                duration_hours = (last_time - first_time).total_seconds() / 3600
                if duration_hours > 0:
                    hourly_rate = total / max(duration_hours, 1)
            
            goal_stats = {
                'goal_id': goal_id,
                'goal_name': self.goal_names.get(goal_id, f'目标{goal_id}' if goal_id != 0 else '未分类'),
                'total_tasks': total,
                'pending_count': pending,
                'completed_count': row['completed_count'],
                'in_progress_count': row['in_progress_count'],
                'auto_generated_count': auto_count,
                'completion_rate': row['completed_count'] / max(total, 1),
                'hourly_rate': round(hourly_rate, 3),
                'first_task_time': str(first_time) if first_time else None,
                'last_task_time': str(last_time) if last_time else None
            }
            
            stats['by_goal'][goal_id] = goal_stats
            
            # 检查告警
            if auto_count > ALERT_RATE_THRESHOLD:
                stats['alerts'].append({
                    'type': 'HIGH_FREQUENCY',
                    'goal_id': goal_id,
                    'goal_name': goal_stats['goal_name'],
                    'message': f"自动生成任务过高: {auto_count}个任务 (阈值={ALERT_RATE_THRESHOLD})",
                    'severity': 'WARNING' if auto_count <= 5 else 'CRITICAL'
                })
            
            if pending > ALERT_PENDING_THRESHOLD:
                stats['alerts'].append({
                    'type': 'HIGH_PENDING',
                    'goal_id': goal_id,
                    'goal_name': goal_stats['goal_name'],
                    'message': f"Pending任务过多: {pending}个 (阈值={ALERT_PENDING_THRESHOLD})",
                    'severity': 'WARNING' if pending <= 6 else 'CRITICAL'
                })
        
        return stats
    
    def get_duplicate_analysis(self, hours: int) -> Dict:
        """分析重复任务"""
        window_start = datetime.now() - timedelta(hours=hours)
        
        # 检查前缀重复（15字）
        sql = """
            SELECT
                LEFT(title, 15) as prefix,
                COUNT(*) as duplicate_count,
                GROUP_CONCAT(id SEPARATOR ', ') as task_ids,
                GROUP_CONCAT(status SEPARATOR ', ') as statuses
            FROM tasks
            WHERE created_at >= %s
            GROUP BY prefix
            HAVING duplicate_count > 1
            ORDER BY duplicate_count DESC
            LIMIT 20
        """
        duplicates = execute_query(sql, (window_start,)) or []
        
        return {
            'period_hours': hours,
            'total_duplicate_groups': len(duplicates),
            'total_duplicate_tasks': sum(d['duplicate_count'] for d in duplicates),
            'duplicate_groups': [
                {
                    'prefix': d['prefix'],
                    'count': d['duplicate_count'],
                    'task_ids': d['task_ids'],
                    'statuses': d['statuses']
                }
                for d in duplicates
            ]
        }
    
    def get_hourly_trend(self, hours: int) -> List[Dict]:
        """获取每小时任务生成趋势"""
        sql = """
            SELECT
                DATE_FORMAT(created_at, '%%Y-%%m-%%d %%H:00:00') as hour,
                goal_id,
                COUNT(*) as task_count
            FROM tasks
            WHERE created_at >= NOW() - INTERVAL %s HOUR
            GROUP BY hour, goal_id
            ORDER BY hour DESC, goal_id
        """
        results = execute_query(sql, (hours,)) or []
        
        trend = {}
        for row in results:
            hour = row['hour']
            if hour not in trend:
                trend[hour] = {}
            goal_id = row['goal_id'] or 0
            trend[hour][goal_id] = row['task_count']
        
        return [{'hour': hour, 'by_goal': goals} for hour, goals in trend.items()]
    
    def generate_report(self, hours: int = 24) -> str:
        """生成文本报告"""
        stats = self.get_task_stats(hours)
        dup_analysis = self.get_duplicate_analysis(hours)
        trend = self.get_hourly_trend(hours)
        
        lines = []
        lines.append("=" * 80)
        lines.append(f"  SDS任务频率监控报告 - 过去{hours}小时")
        lines.append(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        
        # 概览
        lines.append("\n【概览】")
        lines.append(f"  总任务数: {stats['total_all_goals']}")
        lines.append(f"  自动生成: {stats['total_auto_generated']}")
        lines.append(f"  涉及目标数: {len(stats['by_goal'])}")
        
        # 告警
        if stats['alerts']:
            lines.append("\n【⚠️ 告警】")
            for alert in stats['alerts']:
                icon = '🔴' if alert['severity'] == 'CRITICAL' else '🟡'
                lines.append(f"  {icon} [{alert['type']}] {alert['goal_name']}: {alert['message']}")
        else:
            lines.append("\n【✅ 无告警】")
        
        # 各目标详细统计
        lines.append("\n【各目标详细统计】")
        lines.append(f"  {'目标名称':<15} {'总数':>6} {'自动':>6} {'待处理':>6} {'已完成':>6} {'完成率':>8} {'小时率':>8}")
        lines.append("  " + "-" * 70)
        
        for gid in sorted(stats['by_goal'].keys()):
            g = stats['by_goal'][gid]
            lines.append(
                f"  {g['goal_name']:<15} "
                f"{g['total_tasks']:>6} "
                f"{g['auto_generated_count']:>6} "
                f"{g['pending_count']:>6} "
                f"{g['completed_count']:>6} "
                f"{g['completion_rate']:>7.1%} "
                f"{g['hourly_rate']:>7.2f}"
            )
        
        # 重复任务分析
        lines.append("\n【重复任务分析（前缀15字）】")
        if dup_analysis['duplicate_groups']:
            lines.append(f"  发现 {dup_analysis['total_duplicate_groups']} 组重复，共 {dup_analysis['total_duplicate_tasks']} 个任务")
            for dup in dup_analysis['duplicate_groups'][:5]:
                lines.append(f"    \"{dup['prefix']}...\" 出现 {dup['count']} 次 (任务ID: {dup['task_ids']})")
        else:
            lines.append("  ✅ 未发现明显重复任务")
        
        # 最近趋势（前6小时）
        lines.append("\n【最近6小时趋势】")
        for hour_data in trend[:6]:
            hour = hour_data['hour'][11:16]  # 只保留时间部分
            total = sum(hour_data['by_goal'].values())
            lines.append(f"  {hour}: {total}个任务")
        
        lines.append("\n" + "=" * 80)
        
        return '\n'.join(lines)
    
    def export_json(self, hours: int, filename: str = None):
        """导出JSON报告"""
        if not filename:
            filename = REPORT_DIR / f"frequency_report_{hours}h_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'stats': self.get_task_stats(hours),
            'duplicate_analysis': self.get_duplicate_analysis(hours),
            'hourly_trend': self.get_hourly_trend(hours)
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # print(f"✅ JSON报告已导出: {filename}")
        return filename
    
    def export_csv(self, hours: int, filename: str = None):
        """导出CSV报告"""
        if not filename:
            filename = REPORT_DIR / f"frequency_report_{hours}h_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        stats = self.get_task_stats(hours)
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['目标ID', '目标名称', '总任务数', '自动生成', '待处理', '已完成', '进行中', '完成率', '每小时生成率'])
            
            for gid, g in stats['by_goal'].items():
                writer.writerow([
                    gid,
                    g['goal_name'],
                    g['total_tasks'],
                    g['auto_generated_count'],
                    g['pending_count'],
                    g['completed_count'],
                    g['in_progress_count'],
                    f"{g['completion_rate']:.1%}",
                    g['hourly_rate']
                ])
        
        # print(f"✅ CSV报告已导出: {filename}")
        return filename
    
    def run_alerts_check(self) -> bool:
        """运行告警检查，返回是否有告警"""
        stats = self.get_task_stats(24)
        
        if stats['alerts']:
            # print("⚠️ 发现告警:")
            for alert in stats['alerts']:
                # print(f"  - {alert['message']}")
            return True
        else:
            # print("✅ 无告警")
            return False


def main():
    parser = argparse.ArgumentParser(description='SDS任务频率监控工具')
    parser.add_argument('--hours', type=int, default=24, help='监控时间范围（小时）')
    parser.add_argument('--alerts', action='store_true', help='只检查告警')
    parser.add_argument('--export', choices=['json', 'csv', 'both'], help='导出报告格式')
    parser.add_argument('--no-print', action='store_true', help='不打印文本报告')
    
    args = parser.parse_args()
    
    monitor = TaskFrequencyMonitor()
    
    if args.alerts:
        has_alerts = monitor.run_alerts_check()
        sys.exit(1 if has_alerts else 0)
    
    if not args.no_print:
        report = monitor.generate_report(args.hours)
        # print(report)
    
    if args.export in ['json', 'both']:
        monitor.export_json(args.hours)
    
    if args.export in ['csv', 'both']:
        monitor.export_csv(args.hours)


if __name__ == "__main__":
    main()

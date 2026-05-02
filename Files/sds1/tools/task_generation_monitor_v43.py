#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务生成频率监控脚本 - SDS v4.3
功能：
1. 实时监控各目标的任务生成频率
2. 检测异常的任务生成模式
3. 生成频率统计报告
4. 发送告警通知

任务: #2110 - 调度系统频率限制与去重机制升级
创建日期: 2026-04-28
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.db_connector import get_db_connection, execute_query, execute_update
from core.task_generation_guard_v43 import TaskGenerationGuardV43
from config_loader import get_config

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger('FrequencyMonitor')


class TaskGenerationMonitor:
    """任务生成频率监控器"""
    
    def __init__(self, alert_threshold: float = 5.0):
        """
        初始化监控器
        
        Args:
            alert_threshold: 每个目标每小时的告警阈值（默认每小时超过5个任务则告警）
        """
        self.guard = TaskGenerationGuardV43()
        self.alert_threshold = alert_threshold
        self.alerts = []
        
        # 目标名称映射
        self.goal_names = {
            1: "AI助手优化",
            2: "和光智成商业化",
            3: "学术影响力建设",
            4: "财富增值与资产管理",
            5: "家庭幸福与子女教育",
            6: "社会工作与公益",
            7: "身心健康与生活质量"
        }
    
    def get_goal_name(self, goal_id: int) -> str:
        """获取目标名称"""
        return self.goal_names.get(goal_id, f"目标#{goal_id}")
    
    def check_frequency_anomalies(self, hours: int = 24) -> Dict[str, Any]:
        """
        检查频率异常
        
        Args:
            hours: 检查时间窗口（小时）
            
        Returns:
            异常检测结果字典
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        
        # 按小时统计各目标的任务生成量
        sql = """
            SELECT goal_id,
                   HOUR(created_at) as hour,
                   DATE(created_at) as date,
                   COUNT(*) as count
            FROM tasks
            WHERE created_at >= %s
            GROUP BY goal_id, DATE(created_at), HOUR(created_at)
            ORDER BY goal_id, date, hour
        """
        hourly_stats = execute_query(sql, (cutoff,))
        
        anomalies = []
        peak_hours = {}
        
        for stat in hourly_stats:
            goal_id = stat['goal_id']
            hour = stat['hour']
            date = stat['date']
            count = stat['count']
            
            # 检查是否超过每小时阈值
            if count > self.alert_threshold:
                anomalies.append({
                    'goal_id': goal_id,
                    'goal_name': self.get_goal_name(goal_id),
                    'date': str(date),
                    'hour': hour,
                    'count': count,
                    'threshold': self.alert_threshold,
                    'severity': 'high' if count > self.alert_threshold * 2 else 'medium'
                })
            
            # 记录峰值
            if goal_id not in peak_hours or count > peak_hours[goal_id]['count']:
                peak_hours[goal_id] = {
                    'date': str(date),
                    'hour': hour,
                    'count': count
                }
        
        return {
            'window_hours': hours,
            'checked_at': datetime.now().isoformat(),
            'anomalies': anomalies,
            'anomaly_count': len(anomalies),
            'peak_hours': peak_hours
        }
    
    def get_goal_status_report(self) -> Dict[str, Any]:
        """
        生成所有目标的状态报告
        
        Returns:
            完整状态报告字典
        """
        goal_statuses = []
        
        for goal_id in range(1, 8):
            status = self.guard.get_goal_status(goal_id)
            status['goal_name'] = self.get_goal_name(goal_id)
            goal_statuses.append(status)
        
        # 总体统计
        total_pending = sum(g['pending_tasks']['count'] for g in goal_statuses)
        total_quota_used = sum(g['frequency']['used'] for g in goal_statuses)
        goals_over_pending = [g for g in goal_statuses if not g['pending_tasks']['allowed']]
        goals_over_quota = [g for g in goal_statuses if not g['frequency']['allowed']]
        
        return {
            'generated_at': datetime.now().isoformat(),
            'goals': goal_statuses,
            'summary': {
                'total_pending_tasks': total_pending,
                'total_quota_used_24h': total_quota_used,
                'goals_over_pending_limit': len(goals_over_pending),
                'goals_over_frequency_limit': len(goals_over_quota),
                'pending_over_limit_details': goals_over_pending,
                'quota_over_limit_details': goals_over_quota
            },
            'system_health': {
                'pending_health': len(goals_over_pending) == 0,
                'frequency_health': len(goals_over_quota) == 0,
                'overall_health': len(goals_over_pending) == 0 and len(goals_over_quota) == 0
            }
        }
    
    def get_duplicate_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """
        分析重复任务
        
        Args:
            hours: 分析时间窗口
            
        Returns:
            重复分析结果
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        
        # 15字前缀重复分析
        sql1 = """
            SELECT LEFT(title, 15) as prefix,
                   COUNT(*) as duplicate_count,
                   GROUP_CONCAT(id SEPARATOR ', ') as task_ids,
                   GROUP_CONCAT(DISTINCT goal_id SEPARATOR ', ') as goal_ids,
                   MIN(created_at) as first_seen,
                   MAX(created_at) as last_seen
            FROM tasks
            WHERE created_at >= %s
              AND status NOT IN ('cancelled', 'deleted')
            GROUP BY prefix
            HAVING duplicate_count > 1
            ORDER BY duplicate_count DESC
        """
        duplicates = execute_query(sql1, (cutoff,))
        
        # 完全标题重复
        sql2 = """
            SELECT title,
                   COUNT(*) as duplicate_count,
                   GROUP_CONCAT(id SEPARATOR ', ') as task_ids
            FROM tasks
            WHERE created_at >= %s
              AND status NOT IN ('cancelled', 'deleted')
            GROUP BY title
            HAVING duplicate_count > 1
            ORDER BY duplicate_count DESC
            LIMIT 10
        """
        exact_duplicates = execute_query(sql2, (cutoff,))
        
        total_duplicated_tasks = sum(d['duplicate_count'] for d in duplicates)
        
        return {
            'window_hours': hours,
            'analyzed_at': datetime.now().isoformat(),
            'prefix_duplicates': duplicates,
            'exact_title_duplicates': exact_duplicates,
            'total_prefix_duplicate_groups': len(duplicates),
            'total_exact_duplicate_groups': len(exact_duplicates),
            'total_duplicated_tasks_affected': total_duplicated_tasks,
            'duplicate_rate': total_duplicated_tasks / max(total_duplicated_tasks, 1)
        }
    
    def generate_full_report(self, output_file: Optional[str] = None) -> str:
        """
        生成完整的监控报告
        
        Args:
            output_file: 可选的输出文件路径
            
        Returns:
            报告内容（Markdown格式）
        """
        # 获取各项数据
        status_report = self.get_goal_status_report()
        anomaly_report = self.check_frequency_anomalies(hours=24)
        duplicate_report = self.get_duplicate_analysis(hours=24)
        guard_stats = self.guard.get_statistics(hours=24)
        
        # 构建报告
        report = f"""# SDS v4.3 调度系统频率监控报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**监控版本**: v4.3 - 三重保障系统
**对应任务**: #2110 - 调度系统频率限制与去重机制升级

---

## 📊 系统总体状态

| 指标 | 数值 | 状态 |
|------|------|------|
| Pending任务总数 | {status_report['summary']['total_pending_tasks']} | {'✅ 正常' if status_report['system_health']['pending_health'] else '⚠️ 超限'} |
| 24小时内生成任务数 | {status_report['summary']['total_quota_used_24h']} | {'✅ 正常' if status_report['system_health']['frequency_health'] else '⚠️ 超限'} |
| Pending超限目标数 | {status_report['summary']['goals_over_pending_limit']} | {'✅ 0' if status_report['summary']['goals_over_pending_limit'] == 0 else '⚠️ ' + str(status_report['summary']['goals_over_pending_limit'])} |
| 频率超限目标数 | {status_report['summary']['goals_over_frequency_limit']} | {'✅ 0' if status_report['summary']['goals_over_frequency_limit'] == 0 else '⚠️ ' + str(status_report['summary']['goals_over_frequency_limit'])} |
| 检测到异常数 | {anomaly_report['anomaly_count']} | {'✅ 0' if anomaly_report['anomaly_count'] == 0 else '⚠️ ' + str(anomaly_report['anomaly_count'])} |
| 前缀重复组数 | {duplicate_report['total_prefix_duplicate_groups']} | {'✅ 0' if duplicate_report['total_prefix_duplicate_groups'] == 0 else '⚠️ ' + str(duplicate_report['total_prefix_duplicate_groups'])} |

**系统健康状态**: {'✅ 健康' if status_report['system_health']['overall_health'] else '⚠️ 需要关注'}

---

## 🎯 各目标详细状态

| 目标ID | 目标名称 | 24h已生成 | 频率限制 | 剩余配额 | Pending数 | Pending限制 | 可用槽位 | 状态 |
|--------|----------|-----------|----------|----------|-----------|-------------|----------|------|
"""
        
        for goal in status_report['goals']:
            freq = goal['frequency']
            pending = goal['pending_tasks']
            freq_ok = '✅' if freq['allowed'] else '🔴'
            pending_ok = '✅' if pending['allowed'] else '🔴'
            
            report += (
                f"| {goal['goal_id']} | {goal['goal_name']} | "
                f"{freq['used']} | {freq['limit']} | {freq['remaining']} | "
                f"{pending['count']} | {pending['limit']} | {pending['available_slots']} | "
                f"{freq_ok} {pending_ok} |\n"
            )
        
        # 频率超限详情
        if status_report['summary']['goals_over_frequency_limit'] > 0:
            report += f"""
### 🔴 频率超限目标详情

"""
            for goal in status_report['summary']['quota_over_limit_details']:
                quota_release = goal['frequency']['quota_release_time']
                report += f"- **{goal['goal_name']} (#{goal['goal_id']})**: "
                report += f"已用 {goal['frequency']['used']}/{goal['frequency']['limit']}, "
                report += f"配额释放时间: {quota_release}\n"
        
        # Pending超限详情
        if status_report['summary']['goals_over_pending_limit'] > 0:
            report += f"""
### 🔴 Pending水位超限目标详情

"""
            for goal in status_report['summary']['pending_over_limit_details']:
                report += f"- **{goal['goal_name']} (#{goal['goal_id']})**: "
                report += f"当前 {goal['pending_tasks']['count']}/{goal['pending_tasks']['limit']}\n"
        
        # 异常检测
        report += f"""
---

## ⚠️ 频率异常检测（过去24小时）

"""
        if anomaly_report['anomalies']:
            for anomaly in anomaly_report['anomalies']:
                severity_icon = '🔴' if anomaly['severity'] == 'high' else '🟡'
                report += f"{severity_icon} **{anomaly['goal_name']}** {anomaly['date']} {anomaly['hour']}点: "
                report += f"{anomaly['count']}个任务 (阈值: {anomaly['threshold']})\n"
        else:
            report += "✅ 未检测到频率异常\n"
        
        # 重复任务分析
        report += f"""
---

## 🔍 重复任务分析（过去24小时）

"""
        if duplicate_report['prefix_duplicates']:
            report += f"检测到 {len(duplicate_report['prefix_duplicates'])} 组标题前缀重复:\n\n"
            for dup in duplicate_report['prefix_duplicates'][:10]:
                report += f"- \"{dup['prefix']}...\" → **{dup['duplicate_count']} 次重复**\n"
                report += f"  影响任务: {dup['task_ids']}\n"
        else:
            report += "✅ 未检测到标题前缀重复\n"
        
        # 守卫统计
        report += f"""
---

## 🛡️ 守卫系统统计（过去24小时）

| 指标 | 数值 |
|------|------|
| 成功生成任务数 | {guard_stats['tasks_generated']} |
| 被拦截任务数 | {guard_stats['tasks_rejected']} |
| 拦截率 | {guard_stats['rejection_rate']:.1%} |

"""
        if guard_stats['reject_by_reason']:
            report += "### 拦截原因分布\n\n"
            for reason, count in guard_stats['reject_by_reason'].items():
                reason_name = {
                    'frequency_limit': '频率超限',
                    'duplicate_title': '标题重复',
                    'pending_watermark': 'Pending水位超限'
                }.get(reason, reason)
                report += f"- **{reason_name}**: {count} 次\n"
        
        # 结论与建议
        report += f"""
---

## 📋 结论与建议

### 当前问题
"""
        
        issues = []
        if not status_report['system_health']['frequency_health']:
            issues.append("❌ 部分目标频率超限，需要检查任务生成逻辑")
        if not status_report['system_health']['pending_health']:
            issues.append("❌ 部分目标Pending水位过高，需要加快任务消费速度")
        if anomaly_report['anomaly_count'] > 0:
            issues.append("❌ 检测到频率异常，可能存在重复触发问题")
        if duplicate_report['total_prefix_duplicate_groups'] > 0:
            issues.append("❌ 存在标题重复，去重机制需要加强")
        
        if issues:
            for issue in issues:
                report += f"{issue}\n"
        else:
            report += "✅ 系统运行正常，无明显问题\n"
        
        report += f"""
### 优化建议
1. **每目标每24小时最多2个任务** - 确保频率限制生效
2. **标题前缀15字精确匹配** - 防止重复任务生成
3. **每目标最多3个Pending任务** - 控制任务堆积
4. **集成V4.3守卫到所有生成入口** - 确保全面生效

---

*SDS v4.3 频率监控报告 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        # 保存到文件
        if output_file:
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                f.write(report)
            logger.info(f"报告已保存到: {output_file}")
        
        return report
    
    def send_alert_if_needed(self) -> bool:
        """
        如有需要，发送告警
        
        Returns:
            是否发送了告警
        """
        status_report = self.get_goal_status_report()
        anomaly_report = self.check_frequency_anomalies(hours=1)
        
        has_issues = (
            not status_report['system_health']['overall_health'] or
            anomaly_report['anomaly_count'] > 0
        )
        
        if has_issues:
            alert_file = Path(get_config('paths.logs') + "/frequency-alert.log")
            with open(alert_file, 'a') as f:
                f.write(f"\n[{datetime.now().isoformat()}] ALERT:\n")
                f.write(f"  Pending超限: {status_report['summary']['goals_over_pending_limit']}\n")
                f.write(f"  频率超限: {status_report['summary']['goals_over_frequency_limit']}\n")
                f.write(f"  异常数: {anomaly_report['anomaly_count']}\n")
            
            logger.warning("检测到问题，告警已记录")
            return True
        
        logger.info("系统正常，无需告警")
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SDS v4.3 频率监控')
    parser.add_argument('--report', action='store_true', help='生成完整报告')
    parser.add_argument('--output', type=str, help='报告输出文件路径')
    parser.add_argument('--alert', action='store_true', help='检查并发送告警')
    parser.add_argument('--status', action='store_true', help='显示当前状态')
    
    args = parser.parse_args()
    
    monitor = TaskGenerationMonitor()
    
    if args.report:
        output = args.output or get_config('paths.output') + "/task-2110/frequency-monitor-report.md"
        report = monitor.generate_full_report(output_file=output)
        print(report)
    
    elif args.alert:
        monitor.send_alert_if_needed()
    
    elif args.status:
        status = monitor.get_goal_status_report()
        print("=" * 60)
        print("各目标状态概览")
        print("=" * 60)
        for goal in status['goals']:
            freq_ok = '✅' if goal['frequency']['allowed'] else '🔴'
            pending_ok = '✅' if goal['pending_tasks']['allowed'] else '🔴'
            print(f"{goal['goal_name']:20s} | 24h: {goal['frequency']['used']:2d}/{goal['frequency']['limit']:1d} {freq_ok} | "
                  f"Pending: {goal['pending_tasks']['count']:2d}/{goal['pending_tasks']['limit']:1d} {pending_ok}")
        print("=" * 60)
        print(f"系统健康: {'✅ 健康' if status['system_health']['overall_health'] else '⚠️ 有问题'}")
    
    else:
        parser.print_help()
        print("\n示例:")
        print("  python task_generation_monitor_v43.py --status")
        print("  python task_generation_monitor_v43.py --report")
        print("  python task_generation_monitor_v43.py --alert")


if __name__ == '__main__':
    main()

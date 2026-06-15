#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS任务生成频率监控脚本 V4.5+
功能：
1. 实时监控各目标任务生成频率
2. 检测异常高频生成并告警
3. 生成频率统计报告
4. 自动清理重复和僵尸任务

创建日期: 2026-04-26
版本: V4.5
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import logging
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from lib.db_connector import get_db_connection, execute_query, execute_update
from config_loader import get_config

# 日志配置
LOG_DIR = Path(get_config('paths.logs'))
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


@dataclass
class AlertConfig:
    """告警配置"""
    # 频率告警阈值
    FREQ_TASKS_PER_HOUR_WARN: int = 3
    FREQ_TASKS_PER_HOUR_CRITICAL: int = 5
    
    # Pending水位告警阈值
    PENDING_PER_GOAL_WARN: int = 4
    PENDING_PER_GOAL_CRITICAL: int = 6
    
    # 重复任务告警阈值
    DUPLICATE_PREFIX_WARN: int = 2
    DUPLICATE_PREFIX_CRITICAL: int = 4
    
    # 僵尸任务告警阈值（运行超时）
    ZOMBIE_RUNNING_HOURS: int = 2
    
    # 告警等级
    LEVEL_INFO = 'INFO'
    LEVEL_WARN = 'WARN'
    LEVEL_CRITICAL = 'CRITICAL'


@dataclass
class Alert:
    """告警信息"""
    level: str
    category: str
    message: str
    goal_id: Optional[int] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def __str__(self):
        goal_str = f"[目标{self.goal_id}]" if self.goal_id else ""
        return f"[{self.level}] {self.category} {goal_str}: {self.message}"


class TaskGenerationMonitor:
    """任务生成监控器"""
    
    GOAL_NAMES = {
        1: "和光智成商业成功",
        2: "深云智合/硅研新材法务",
        3: "学术影响力建设",
        4: "财富增值与资产管理",
        5: "家庭幸福与子女教育",
        6: "社会参与与公共事务",
        7: "身心健康与自我提升"
    }
    
    def __init__(self, alert_config: AlertConfig = None):
        self.alert_config = alert_config or AlertConfig()
        self.alerts: List[Alert] = []
    
    def get_frequency_stats(self, hours: int = 24) -> Dict:
        """获取频率统计"""
        sql = """
            SELECT 
                goal_id,
                COUNT(*) as total_tasks,
                COUNT(*) / %s as tasks_per_hour,
                MIN(created_at) as first_generation,
                MAX(created_at) as last_generation,
                COUNT(DISTINCT HOUR(created_at)) as active_hours,
                COUNT(DISTINCT DATE_FORMAT(created_at, '%%Y-%%m-%%d %%H:00')) as hourly_distribution
            FROM tasks
            WHERE created_at > NOW() - INTERVAL %s HOUR
              AND task_type LIKE 'auto_generated%%'
            GROUP BY goal_id
            ORDER BY total_tasks DESC
        """
        results = execute_query(sql, (hours, hours))
        
        stats = {}
        for row in results:
            gid = row['goal_id']
            if gid:
                stats[gid] = {
                    'goal_id': gid,
                    'goal_name': self.GOAL_NAMES.get(gid, f'目标{gid}'),
                    'total_tasks': row['total_tasks'],
                    'tasks_per_hour': round(row['tasks_per_hour'], 2),
                    'first_generation': str(row['first_generation']),
                    'last_generation': str(row['last_generation']),
                    'active_hours': row['active_hours'],
                    'hourly_distribution': row['hourly_distribution']
                }
        
        return stats
    
    def check_frequency_alerts(self, hours: int = 24) -> List[Alert]:
        """检查频率告警"""
        alerts = []
        stats = self.get_frequency_stats(hours)
        
        for gid, stat in stats.items():
            tph = stat['tasks_per_hour']
            
            if tph >= self.alert_config.FREQ_TASKS_PER_HOUR_CRITICAL:
                alerts.append(Alert(
                    level=self.alert_config.LEVEL_CRITICAL,
                    category='FREQUENCY',
                    message=f"任务生成频率过高: {tph:.2f} 个/小时, 过去{hours}小时共生成{stat['total_tasks']}个",
                    goal_id=gid,
                    metric_value=tph,
                    threshold=self.alert_config.FREQ_TASKS_PER_HOUR_CRITICAL
                ))
            elif tph >= self.alert_config.FREQ_TASKS_PER_HOUR_WARN:
                alerts.append(Alert(
                    level=self.alert_config.LEVEL_WARN,
                    category='FREQUENCY',
                    message=f"任务生成频率偏高: {tph:.2f} 个/小时, 过去{hours}小时共生成{stat['total_tasks']}个",
                    goal_id=gid,
                    metric_value=tph,
                    threshold=self.alert_config.FREQ_TASKS_PER_HOUR_WARN
                ))
        
        return alerts
    
    def get_pending_watermark(self) -> Dict:
        """获取Pending水位"""
        sql = """
            SELECT 
                goal_id,
                COUNT(*) as pending_count,
                MIN(created_at) as oldest_pending,
                MAX(created_at) as newest_pending
            FROM tasks
            WHERE status = 'pending'
            GROUP BY goal_id
            ORDER BY pending_count DESC
        """
        results = execute_query(sql)
        
        stats = {}
        for row in results:
            gid = row['goal_id']
            if gid:
                stats[gid] = {
                    'goal_id': gid,
                    'goal_name': self.GOAL_NAMES.get(gid, f'目标{gid}'),
                    'pending_count': row['pending_count'],
                    'oldest_pending': str(row['oldest_pending']),
                    'newest_pending': str(row['newest_pending'])
                }
        
        return stats
    
    def check_pending_alerts(self) -> List[Alert]:
        """检查Pending水位告警"""
        alerts = []
        stats = self.get_pending_watermark()
        
        for gid, stat in stats.items():
            count = stat['pending_count']
            
            if count >= self.alert_config.PENDING_PER_GOAL_CRITICAL:
                alerts.append(Alert(
                    level=self.alert_config.LEVEL_CRITICAL,
                    category='PENDING_WATERMARK',
                    message=f"Pending任务过多: {count}个, 超过临界阈值",
                    goal_id=gid,
                    metric_value=count,
                    threshold=self.alert_config.PENDING_PER_GOAL_CRITICAL
                ))
            elif count >= self.alert_config.PENDING_PER_GOAL_WARN:
                alerts.append(Alert(
                    level=self.alert_config.LEVEL_WARN,
                    category='PENDING_WATERMARK',
                    message=f"Pending任务偏高: {count}个, 超过警告阈值",
                    goal_id=gid,
                    metric_value=count,
                    threshold=self.alert_config.PENDING_PER_GOAL_WARN
                ))
        
        return alerts
    
    def get_duplicate_stats(self, hours: int = 24, prefix_len: int = 15) -> Dict:
        """获取重复任务统计"""
        sql = """
            SELECT 
                LEFT(title, %s) as prefix,
                COUNT(*) as duplicate_count,
                GROUP_CONCAT(DISTINCT goal_id ORDER BY goal_id SEPARATOR ',') as goal_ids,
                GROUP_CONCAT(DISTINCT status SEPARATOR ',') as statuses,
                MIN(created_at) as first_created,
                MAX(created_at) as last_created
            FROM tasks
            WHERE created_at > NOW() - INTERVAL %s HOUR
            GROUP BY prefix
            HAVING duplicate_count > 1
            ORDER BY duplicate_count DESC
        """
        results = execute_query(sql, (prefix_len, hours))
        
        return {
            'total_duplicate_prefixes': len(results),
            'total_duplicate_tasks': sum(r['duplicate_count'] for r in results),
            'duplicates': results,
            'prefix_length': prefix_len,
            'check_hours': hours
        }
    
    def check_duplicate_alerts(self, hours: int = 24) -> List[Alert]:
        """检查重复任务告警"""
        alerts = []
        stats = self.get_duplicate_stats(hours)
        
        for dup in stats['duplicates']:
            count = dup['duplicate_count']
            
            if count >= self.alert_config.DUPLICATE_PREFIX_CRITICAL:
                alerts.append(Alert(
                    level=self.alert_config.LEVEL_CRITICAL,
                    category='DUPLICATE_TASKS',
                    message=f"严重重复: 前缀\"{dup['prefix']}\"共有{count}个重复任务",
                    goal_id=None,
                    metric_value=count,
                    threshold=self.alert_config.DUPLICATE_PREFIX_CRITICAL
                ))
            elif count >= self.alert_config.DUPLICATE_PREFIX_WARN:
                alerts.append(Alert(
                    level=self.alert_config.LEVEL_WARN,
                    category='DUPLICATE_TASKS',
                    message=f"任务重复: 前缀\"{dup['prefix']}\"共有{count}个重复任务",
                    goal_id=None,
                    metric_value=count,
                    threshold=self.alert_config.DUPLICATE_PREFIX_WARN
                ))
        
        return alerts
    
    def get_zombie_tasks(self) -> List[Dict]:
        """获取僵尸任务"""
        sql = """
            SELECT 
                id, title, goal_id, status, created_at, updated_at,
                TIMESTAMPDIFF(HOUR, created_at, NOW()) as running_hours,
                execution_log
            FROM tasks
            WHERE status = 'in_progress'
              AND created_at < NOW() - INTERVAL %s HOUR
            ORDER BY running_hours DESC
        """
        return execute_query(sql, (self.alert_config.ZOMBIE_RUNNING_HOURS,))
    
    def check_zombie_alerts(self) -> List[Alert]:
        """检查僵尸任务告警"""
        alerts = []
        zombies = self.get_zombie_tasks()
        
        for zombie in zombies:
            alerts.append(Alert(
                level=self.alert_config.LEVEL_WARN,
                category='ZOMBIE_TASK',
                message=f"可能是僵尸任务: #{zombie['id']} \"{zombie['title'][:40]}...\" 已运行{zombie['running_hours']}小时",
                goal_id=zombie['goal_id'],
                metric_value=zombie['running_hours'],
                threshold=self.alert_config.ZOMBIE_RUNNING_HOURS
            ))
        
        return alerts
    
    def run_full_check(self, hours: int = 24) -> Dict:
        """执行完整检查"""
        logger.info(f"开始执行完整监控检查 (过去{hours}小时)...")
        
        self.alerts = []
        
        # 1. 频率检查
        freq_alerts = self.check_frequency_alerts(hours)
        self.alerts.extend(freq_alerts)
        logger.info(f"频率检查: 发现 {len(freq_alerts)} 个告警")
        
        # 2. Pending水位检查
        pending_alerts = self.check_pending_alerts()
        self.alerts.extend(pending_alerts)
        logger.info(f"Pending检查: 发现 {len(pending_alerts)} 个告警")
        
        # 3. 重复任务检查
        dup_alerts = self.check_duplicate_alerts(hours)
        self.alerts.extend(dup_alerts)
        logger.info(f"重复检查: 发现 {len(dup_alerts)} 个告警")
        
        # 4. 僵尸任务检查
        zombie_alerts = self.check_zombie_alerts()
        self.alerts.extend(zombie_alerts)
        logger.info(f"僵尸任务检查: 发现 {len(zombie_alerts)} 个告警")
        
        # 汇总统计
        critical_count = sum(1 for a in self.alerts if a.level == self.alert_config.LEVEL_CRITICAL)
        warn_count = sum(1 for a in self.alerts if a.level == self.alert_config.LEVEL_WARN)
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'check_hours': hours,
            'total_alerts': len(self.alerts),
            'critical_alerts': critical_count,
            'warning_alerts': warn_count,
            'alerts': [a.__dict__ for a in self.alerts],
            'frequency_stats': self.get_frequency_stats(hours),
            'pending_stats': self.get_pending_watermark(),
            'duplicate_stats': self.get_duplicate_stats(hours),
            'zombie_count': len(self.get_zombie_tasks())
        }
        
        logger.info(f"检查完成: 共{len(self.alerts)}个告警 (CRITICAL={critical_count}, WARN={warn_count})")
        return result
    
    def print_report(self, result: Dict):
        """打印监控报告"""
        # print("\n" + "="*80)
        # print("SDS任务生成监控报告 V4.5")
        # print("="*80)
        # print(f"检查时间: {result['timestamp']}")
        # print(f"检查范围: 过去{result['check_hours']}小时")
        # print()
        
        # print("【告警汇总】")
        # print(f"  总告警数: {result['total_alerts']}")
        # print(f"  CRITICAL: {result['critical_alerts']}")
        # print(f"  WARN: {result['warning_alerts']}")
        # print()
        
        if result['alerts']:
            # print("【告警详情】")
            for alert in result['alerts']:
                goal_str = f"[目标{alert['goal_id']}]" if alert['goal_id'] else ""
                # print(f"  [{alert['level']}] {alert['category']} {goal_str}")
                # print(f"    {alert['message']}")
            # print()
        
        # print("【频率统计】")
        for gid, stat in result['frequency_stats'].items():
            # print(f"  目标{gid} ({stat['goal_name']}): {stat['total_tasks']}个, {stat['tasks_per_hour']:.2f}个/小时")
        # print()
        
        # print("【Pending水位】")
        for gid, stat in result['pending_stats'].items():
            # print(f"  目标{gid} ({stat['goal_name']}): {stat['pending_count']}个 pending")
        total_pending = sum(s['pending_count'] for s in result['pending_stats'].values())
        # print(f"  总计: {total_pending}个 pending任务")
        # print()
        
        # print("【重复统计】")
        dup = result['duplicate_stats']
        # print(f"  重复前缀数: {dup['total_duplicate_prefixes']}")
        # print(f"  重复任务数: {dup['total_duplicate_tasks']}")
        if dup['duplicates']:
            # print("  严重重复:")
            for d in dup['duplicates'][:5]:
                # print(f"    \"{d['prefix']}\": {d['duplicate_count']}个")
        # print()
        
        # print("【僵尸任务】")
        # print(f"  运行超时任务: {result['zombie_count']}个")
        # print("="*80)
    
    def save_report(self, result: Dict, output_file: str):
        """保存报告到文件"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        logger.info(f"报告已保存到: {output_file}")
    
    def auto_fix_issues(self, dry_run: bool = False) -> Dict:
        """自动修复问题
        
        Args:
            dry_run: 是否为演练模式（不实际修改）
            
        Returns:
            修复统计
        """
        fix_stats = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': dry_run,
            'duplicate_tasks_cancelled': 0,
            'zombie_tasks_reset': 0,
            'actions': []
        }
        
        logger.info(f"开始自动修复问题 (dry_run={dry_run})...")
        
        # 1. 清理重复的pending任务
        sql_dup = """
            SELECT LEFT(title, 15) as prefix,
                   GROUP_CONCAT(id ORDER BY created_at DESC SEPARATOR ',') as task_ids,
                   COUNT(*) as count
            FROM tasks
            WHERE status = 'pending'
            GROUP BY prefix
            HAVING count > 1
            ORDER BY count DESC
        """
        duplicate_groups = execute_query(sql_dup)
        
        for group in duplicate_groups:
            task_ids = [int(i) for i in group['task_ids'].split(',')]
            keep_id = task_ids[0]
            cancel_ids = task_ids[1:]
            
            for task_id in cancel_ids:
                if not dry_run:
                    execute_update("""
                        UPDATE tasks 
                        SET status = 'duplicate', 
                            updated_at = NOW(),
                            notes = CONCAT(IFNULL(notes, ''), '\\n[监控自动修复] 标题前缀重复，保留ID ', %s)
                        WHERE id = %s AND status = 'pending'
                    """, (keep_id, task_id))
                
                fix_stats['actions'].append({
                    'type': 'CANCEL_DUPLICATE',
                    'task_id': task_id,
                    'kept_id': keep_id,
                    'reason': f"标题前缀重复: {group['prefix']}"
                })
                fix_stats['duplicate_tasks_cancelled'] += 1
        
        # 2. 重置僵尸任务
        zombies = self.get_zombie_tasks()
        for zombie in zombies:
            task_id = zombie['id']
            
            if not dry_run:
                execute_update("""
                    UPDATE tasks 
                    SET status = 'pending', 
                        updated_at = NOW(),
                        notes = CONCAT(IFNULL(notes, ''), '\\n[监控自动修复] 僵尸任务重置，运行超过2小时')
                    WHERE id = %s
                """, (task_id,))
            
            fix_stats['actions'].append({
                'type': 'RESET_ZOMBIE',
                'task_id': task_id,
                'running_hours': zombie['running_hours'],
                'reason': '任务运行超时'
            })
            fix_stats['zombie_tasks_reset'] += 1
        
        logger.info(f"修复完成: 取消{fix_stats['duplicate_tasks_cancelled']}个重复任务, "
                   f"重置{fix_stats['zombie_tasks_reset']}个僵尸任务")
        
        return fix_stats


def main():
    parser = argparse.ArgumentParser(description='SDS任务生成频率监控工具 V4.5')
    parser.add_argument('--hours', type=int, default=24, help='检查过去N小时的数据')
    parser.add_argument('--output', type=str, help='输出报告文件路径')
    parser.add_argument('--auto-fix', action='store_true', help='自动修复问题')
    parser.add_argument('--dry-run', action='store_true', help='演练模式，不实际修改')
    parser.add_argument('--alert-only', action='store_true', help='只输出告警，不打印完整报告')
    
    args = parser.parse_args()
    
    monitor = TaskGenerationMonitor()
    
    # 执行检查
    result = monitor.run_full_check(args.hours)
    
    # 输出报告
    if not args.alert_only:
        monitor.print_report(result)
    
    # 保存报告
    if args.output:
        monitor.save_report(result, args.output)
    
    # 自动修复
    if args.auto_fix:
        fix_result = monitor.auto_fix_issues(dry_run=args.dry_run)
        # print("\n【自动修复结果】")
        # print(f"  演练模式: {fix_result['dry_run']}")
        # print(f"  取消重复任务: {fix_result['duplicate_tasks_cancelled']}个")
        # print(f"  重置僵尸任务: {fix_result['zombie_tasks_reset']}个")
        if fix_result['actions']:
            # print("  操作明细:")
            for action in fix_result['actions'][:10]:
                # print(f"    - [{action['type']}] 任务#{action['task_id']}: {action['reason']}")
            if len(fix_result['actions']) > 10:
                # print(f"    ... 还有{len(fix_result['actions'])-10}个操作")
    
    # 非零退出码表示有CRITICAL告警
    if result['critical_alerts'] > 0:
        sys.exit(2)
    elif result['warning_alerts'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

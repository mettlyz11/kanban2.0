#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS任务生成频率监控脚本 V4.7 (Task#2110)

功能:
1. 实时监控各目标24小时任务生成数量
2. 监控pending任务水位
3. 检测重复任务
4. 生成告警报告
5. 审计统计
"""

import sys
from config_loader import get_config
import os
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
sys.path.insert(0, str(os.path.dirname(os.path.dirname(__file__)) + '/core'))

from lib.db_connector import execute_query
from datetime import datetime, timedelta
from collections import defaultdict


class TaskGenerationMonitor:
    """任务生成监控器"""
    
    def __init__(self):
        self.goal_names = {
            1: 'AI助手优化',
            2: '和光智成商业化',
            3: '和光工业AI',
            4: '学术影响力建设',
            5: '深云智合诉讼',
            6: '个人成长与健康',
            7: '系统维护'
        }
    
    def get_24h_generation_stats(self) -> dict:
        """获取过去24小时生成统计"""
        sql = """
            SELECT 
                goal_id,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status LIKE 'completed%%' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM tasks
            WHERE created_at >= NOW() - INTERVAL 24 HOUR
              AND task_type LIKE 'auto_generated%%'
            GROUP BY goal_id
            ORDER BY total DESC
        """
        results = execute_query(sql)
        
        stats = defaultdict(lambda: {
            'total': 0, 'pending': 0, 'in_progress': 0,
            'completed': 0, 'failed': 0, 'goal_name': ''
        })
        
        for r in results:
            stats[r['goal_id']] = {
                'total': r['total'],
                'pending': r['pending'],
                'in_progress': r['in_progress'],
                'completed': r['completed'],
                'failed': r['failed'],
                'goal_name': self.goal_names.get(r['goal_id'], f'目标{r["goal_id"]}')
            }
        
        # 补充没有生成任务的目标
        for gid in range(1, 8):
            if gid not in stats:
                stats[gid] = {
                    'total': 0, 'pending': 0, 'in_progress': 0,
                    'completed': 0, 'failed': 0,
                    'goal_name': self.goal_names.get(gid, f'目标{gid}')
                }
        
        return dict(stats)
    
    def get_pending_watermark(self) -> dict:
        """获取当前pending水位"""
        sql = """
            SELECT 
                goal_id,
                COUNT(*) as pending_count
            FROM tasks
            WHERE status = 'pending'
              AND execution_mode = 'auto'
            GROUP BY goal_id
        """
        results = execute_query(sql)
        
        watermark = {g: 0 for g in range(1, 8)}
        for r in results:
            watermark[r['goal_id']] = r['pending_count']
        
        return watermark
    
    def detect_duplicate_tasks(self, hours: int = 24) -> list:
        """检测重复任务（前15字精确匹配）"""
        sql = """
            SELECT 
                LEFT(title, 15) as prefix,
                goal_id,
                COUNT(*) as duplicate_count,
                GROUP_CONCAT(id ORDER BY created_at SEPARATOR ',') as task_ids,
                MIN(created_at) as first_created,
                MAX(created_at) as last_created
            FROM tasks
            WHERE created_at >= NOW() - INTERVAL %s HOUR
              AND task_type LIKE 'auto_generated%%'
            GROUP BY LEFT(title, 15), goal_id
            HAVING COUNT(*) >= 2
            ORDER BY duplicate_count DESC
        """
        return execute_query(sql, (hours,))
    
    def get_hourly_distribution(self, hours: int = 24) -> list:
        """获取按小时分布"""
        sql = """
            SELECT 
                HOUR(created_at) as hour,
                COUNT(*) as count
            FROM tasks
            WHERE created_at >= NOW() - INTERVAL %s HOUR
              AND task_type LIKE 'auto_generated%%'
            GROUP BY HOUR(created_at)
            ORDER BY hour
        """
        return execute_query(sql, (hours,))
    
    def check_rate_limit_violations(self) -> list:
        """检查频率限制违规（超过2个/24h）"""
        stats = self.get_24h_generation_stats()
        violations = []
        
        for gid, s in stats.items():
            if s['total'] > 2:
                violations.append({
                    'goal_id': gid,
                    'goal_name': s['goal_name'],
                    'actual': s['total'],
                    'limit': 2,
                    'overage': s['total'] - 2
                })
        
        return violations
    
    def check_watermark_violations(self) -> list:
        """检查pending水位违规（超过3个）"""
        watermark = self.get_pending_watermark()
        violations = []
        
        for gid, count in watermark.items():
            if count > 3:
                violations.append({
                    'goal_id': gid,
                    'goal_name': self.goal_names.get(gid, f'目标{gid}'),
                    'actual': count,
                    'limit': 3,
                    'overage': count - 3
                })
        
        return violations
    
    def generate_report(self) -> str:
        """生成监控报告"""
        lines = []
        lines.append('=' * 70)
        lines.append('SDS任务生成监控报告 V4.7 (Task#2110)')
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append('=' * 70)
        
        # 1. 24小时生成统计
        stats = self.get_24h_generation_stats()
        lines.append('\n【过去24小时任务生成统计】')
        lines.append(f"{'目标':<5} {'名称':<20} {'总数':<8} {'pending':<10} {'进行中':<10} {'已完成':<10}")
        lines.append('-' * 70)
        total_all = 0
        for gid in range(1, 8):
            s = stats.get(gid, {})
            total = s.get('total', 0)
            total_all += total
            limit_marker = '🔴' if total > 2 else ('🟡' if total == 2 else '✅')
            lines.append(
                f"{limit_marker} {gid:<3} {s.get('goal_name', ''):<20} "
                f"{total:<8} {s.get('pending', 0):<10} {s.get('in_progress', 0):<10} "
                f"{s.get('completed', 0):<10}"
            )
        lines.append('-' * 70)
        lines.append(f"总计: {total_all}个任务")
        
        # 2. 频率限制检查
        rate_violations = self.check_rate_limit_violations()
        lines.append('\n【频率限制检查 (限制: 2个/24h)】')
        if rate_violations:
            for v in rate_violations:
                lines.append(f"  ❌ {v['goal_name']}: {v['actual']}个 (超{v['overage']}个)")
        else:
            lines.append('  ✅ 所有目标均在频率限制范围内')
        
        # 3. Pending水位检查
        water_violations = self.check_watermark_violations()
        lines.append('\n【Pending水位检查 (限制: 3个/目标)】')
        if water_violations:
            for v in water_violations:
                lines.append(f"  ❌ {v['goal_name']}: {v['actual']}个 (超{v['overage']}个)")
        else:
            lines.append('  ✅ 所有目标pending水位正常')
        
        # 4. 重复任务检测
        duplicates = self.detect_duplicate_tasks(24)
        lines.append('\n【重复任务检测 (前15字精确匹配)】')
        if duplicates:
            for d in duplicates:
                lines.append(
                    f"  🔴 '{d['prefix']}' (目标{d['goal_id']}): "
                    f"{d['duplicate_count']}次重复, IDs={d['task_ids']}"
                )
        else:
            lines.append('  ✅ 未发现重复任务')
        
        # 5. 小时分布
        hourly = self.get_hourly_distribution(24)
        lines.append('\n【24小时生成分布】')
        for h in hourly:
            bar = '█' * min(int(h['count'] / 1), 40)
            lines.append(f"  {h['hour']:02d}:00  {h['count']:<4} {bar}")
        
        # 6. 总结
        lines.append('\n' + '=' * 70)
        has_issues = rate_violations or water_violations or duplicates
        if has_issues:
            lines.append('⚠️  检测到问题，建议检查调度系统配置')
        else:
            lines.append('✅ 所有指标正常，调度系统运行良好')
        lines.append('=' * 70)
        
        return '\n'.join(lines)


def main():
    monitor = TaskGenerationMonitor()
    report = monitor.generate_report()
    # print(report)
    
    # 保存报告
    report_file = get_config('paths.logs') + '/task-generation-monitor-report.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    # print(f"\n报告已保存到: {report_file}")


if __name__ == '__main__':
    main()

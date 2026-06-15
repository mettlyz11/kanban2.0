#!/usr/bin/env python3
"""
SDS任务分析器 (Task Analyzer)
功能：分析现有任务、项目差距、系统状态，智能识别需要执行的工作
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# 添加lib路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from lib.db_connector import get_db_connection, execute_query, execute_update
from config_loader import get_config

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(get_config('paths.logs') + '/sds-task-analyzer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TaskAnalyzer')


class TaskAnalyzer:
    """任务分析器 - 智能识别需要执行的工作"""
    
    def __init__(self):
        self.conn = None
        self.task_gaps = []
        self.system_issues = []
        self.project_gaps = []
        
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
    
    def analyze_active_projects(self) -> List[Dict]:
        """分析活跃项目，识别任务缺口"""
        logger.info("分析活跃项目状态...")
        
        sql = """
            SELECT p.id, p.name, p.status, 
                   COUNT(t.id) as task_count,
                   SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) as completed_count,
                   SUM(CASE WHEN t.status IN ('pending', 'in_progress') THEN 1 ELSE 0 END) as active_count
            FROM projects p
            LEFT JOIN tasks t ON p.id = t.project_id
            WHERE p.status = 'active'
            GROUP BY p.id, p.name, p.status
            HAVING active_count = 0 OR task_count = 0
            ORDER BY p.id
        """
        
        results = execute_query(sql)
        gaps = []
        
        for row in results:
            gap = {
                'project_id': row['id'],
                'project_name': row['name'],
                'task_count': row['task_count'],
                'active_count': row['active_count'],
                'gap_type': 'no_tasks' if row['task_count'] == 0 else 'no_active_tasks',
                'severity': 'high' if row['task_count'] == 0 else 'medium'
            }
            gaps.append(gap)
            logger.warning(f"发现项目缺口: [{row['name']}] - {gap['gap_type']}")
        
        self.project_gaps = gaps
        return gaps
    
    def analyze_stale_tasks(self, hours: int = 24) -> List[Dict]:
        """分析停滞任务（超过指定时间无更新）"""
        logger.info(f"分析超过{hours}小时无更新的任务...")
        
        sql = """
            SELECT id, number, title, status, updated_at, 
                   TIMESTAMPDIFF(HOUR, updated_at, NOW()) as hours_since_update
            FROM tasks
            WHERE status IN ('pending', 'in_progress')
              AND TIMESTAMPDIFF(HOUR, updated_at, NOW()) > %s
            ORDER BY hours_since_update DESC
        """
        
        results = execute_query(sql, (hours,))
        stale_tasks = []
        
        for row in results:
            task = {
                'task_id': row['id'],
                'task_number': row['number'],
                'title': row['title'],
                'status': row['status'],
                'hours_since_update': row['hours_since_update'],
                'gap_type': 'stale_task'
            }
            stale_tasks.append(task)
            logger.warning(f"停滞任务: #{row['id']} - {row['title'][:50]} ({row['hours_since_update']}h)")
        
        return stale_tasks
    
    def analyze_task_completion_quality(self) -> List[Dict]:
        """分析任务完成质量"""
        logger.info("分析任务完成质量...")
        
        issues = []
        
        # 检查完成任务但缺少summary
        sql1 = """
            SELECT id, number, title, status, task_summary
            FROM tasks
            WHERE status = 'completed'
              AND (task_summary IS NULL OR CHAR_LENGTH(task_summary) < 50)
            ORDER BY updated_at DESC
            LIMIT 20
        """
        results1 = execute_query(sql1)
        
        for row in results1:
            issues.append({
                'task_id': row['id'],
                'issue_type': 'missing_or_short_summary',
                'details': f"summary长度: {len(row['task_summary']) if row['task_summary'] else 0}字"
            })
        
        # 检查完成任务但缺少execution_log
        sql2 = """
            SELECT id, number, title, status, execution_log
            FROM tasks
            WHERE status = 'completed'
              AND (execution_log IS NULL OR CHAR_LENGTH(execution_log) < 200)
            ORDER BY updated_at DESC
            LIMIT 20
        """
        results2 = execute_query(sql2)
        
        for row in results2:
            issues.append({
                'task_id': row['id'],
                'issue_type': 'missing_or_short_execution_log',
                'details': f"log长度: {len(row['execution_log']) if row['execution_log'] else 0}字"
            })
        
        for issue in issues[:5]:
            logger.warning(f"质量问题: #{issue['task_id']} - {issue['issue_type']}")
        
        return issues
    
    def analyze_system_health(self) -> Dict:
        """分析系统健康状态"""
        logger.info("分析系统健康状态...")
        
        health = {
            'timestamp': datetime.now().isoformat(),
            'pending_tasks': 0,
            'in_progress_tasks': 0,
            'completed_last_24h': 0,
            'failed_tasks': 0,
            'projects_without_tasks': 0,
            'stale_tasks_count': 0
        }
        
        # 统计各状态任务数
        sql = """
            SELECT status, COUNT(*) as count
            FROM tasks
            GROUP BY status
        """
        results = execute_query(sql)
        
        status_map = {
            'pending': 'pending_tasks',
            'in_progress': 'in_progress_tasks',
            'completed': 'completed_tasks',
            'failed': 'failed_tasks'
        }
        
        for row in results:
            key = status_map.get(row['status'].lower())
            if key:
                health[key] = row['count']
        
        # 24小时内完成的任务
        sql2 = """
            SELECT COUNT(*) as count
            FROM tasks
            WHERE status = 'completed'
              AND updated_at >= NOW() - INTERVAL 24 HOUR
        """
        result2 = execute_query(sql2)
        if result2:
            health['completed_last_24h'] = result2[0]['count']
        
        # 无任务的活跃项目
        sql3 = """
            SELECT COUNT(*) as count
            FROM projects p
            WHERE p.status = 'active'
              AND NOT EXISTS (SELECT 1 FROM tasks t WHERE t.project_id = p.id)
        """
        result3 = execute_query(sql3)
        if result3:
            health['projects_without_tasks'] = result3[0]['count']
        
        # 停滞任务
        sql4 = """
            SELECT COUNT(*) as count
            FROM tasks
            WHERE status IN ('pending', 'in_progress')
              AND TIMESTAMPDIFF(HOUR, updated_at, NOW()) > 24
        """
        result4 = execute_query(sql4)
        if result4:
            health['stale_tasks_count'] = result4[0]['count']
        
        logger.info(f"系统健康: pending={health['pending_tasks']}, "
                   f"in_progress={health['in_progress_tasks']}, "
                   f"completed_24h={health['completed_last_24h']}")
        
        return health
    
    def generate_task_recommendations(self) -> List[Dict]:
        """生成任务推荐列表"""
        logger.info("生成任务推荐...")
        
        recommendations = []
        
        # 1. 从项目缺口生成任务
        for gap in self.project_gaps:
            rec = {
                'task_type': 'project_gap_filler',
                'priority': 'high' if gap['severity'] == 'high' else 'medium',
                'project_id': gap['project_id'],
                'title': f"[{gap['project_name']}] 项目任务规划与补充",
                'description': f"项目状态分析发现: {gap['gap_type']}。需要为该项目规划并创建具体执行任务。\n"
                              f"项目ID: {gap['project_id']}\n"
                              f"现有任务数: {gap['task_count']}\n"
                              f"活跃任务数: {gap['active_count']}",
                'source': 'analyzer_project_gap'
            }
            recommendations.append(rec)
        
        # 2. 生成系统维护任务
        health = self.analyze_system_health()
        
        if health['stale_tasks_count'] > 0:
            recommendations.append({
                'task_type': 'system_maintenance',
                'priority': 'medium',
                'title': "停滞任务清理与重新激活",
                'description': f"系统发现 {health['stale_tasks_count']} 个停滞任务（超过24小时无更新）。"
                              f"需要检查这些任务的状态，决定是继续执行、重置还是归档。",
                'source': 'analyzer_stale_tasks'
            })
        
        if health['projects_without_tasks'] > 0:
            recommendations.append({
                'task_type': 'system_maintenance',
                'priority': 'high',
                'title': "活跃项目任务初始化",
                'description': f"有 {health['projects_without_tasks']} 个活跃项目没有任何任务。"
                              f"需要为这些项目创建具体的执行任务。",
                'source': 'analyzer_empty_projects'
            })
        
        # 3. 定期系统检查任务
        recommendations.append({
            'task_type': 'system_health_check',
            'priority': 'low',
            'title': "SDS系统健康检查与性能优化",
            'description': "定期检查自我驱动系统运行状态：\n"
                          "- 检查所有组件运行日志\n"
                          "- 验证数据库连接和性能\n"
                          "- 清理过期日志文件\n"
                          "- 优化系统配置参数",
            'source': 'analyzer_regular_check'
        })
        
        # 4. 知识库维护任务
        recommendations.append({
            'task_type': 'knowledge_maintenance',
            'priority': 'medium',
            'title': "系统记忆更新与知识库维护",
            'description': "整理近期执行的任务成果，更新系统知识库：\n"
                          "- 提取任务中的关键决策和经验\n"
                          "- 更新核心原则文档\n"
                          "- 归档重要执行记录",
            'source': 'analyzer_knowledge'
        })
        
        logger.info(f"生成 {len(recommendations)} 个任务推荐")
        return recommendations
    
    def run_full_analysis(self) -> Dict:
        """运行完整分析"""
        logger.info("=" * 60)
        logger.info("开始SDS任务分析器完整分析")
        logger.info("=" * 60)
        
        if not self.connect():
            return {'error': '数据库连接失败'}
        
        try:
            # 执行各项分析
            project_gaps = self.analyze_active_projects()
            stale_tasks = self.analyze_stale_tasks()
            quality_issues = self.analyze_task_completion_quality()
            recommendations = self.generate_task_recommendations()
            
            analysis_result = {
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'project_gaps_count': len(project_gaps),
                    'stale_tasks_count': len(stale_tasks),
                    'quality_issues_count': len(quality_issues),
                    'recommendations_count': len(recommendations)
                },
                'project_gaps': project_gaps,
                'stale_tasks': stale_tasks,
                'quality_issues': quality_issues,
                'recommendations': recommendations
            }
            
            # 保存分析结果 - 处理Decimal类型
            def decimal_default(obj):
                if hasattr(obj, '__class__') and obj.__class__.__name__ == 'Decimal':
                    return float(obj)
                raise TypeError
            
            output_file = Path(get_config('paths.logs') + "/sds-analysis-latest.json")
            with open(output_file, 'w') as f:
                json.dump(analysis_result, f, indent=2, ensure_ascii=False, default=decimal_default)
            
            logger.info(f"分析完成，结果已保存到 {output_file}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"分析异常: {e}")
            return {'error': str(e)}
        finally:
            self.close()
            logger.info("=" * 60)


if __name__ == "__main__":
    analyzer = TaskAnalyzer()
    result = analyzer.run_full_analysis()
    
    def decimal_default(obj):
        if hasattr(obj, '__class__') and obj.__class__.__name__ == 'Decimal':
            return float(obj)
        raise TypeError
    
    # print(json.dumps(result, indent=2, ensure_ascii=False, default=decimal_default))

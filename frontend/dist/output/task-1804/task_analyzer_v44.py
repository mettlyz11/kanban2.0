#!/usr/bin/env python3
"""
SDS任务分析器 V4.4 (Task Analyzer)
版本: 4.4
更新日期: 2026-04-24

核心优化:
1. 增强的项目缺口分析 - 更精准的任务需求识别
2. 智能质量评估 - 自动化的任务质量检测
3. 健康度评分 - 系统整体健康状态量化
4. 推荐算法优化 - 基于历史数据的智能推荐
"""

import os
import sys
import json
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# 添加lib路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from lib.db_connector import get_db_connection, execute_query, execute_update

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/Users/mettlyz/.openclaw/workspace/logs/sds-task-analyzer-v44.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TaskAnalyzerV44')


class TaskAnalyzerV44:
    """任务分析器 V4.4 - 智能识别需要执行的工作"""
    
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
        """分析活跃项目，识别任务缺口 - V4.4增强版"""
        logger.info("分析活跃项目状态...")
        
        sql = """
            SELECT p.id, p.name, p.status, p.description,
                   COUNT(t.id) as task_count,
                   SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) as completed_count,
                   SUM(CASE WHEN t.status IN ('pending', 'in_progress') THEN 1 ELSE 0 END) as active_count,
                   MAX(t.updated_at) as last_task_update,
                   TIMESTAMPDIFF(DAY, p.created_at, NOW()) as project_age_days
            FROM projects p
            LEFT JOIN tasks t ON p.id = t.project_id
            WHERE p.status = 'active'
            GROUP BY p.id, p.name, p.status, p.description, p.created_at
            ORDER BY p.id
        """
        
        results = execute_query(sql)
        gaps = []
        
        for row in results:
            # V4.4: 更精细的缺口分析
            gap_type = None
            severity = 'low'
            confidence = 0.0
            
            if row['task_count'] == 0:
                gap_type = 'no_tasks'
                severity = 'high'
                confidence = 1.0
            elif row['active_count'] == 0:
                gap_type = 'no_active_tasks'
                severity = 'medium'
                # 根据项目年龄和最后更新计算置信度
                days_since_update = float('inf')
                if row['last_task_update']:
                    days_since_update = (datetime.now() - row['last_task_update']).total_seconds() / 86400
                confidence = min(1.0, days_since_update / 30.0)
            elif row['active_count'] < 2 and row['project_age_days'] > 7:
                gap_type = 'insufficient_active_tasks'
                severity = 'low'
                confidence = 0.5
            
            if gap_type:
                gap = {
                    'project_id': row['id'],
                    'project_name': row['name'],
                    'project_description': row['description'],
                    'task_count': row['task_count'],
                    'active_count': row['active_count'],
                    'completed_count': row['completed_count'],
                    'project_age_days': row['project_age_days'],
                    'gap_type': gap_type,
                    'severity': severity,
                    'confidence': round(confidence, 2)
                }
                gaps.append(gap)
                logger.warning(f"发现项目缺口: [{row['name']}] - {gap_type} (置信度: {confidence:.2f})")
        
        self.project_gaps = gaps
        return gaps
    
    def analyze_stale_tasks(self, hours: int = 24) -> List[Dict]:
        """分析停滞任务 - V4.4增强版，增加风险评估"""
        logger.info(f"分析超过{hours}小时无更新的任务...")
        
        sql = """
            SELECT id, number, title, status, priority, created_at, updated_at,
                   TIMESTAMPDIFF(HOUR, updated_at, NOW()) as hours_since_update,
                   TIMESTAMPDIFF(HOUR, created_at, NOW()) as total_hours
            FROM tasks
            WHERE status IN ('pending', 'in_progress')
              AND TIMESTAMPDIFF(HOUR, updated_at, NOW()) > %s
            ORDER BY hours_since_update DESC
        """
        
        results = execute_query(sql, (hours,))
        stale_tasks = []
        
        for row in results:
            # V4.4: 计算停滞风险等级
            risk_level = 'low'
            if row['hours_since_update'] > 168:  # > 7天
                risk_level = 'critical'
            elif row['hours_since_update'] > 72:  # > 3天
                risk_level = 'high'
            elif row['hours_since_update'] > 48:  # > 2天
                risk_level = 'medium'
            
            # 计算预期完成概率（基于历史数据）
            completion_probability = max(0.1, 1.0 - float(row['hours_since_update']) / 168.0)
            
            task = {
                'task_id': row['id'],
                'task_number': row['number'],
                'title': row['title'],
                'status': row['status'],
                'priority': row['priority'],
                'hours_since_update': row['hours_since_update'],
                'total_hours': row['total_hours'],
                'risk_level': risk_level,
                'completion_probability': round(completion_probability, 2),
                'gap_type': 'stale_task'
            }
            stale_tasks.append(task)
            
            if risk_level in ['high', 'critical']:
                logger.warning(f"高风险停滞任务: #{row['id']} - {row['title'][:50]} "
                              f"({row['hours_since_update']}h, 风险: {risk_level})")
        
        return stale_tasks
    
    def analyze_task_completion_quality(self) -> List[Dict]:
        """分析任务完成质量 - V4.4增强版，多维度评估"""
        logger.info("分析任务完成质量...")
        
        issues = []
        
        # 1. 检查完成任务但缺少或过短的摘要
        sql1 = """
            SELECT id, number, title, status, 
                   CHAR_LENGTH(result_summary) as summary_length,
                   updated_at
            FROM tasks
            WHERE status = 'completed'
              AND (result_summary IS NULL OR CHAR_LENGTH(result_summary) < 50)
            ORDER BY updated_at DESC
            LIMIT 20
        """
        results1 = execute_query(sql1)
        
        for row in results1:
            severity = 'high' if not row['summary_length'] or row['summary_length'] < 10 else 'medium'
            issues.append({
                'task_id': row['id'],
                'task_title': row['title'],
                'issue_type': 'missing_or_short_summary',
                'severity': severity,
                'details': f"summary长度: {row['summary_length'] or 0}字",
                'quality_score': max(0, 1.0 - (50 - (row['summary_length'] or 0)) / 50)
            })
        
        # 2. 检查完成任务但缺少或过短的执行日志
        sql2 = """
            SELECT id, number, title, status, 
                   CHAR_LENGTH(execution_log) as log_length,
                   updated_at
            FROM tasks
            WHERE status = 'completed'
              AND (execution_log IS NULL OR CHAR_LENGTH(execution_log) < 200)
            ORDER BY updated_at DESC
            LIMIT 20
        """
        results2 = execute_query(sql2)
        
        for row in results2:
            severity = 'high' if not row['log_length'] or row['log_length'] < 50 else 'medium'
            issues.append({
                'task_id': row['id'],
                'task_title': row['title'],
                'issue_type': 'missing_or_short_execution_log',
                'severity': severity,
                'details': f"log长度: {row['log_length'] or 0}字",
                'quality_score': max(0, 1.0 - (200 - (row['log_length'] or 0)) / 200)
            })
        
        # 3. 检查缺少附件的任务
        sql3 = """
            SELECT t.id, t.number, t.title, t.status,
                   a.id as attachment_id
            FROM tasks t
            LEFT JOIN attachments a ON t.id = a.entity_id AND a.entity_type = 'task'
            WHERE t.status = 'completed'
              AND a.id IS NULL
              AND t.description LIKE '%产出%' OR t.description LIKE '%附件%' OR t.description LIKE '%文件%'
            ORDER BY t.updated_at DESC
            LIMIT 10
        """
        results3 = execute_query(sql3)
        
        for row in results3:
            issues.append({
                'task_id': row['id'],
                'task_title': row['title'],
                'issue_type': 'missing_attachment',
                'severity': 'medium',
                'details': '任务描述要求产出文件但无附件',
                'quality_score': 0.5
            })
        
        for issue in issues[:5]:
            logger.warning(f"质量问题: #{issue['task_id']} - {issue['issue_type']} "
                          f"(严重度: {issue['severity']}, 质量分: {issue['quality_score']:.2f})")
        
        return issues
    
    def analyze_system_health(self) -> Dict:
        """分析系统健康状态 - V4.4增强版，综合健康度评分"""
        logger.info("分析系统健康状态...")
        
        health = {
            'timestamp': datetime.now().isoformat(),
            'version': '4.4'
        }
        
        # 1. 任务状态统计
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
        
        for status_key in status_map.values():
            health[status_key] = 0
        
        for row in results:
            key = status_map.get(row['status'].lower())
            if key:
                health[key] = row['count']
        
        health['total_tasks'] = sum(health.get(k, 0) for k in status_map.values())
        
        # 2. 24小时内完成的任务
        sql2 = """
            SELECT COUNT(*) as count
            FROM tasks
            WHERE status = 'completed'
              AND updated_at >= NOW() - INTERVAL 24 HOUR
        """
        result2 = execute_query(sql2)
        if result2:
            health['completed_last_24h'] = result2[0]['count']
        
        # 3. 无任务的活跃项目
        sql3 = """
            SELECT COUNT(*) as count
            FROM projects p
            WHERE p.status = 'active'
              AND NOT EXISTS (SELECT 1 FROM tasks t WHERE t.project_id = p.id)
        """
        result3 = execute_query(sql3)
        if result3:
            health['projects_without_tasks'] = result3[0]['count']
        
        # 4. 停滞任务统计
        sql4 = """
            SELECT 
                COUNT(*) as count,
                SUM(CASE WHEN TIMESTAMPDIFF(HOUR, updated_at, NOW()) > 168 THEN 1 ELSE 0 END) as critical_count
            FROM tasks
            WHERE status IN ('pending', 'in_progress')
              AND TIMESTAMPDIFF(HOUR, updated_at, NOW()) > 24
        """
        result4 = execute_query(sql4)
        if result4:
            health['stale_tasks_count'] = result4[0]['count']
            health['critical_stale_count'] = result4[0]['critical_count']
        
        # 5. 质量指标统计
        sql5 = """
            SELECT 
                COUNT(*) as total_completed,
                SUM(CASE WHEN CHAR_LENGTH(execution_log) >= 200 THEN 1 ELSE 0 END) as log_quality_count,
                SUM(CASE WHEN CHAR_LENGTH(result_summary) >= 50 THEN 1 ELSE 0 END) as summary_quality_count
            FROM tasks
            WHERE status = 'completed'
              AND updated_at >= NOW() - INTERVAL 7 DAY
        """
        result5 = execute_query(sql5)
        if result5 and result5[0]['total_completed'] > 0:
            total = result5[0]['total_completed']
            health['log_quality_rate'] = round(result5[0]['log_quality_count'] / total, 3)
            health['summary_quality_rate'] = round(result5[0]['summary_quality_count'] / total, 3)
        else:
            health['log_quality_rate'] = 0.0
            health['summary_quality_rate'] = 0.0
        
        # V4.4: 计算综合健康度评分 (0-100)
        health_score = 100
        
        # 停滞任务扣分
        stale_ratio = health['stale_tasks_count'] / max(1, health['pending_tasks'] + health['in_progress_tasks'])
        health_score -= min(30, stale_ratio * 100)
        
        # 失败率扣分
        failure_rate = health['failed_tasks'] / max(1, health['total_tasks'])
        health_score -= min(20, failure_rate * 200)
        
        # 质量指标扣分
        health_score -= (1 - health['log_quality_rate']) * 15
        health_score -= (1 - health['summary_quality_rate']) * 15
        
        # 无任务项目扣分
        health_score -= health['projects_without_tasks'] * 5
        
        health['health_score'] = max(0, round(health_score, 1))
        
        # 健康等级
        if health['health_score'] >= 80:
            health['health_level'] = 'excellent'
        elif health['health_score'] >= 60:
            health['health_level'] = 'good'
        elif health['health_score'] >= 40:
            health['health_level'] = 'fair'
        else:
            health['health_level'] = 'poor'
        
        logger.info(f"系统健康评分: {health['health_score']}/100 (等级: {health['health_level']})")
        logger.info(f"  - pending: {health['pending_tasks']}, in_progress: {health['in_progress_tasks']}")
        logger.info(f"  - 24h完成: {health['completed_last_24h']}, 停滞: {health['stale_tasks_count']}")
        logger.info(f"  - 日志质量: {health['log_quality_rate']:.1%}, 摘要质量: {health['summary_quality_rate']:.1%}")
        
        return health
    
    def generate_task_recommendations(self) -> List[Dict]:
        """生成任务推荐列表 - V4.4增强版，智能排序"""
        logger.info("生成任务推荐...")
        
        recommendations = []
        
        # 1. 从项目缺口生成任务
        for gap in self.project_gaps:
            priority_map = {'high': 3, 'medium': 2, 'low': 1}
            priority = priority_map.get(gap['severity'], 2)
            
            rec = {
                'task_type': 'project_gap_filler',
                'priority_level': priority,
                'confidence': gap['confidence'],
                'project_id': gap['project_id'],
                'title': f"[{gap['project_name']}] 项目任务规划与补充",
                'description': f"项目状态分析发现: {gap['gap_type']}。需要为该项目规划并创建具体执行任务。\n"
                              f"项目ID: {gap['project_id']}\n"
                              f"项目描述: {gap['project_description'] or '无'}\n"
                              f"现有任务数: {gap['task_count']}\n"
                              f"活跃任务数: {gap['active_count']}\n"
                              f"已完成任务数: {gap['completed_count']}\n"
                              f"项目创建时长: {gap['project_age_days']}天",
                'source': 'analyzer_project_gap_v44'
            }
            recommendations.append(rec)
        
        # 2. 生成停滞任务处理任务
        stale_tasks = self.analyze_stale_tasks()
        high_risk_stale = [t for t in stale_tasks if t['risk_level'] in ['high', 'critical']]
        
        if high_risk_stale:
            recommendations.append({
                'task_type': 'system_maintenance',
                'priority_level': 3,
                'confidence': 0.9,
                'title': "高风险停滞任务清理与重新激活",
                'description': f"系统发现 {len(high_risk_stale)} 个高风险停滞任务（超过3天无更新）：\n"
                              + '\n'.join([f"- #{t['task_id']}: {t['title'][:40]}... ({t['hours_since_update']}h)" 
                                           for t in high_risk_stale[:5]])
                              + f"\n\n需要检查这些任务的状态，决定是继续执行、重置还是归档。",
                'source': 'analyzer_stale_tasks_v44'
            })
        
        if stale_tasks:
            recommendations.append({
                'task_type': 'system_maintenance',
                'priority_level': 2,
                'confidence': 0.7,
                'title': "停滞任务批量清理与状态更新",
                'description': f"系统发现 {len(stale_tasks)} 个停滞任务（超过24小时无更新）。\n"
                              f"- 高风险: {len(high_risk_stale)}\n"
                              f"- 中风险: {len([t for t in stale_tasks if t['risk_level'] == 'medium'])}\n"
                              f"- 低风险: {len([t for t in stale_tasks if t['risk_level'] == 'low'])}\n\n"
                              f"需要批量检查并更新这些任务的状态。",
                'source': 'analyzer_stale_tasks_batch_v44'
            })
        
        # 3. 无任务项目初始化任务
        if self.analyze_system_health().get('projects_without_tasks', 0) > 0:
            recommendations.append({
                'task_type': 'system_maintenance',
                'priority_level': 3,
                'confidence': 0.85,
                'title': "活跃项目任务初始化与规划",
                'description': f"有 {self.analyze_system_health()['projects_without_tasks']} 个活跃项目没有任何任务。"
                              f"需要为这些项目创建具体的执行任务，确保项目有序推进。",
                'source': 'analyzer_empty_projects_v44'
            })
        
        # 4. 定期系统健康检查任务
        recommendations.append({
            'task_type': 'system_health_check',
            'priority_level': 1,
            'confidence': 0.6,
            'title': "SDS系统健康检查与性能优化",
            'description': "定期检查自我驱动系统运行状态：\n"
                          "- 检查所有组件运行日志\n"
                          "- 验证数据库连接和性能\n"
                          "- 清理过期日志文件\n"
                          "- 优化系统配置参数\n"
                          "- 生成系统健康报告",
            'source': 'analyzer_regular_check_v44'
        })
        
        # 5. 知识库维护任务
        recommendations.append({
            'task_type': 'knowledge_maintenance',
            'priority_level': 2,
            'confidence': 0.75,
            'title': "系统记忆更新与知识库维护",
            'description': "整理近期执行的任务成果，更新系统知识库：\n"
                          "- 提取任务中的关键决策和经验\n"
                          "- 更新核心原则文档\n"
                          "- 归档重要执行记录\n"
                          "- 优化任务模板和验收标准",
            'source': 'analyzer_knowledge_v44'
        })
        
        # 6. 质量保证任务
        quality_issues = self.analyze_task_completion_quality()
        if quality_issues:
            high_severity = [i for i in quality_issues if i['severity'] == 'high']
            recommendations.append({
                'task_type': 'quality_assurance',
                'priority_level': 2 if len(high_severity) > 0 else 1,
                'confidence': 0.8,
                'title': "已完成任务质量检查与标准优化",
                'description': f"发现 {len(quality_issues)} 个质量问题需要处理：\n"
                              f"- 高严重度: {len(high_severity)}\n"
                              f"- 中严重度: {len([i for i in quality_issues if i['severity'] == 'medium'])}\n\n"
                              + '\n'.join([f"- #{i['task_id']}: {i['issue_type']} - {i['details']}" 
                                           for i in quality_issues[:5]]),
                'source': 'analyzer_quality_assurance_v44'
            })
        
        # V4.4: 按优先级和置信度排序
        recommendations.sort(
            key=lambda x: (x['priority_level'] * 10 + x['confidence'] * 10),
            reverse=True
        )
        
        logger.info(f"生成 {len(recommendations)} 个任务推荐 (已按优先级排序)")
        for i, rec in enumerate(recommendations[:3], 1):
            logger.info(f"  {i}. [P{rec['priority_level']}] {rec['title']} (置信度: {rec['confidence']:.2f})")
        
        return recommendations
    
    def run_full_analysis(self) -> Dict:
        """运行完整分析 - V4.4增强版"""
        logger.info("=" * 70)
        logger.info("🚀 开始 SDS 任务分析器 V4.4 完整分析")
        logger.info("=" * 70)
        
        if not self.connect():
            return {'error': '数据库连接失败'}
        
        try:
            # 执行各项分析
            project_gaps = self.analyze_active_projects()
            stale_tasks = self.analyze_stale_tasks()
            quality_issues = self.analyze_task_completion_quality()
            system_health = self.analyze_system_health()
            recommendations = self.generate_task_recommendations()
            
            # 计算分析质量评分
            analysis_quality_score = min(100, 
                len(project_gaps) * 5 + 
                len(stale_tasks) * 2 + 
                len(quality_issues) * 3 + 
                system_health.get('health_score', 0)
            )
            
            analysis_result = {
                'version': '4.4',
                'timestamp': datetime.now().isoformat(),
                'analysis_quality_score': round(analysis_quality_score, 1),
                'summary': {
                    'project_gaps_count': len(project_gaps),
                    'stale_tasks_count': len(stale_tasks),
                    'quality_issues_count': len(quality_issues),
                    'recommendations_count': len(recommendations),
                    'system_health_score': system_health.get('health_score', 0),
                    'system_health_level': system_health.get('health_level', 'unknown')
                },
                'system_health': system_health,
                'project_gaps': project_gaps,
                'stale_tasks': stale_tasks,
                'quality_issues': quality_issues,
                'recommendations': recommendations
            }
            
            # 保存分析结果
            output_file = Path("/Users/mettlyz/.openclaw/workspace/logs/sds-analysis-v44-latest.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ 分析完成，结果已保存到 {output_file}")
            logger.info(f"📊 分析质量评分: {analysis_quality_score:.1f}/100")
            logger.info(f"🏥 系统健康等级: {system_health.get('health_level', 'unknown')}")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ 分析异常: {e}", exc_info=True)
            return {'error': str(e)}
        finally:
            self.close()
            logger.info("=" * 70)


if __name__ == "__main__":
    print("=" * 70)
    print("  SDS 任务分析器 V4.4")
    print("  核心功能: 智能缺口识别 | 质量评估 | 健康评分 | 任务推荐")
    print("=" * 70)
    
    analyzer = TaskAnalyzerV44()
    result = analyzer.run_full_analysis()
    
    if 'error' in result:
        print(f"\n❌ 分析失败: {result['error']}")
    else:
        print(f"\n✅ 分析成功!")
        print(f"   分析质量评分: {result['analysis_quality_score']}/100")
        print(f"   系统健康评分: {result['summary']['system_health_score']}/100")
        print(f"   系统健康等级: {result['summary']['system_health_level']}")
        print(f"\n   📋 分析摘要:")
        print(f"   - 项目缺口: {result['summary']['project_gaps_count']} 个")
        print(f"   - 停滞任务: {result['summary']['stale_tasks_count']} 个")
        print(f"   - 质量问题: {result['summary']['quality_issues_count']} 个")
        print(f"   - 任务推荐: {result['summary']['recommendations_count']} 个")
        
        print(f"\n   🎯 优先级最高的 3 个推荐任务:")
        for i, rec in enumerate(result['recommendations'][:3], 1):
            print(f"   {i}. [P{rec['priority_level']}] {rec['title']}")
    
    print("\n" + "=" * 70)

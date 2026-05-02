#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS自动任务生成器 V4.6 (集成三重保障)
Auto Task Generator with Three-Layer Guard Integration

基于Tavily Research优化：
- 2026年主流Agent调度系统采用"幂等性 + 频率限制 + 去重校验"三层保障
- 参考OpenAI Swarm框架任务生成最佳实践

功能：
1. 根据分析结果自动创建高质量看板任务
2. 集成V4.6三重保障系统（频率限制/语义去重/幂等性）
3. 支持批量任务生成与过滤
4. 完整的审计日志与生成统计
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "core"))

from lib.db_connector import get_db_connection, execute_query, execute_update

# 导入V4.6三重保障
from core.task_generation_guard_v46 import TaskGenerationGuard, GuardDecision

# 日志配置
LOG_DIR = Path("/Users/mettlyz/.openclaw/workspace/logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'sds-auto-task-generator-v46.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AutoTaskGeneratorV46')


class AutoTaskGeneratorV46:
    """自动任务生成器 V4.6 - 集成三重保障"""
    
    def __init__(self, use_guard: bool = True):
        self.conn = None
        self.generated_tasks = []
        self.blocked_tasks = []
        self.use_guard = use_guard
        self.guard = TaskGenerationGuard() if use_guard else None
        
        # 任务模板库
        self.task_templates = {
            'system_maintenance': {
                'priority_mapping': {'high': 3, 'medium': 2, 'low': 1},
                'default_description': """
【执行要点】
1. 仔细分析当前系统状态
2. 按照优先级执行必要的维护操作
3. 记录所有变更和执行结果
4. 验证维护效果

【验收标准】
- execution_log ≥ 200字，详细记录执行过程
- result_summary ≥ 50字，总结核心成果
- 产出文件已保存并上传到附件
                """.strip()
            },
            'project_gap_filler': {
                'priority_mapping': {'high': 3, 'medium': 2, 'low': 1},
                'default_description': """
【执行要点】
1. 分析项目当前状态和目标
2. 拆解为具体可执行的子任务
3. 为每个子任务设置明确的验收标准
4. 创建任务并关联到对应项目

【验收标准】
- 至少创建3个具体的执行任务
- 每个任务都有明确的完成标准
- 任务优先级和依赖关系清晰
                """.strip()
            },
            'knowledge_maintenance': {
                'priority_mapping': {'high': 3, 'medium': 2, 'low': 1},
                'default_description': """
【执行要点】
1. 梳理近期执行的任务成果
2. 提取关键决策、经验教训、最佳实践
3. 更新对应领域的知识库文档
4. 整理归档重要执行记录

【验收标准】
- 至少更新1个核心知识文档
- 提炼至少3条关键经验
- 产出文件已保存并上传
                """.strip()
            },
            'academic_research': {
                'priority_mapping': {'high': 3, 'medium': 2, 'low': 1},
                'default_description': """
【执行要点】
1. 确定研究主题和关键词
2. 使用学术搜索工具获取最新文献
3. 分析研究热点和趋势
4. 生成研究报告或综述

【验收标准】
- 至少检索20篇相关文献
- 完整的研究分析报告
- 关键发现和建议清晰
                """.strip()
            }
        }
    
    def connect(self) -> bool:
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
            self.conn = None
    
    def get_default_goal_id(self) -> int:
        """获取默认目标ID"""
        return 7  # 系统维护目标
    
    def _build_description(self, task_data: Dict) -> str:
        """构建任务描述"""
        template_type = task_data.get('task_type', 'system_maintenance')
        template = self.task_templates.get(template_type, self.task_templates['system_maintenance'])
        
        user_desc = task_data.get('description', '')
        default_desc = template['default_description']
        
        if user_desc:
            return f"{user_desc}\n\n{default_desc}"
        return default_desc
    
    def create_single_task(self, task_data: Dict) -> Optional[int]:
        """
        创建单个任务（带三重保障）
        
        Returns:
            task_id or None
        """
        title = task_data.get('title', '')
        if not title:
            logger.warning("任务标题为空，跳过")
            return None
        
        goal_id = task_data.get('goal_id') or self.get_default_goal_id()
        description = self._build_description(task_data)
        priority = task_data.get('priority', 2)
        task_type = task_data.get('task_type', 'auto_generated_v4.6')
        execution_mode = task_data.get('execution_mode', 'auto')
        due_date = task_data.get('due_date')
        
        # 三重保障检查
        if self.use_guard and self.guard:
            guard_result = self.guard.check(title, goal_id, description)
            
            if not guard_result.can_generate:
                blocked_info = {
                    'title': title,
                    'goal_id': goal_id,
                    'reason': guard_result.reason,
                    'decision': guard_result.decision.value,
                    'timestamp': datetime.now().isoformat()
                }
                self.blocked_tasks.append(blocked_info)
                logger.warning(f"⛔ 任务被保障系统拦截: {title[:60]} - {guard_result.reason}")
                return None
            
            logger.info(f"✅ 任务通过三重保障检查: {title[:60]}")
        
        # 创建任务
        try:
            sql = """
                INSERT INTO tasks
                (title, description, status, priority, goal_id, task_type,
                 execution_mode, due_date, created_at, updated_at)
                VALUES (%s, %s, 'pending', %s, %s, %s, %s, %s, NOW(), NOW())
            """
            execute_update(sql, (
                title, description, priority, goal_id,
                task_type, execution_mode, due_date
            ))
            
            # 获取task_id
            result = execute_query("SELECT LAST_INSERT_ID() as id")
            task_id = result[0]['id'] if result else None
            
            if task_id:
                # 记录幂等性
                if self.use_guard and self.guard:
                    idem_key = self.guard.idempotency.generate_key(title, goal_id, description)
                    self.guard.idempotency.record(idem_key, task_id, title, goal_id)
                
                self.generated_tasks.append({
                    'id': task_id,
                    'title': title,
                    'goal_id': goal_id,
                    'created_at': datetime.now().isoformat()
                })
                
                logger.info(f"✅ 成功创建任务 #{task_id}: {title[:60]}")
                return task_id
            
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
        
        return None
    
    def create_tasks_from_recommendations(self, recommendations: List[Dict]) -> Dict:
        """
        根据推荐列表批量创建任务
        
        Returns:
            生成统计字典
        """
        logger.info(f"开始V4.6批量任务生成: 共 {len(recommendations)} 个推荐")
        
        created_ids = []
        blocked_count = 0
        error_count = 0
        
        for rec in recommendations:
            try:
                task_id = self.create_single_task(rec)
                if task_id:
                    created_ids.append(task_id)
                else:
                    blocked_count += 1
            except Exception as e:
                logger.error(f"处理推荐时出错: {e}")
                error_count += 1
        
        stats = {
            'total_recommendations': len(recommendations),
            'created': len(created_ids),
            'blocked': blocked_count,
            'errors': error_count,
            'created_ids': created_ids,
            'block_rate': blocked_count / len(recommendations) * 100 if recommendations else 0
        }
        
        logger.info(f"批量生成完成: {stats['created']}成功, {stats['blocked']}被拦截, {stats['errors']}错误")
        return stats
    
    def run_generation(self, recommendations: List[Dict] = None) -> Dict:
        """运行任务生成流程"""
        logger.info("=" * 70)
        logger.info("SDS自动任务生成器 V4.6 启动")
        logger.info("=" * 70)
        
        if not self.connect():
            return {'error': '数据库连接失败'}
        
        try:
            # 如果没有推荐，尝试加载分析结果
            if not recommendations:
                recommendations = self._load_default_recommendations()
            
            if not recommendations:
                logger.warning("没有推荐任务可生成")
                return {'error': '没有推荐任务'}
            
            # 批量生成
            stats = self.create_tasks_from_recommendations(recommendations)
            
            # 保存生成记录
            generation_record = {
                'timestamp': datetime.now().isoformat(),
                'version': 'V4.6',
                'guard_enabled': self.use_guard,
                'statistics': stats,
                'generated_tasks': self.generated_tasks,
                'blocked_tasks': self.blocked_tasks,
                'guard_batch_id': self.guard.batch_id if self.guard else None
            }
            
            output_file = LOG_DIR / 'sds-generation-v46-latest.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(generation_record, f, indent=2, ensure_ascii=False)
            
            logger.info(f"生成记录已保存: {output_file}")
            return generation_record
            
        except Exception as e:
            logger.error(f"生成异常: {e}")
            return {'error': str(e)}
        finally:
            self.close()
            logger.info("=" * 70)
    
    def _load_default_recommendations(self) -> List[Dict]:
        """加载默认推荐（从分析结果文件）"""
        analysis_file = LOG_DIR / 'sds-analysis-latest.json'
        if not analysis_file.exists():
            return []
        
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('recommendations', [])
        except Exception as e:
            logger.error(f"加载分析结果失败: {e}")
            return []
    
    def get_generation_stats(self, hours: int = 24) -> Dict:
        """获取任务生成统计"""
        try:
            sql = """
                SELECT
                    COUNT(*) as total_generated,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status IN ('pending', 'in_progress') THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM tasks
                WHERE task_type LIKE 'auto_generated%%'
                  AND created_at >= NOW() - INTERVAL %s HOUR
            """
            results = execute_query(sql, (hours,))
            return results[0] if results else {}
        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return {}


def generate_tasks_with_guard(recommendations: List[Dict], use_guard: bool = True) -> Dict:
    """便捷函数：带保障的任务生成"""
    generator = AutoTaskGeneratorV46(use_guard=use_guard)
    return generator.run_generation(recommendations)


if __name__ == "__main__":
    print("=" * 70)
    print("SDS自动任务生成器 V4.6 - 集成三重保障")
    print("=" * 70)
    
    # 测试推荐
    test_recommendations = [
        {
            'title': 'T1: AI助手优化 - SDS调度系统V4.6测试任务',
            'goal_id': 1,
            'description': '测试三重保障系统的任务生成',
            'priority': 2,
            'task_type': 'system_maintenance'
        },
        {
            'title': 'T2: 和光智成商业化 - 融资BP更新V4.6',
            'goal_id': 2,
            'description': '更新商业计划书',
            'priority': 3,
            'task_type': 'project_gap_filler'
        },
        {
            'title': 'T7: 系统维护 - 三重保障审计日志检查',
            'goal_id': 7,
            'description': '检查审计日志完整性',
            'priority': 2,
            'task_type': 'system_maintenance'
        }
    ]
    
    generator = AutoTaskGeneratorV46(use_guard=True)
    result = generator.run_generation(test_recommendations)
    
    print("\n生成结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

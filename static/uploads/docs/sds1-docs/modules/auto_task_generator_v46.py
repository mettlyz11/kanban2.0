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

from lib.db_connector import get_db_connection, execute_query, execute_update, execute_insert_with_id

# 导入V4.6三重保障
from core.task_generation_guard_v46 import TaskGenerationGuard, GuardDecision
from config_loader import get_config

# 日志配置
LOG_DIR = Path(get_config('paths.logs'))
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
- execution_log ≥ 500字，详细记录执行过程
- result_summary ≥ 300字，总结核心成果
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
        
        # 方案2：任务元数据内嵌强制要求
        MANDATORY_PREFIX = """═══════════════════════════════════════════
🔥🔥🔥 【强制执行要求 - 必须遵守】 🔥🔥🔥
═══════════════════════════════════════════

⚠️ 不满足以下要求 → 任务直接失败 → 自动重试

🔴 execution_log ≥ 500字（详细记录每一步执行过程）
🔴 result_summary ≥ 300字（详细总结核心成果）
🔴 task_summary ≥ 50字（简洁描述任务成果）

❌ 字数不够 = 任务失败 = 重新执行 = 继续失败...
✅ 只有写满字数，任务才能通过验收！

═══════════════════════════════════════════

【任务描述】
"""
        description = MANDATORY_PREFIX + description
        
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
            # 加时间戳后缀避免唯一键冲突
            ts = datetime.now().strftime('%m%d%H%M')
            unique_title = f"{title} [{ts}]" if len(title) < 100 else f"{title[:97]}[{ts}]"
            
            sql = """
                INSERT INTO tasks
                (title, description, status, priority, goal_id, project_id, task_type,
                 execution_mode, due_date, created_at, updated_at)
                VALUES (%s, %s, 'pending', %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            project_id = task_data.get('project_id')
            task_id = execute_insert_with_id(sql, (
                unique_title, description, priority, goal_id, project_id,
                task_type, execution_mode, due_date
            ))
            logger.info(f"[DEBUG] task_id={task_id}")
            
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
            import traceback
            logger.error(f"创建任务失败: {e}")
            logger.error(f"[DEBUG] 堆栈: {traceback.format_exc()}")
            logger.error(f"[DEBUG] title={title[:50]}, goal_id={goal_id}, task_type={task_type}")
        
        return None
    
    def create_tasks_from_recommendations(self, recommendations: List[Dict]) -> Dict:
        """
        根据推荐列表批量创建任务（均衡分布版）
        
        规则：
        1. 每个目标每周期最多生成 ceil(target_count / 7) 个任务
        2. 优先为任务数少的目标生成任务
        3. 确保7个目标均匀获得新任务
        
        Returns:
            生成统计字典
        """
        # ✅ 修改：减少生成数量，pending < 10 时才生成
        target_count = 4  # 每周期最多生成4个任务（pending < 10时）
        max_per_goal = max(1, target_count // 7 + (1 if target_count % 7 > 0 else 0))  # 每个目标最多1个
        
        logger.info(f"开始V4.6批量任务生成: 共 {len(recommendations)} 个推荐，目标 {target_count} 个，每目标最多 {max_per_goal} 个")
        
        created_ids = []
        blocked_count = 0
        error_count = 0
        blocked_titles = []  # 记录被拦截的任务标题，用于备用推荐时排除
        
        # ✅ 新增：统计每个目标已创建的任务数
        goal_created_counts = {}
        
        # 按 goal_id 对推荐进行分组
        goal_recommendations = {}
        for rec in recommendations:
            gid = rec.get('goal_id', 7)
            goal_recommendations.setdefault(gid, []).append(rec)
        
        logger.info(f"📊 推荐分布: { {k: len(v) for k, v in goal_recommendations.items()} }")
        
        # 第一轮：均匀处理每个目标的推荐
        # 按目标ID循环，确保每个目标都有机会
        sorted_goals = sorted(goal_recommendations.keys())
        round_num = 0
        while len(created_ids) < target_count:
            round_num += 1
            any_created_this_round = False
            
            for goal_id in sorted_goals:
                if len(created_ids) >= target_count:
                    break
                if goal_created_counts.get(goal_id, 0) >= max_per_goal:
                    continue  # 该目标已达到上限
                
                goal_recs = goal_recommendations.get(goal_id, [])
                rec_idx = goal_created_counts.get(goal_id, 0)
                
                if rec_idx < len(goal_recs):
                    rec = goal_recs[rec_idx]
                    try:
                        task_id = self.create_single_task(rec)
                        if task_id:
                            created_ids.append(task_id)
                            goal_created_counts[goal_id] = goal_created_counts.get(goal_id, 0) + 1
                            any_created_this_round = True
                            logger.info(f"✅ 目标{goal_id}: 已创建 {goal_created_counts[goal_id]} 个")
                        else:
                            blocked_count += 1
                            blocked_titles.append(rec.get('title', ''))
                    except Exception as e:
                        logger.error(f"处理推荐时出错: {e}")
                        error_count += 1
            
            # 如果一轮下来没有任何新创建，说明没有更多可创建的任务了
            if not any_created_this_round:
                logger.info("一轮结束，无新任务可创建")
                break
            
            # 安全检查：最多循环10轮
            if round_num > 10:
                logger.warning("达到最大循环轮数，停止生成")
                break
        
        logger.info(f"📊 第一轮生成完成: {len(created_ids)} 个任务，分布: {goal_created_counts}")
        
        # ==================== 备用推荐补充（保持均衡）====================
        # 如果成功创建的太少，尝试获取备用推荐，但优先补充任务少的目标
        if len(created_ids) < target_count:
            logger.warning(f"⚠️ 只成功创建 {len(created_ids)} 个，尝试从其他项目补充...")
            
            try:
                import sys
                sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
                from project_gap_analyzer import ProjectGapAnalyzer
                
                gap_analyzer = ProjectGapAnalyzer()
                backup_recs = gap_analyzer.get_backup_recommendations(
                    exclude_titles=blocked_titles,
                    limit=target_count * 3
                )
                
                if backup_recs:
                    logger.info(f"📦 获取到 {len(backup_recs)} 个备用推荐")
                    
                    # 按 goal_id 分组备用推荐
                    backup_by_goal = {}
                    for rec in backup_recs:
                        gid = rec.get('goal_id', 7)
                        backup_by_goal.setdefault(gid, []).append(rec)
                    
                    # 优先补充任务数少的目标
                    for _ in range(3):  # 最多3轮
                        if len(created_ids) >= target_count:
                            break
                        
                        # 找出任务数最少的目标
                        goal_counts_sorted = sorted(
                            [(gid, goal_created_counts.get(gid, 0)) for gid in range(1, 8)],
                            key=lambda x: x[1]
                        )
                        
                        for goal_id, count in goal_counts_sorted:
                            if len(created_ids) >= target_count:
                                break
                            if count >= max_per_goal:
                                continue
                            
                            goal_backups = backup_by_goal.get(goal_id, [])
                            used_count = goal_created_counts.get(goal_id, 0)
                            
                            if used_count < len(goal_backups):
                                rec = goal_backups[used_count]
                                try:
                                    task_id = self.create_single_task(rec)
                                    if task_id:
                                        created_ids.append(task_id)
                                        goal_created_counts[goal_id] = goal_created_counts.get(goal_id, 0) + 1
                                        logger.info(f"✅ 补充: 目标{goal_id} -> {rec.get('title', '')[:40]}")
                                    else:
                                        blocked_count += 1
                                except Exception as e:
                                    logger.error(f"处理备用推荐时出错: {e}")
                                    error_count += 1
                    
                    logger.info(f"📊 补充后总计: {len(created_ids)} 个，分布: {goal_created_counts}")
                else:
                    logger.info("没有可用的备用推荐")
                    
            except Exception as e:
                logger.error(f"获取备用推荐时出错: {e}")
        
        # ==================== 最终检查：如果还是没有任务，强制降低相似度阈值 ====================
        if len(created_ids) == 0:
            logger.error("🚨 严重：没有任何任务被创建！系统不能空跑，强制降低相似度阈值重试...")
            
            try:
                # 临时降低相似度阈值，从主推荐中重试
                if self.use_guard and self.guard:
                    original_threshold = self.guard.dedup.similarity_threshold
                    self.guard.dedup.similarity_threshold = 0.1  # 临时大幅降低阈值，确保能创建
                    logger.info(f"🔧 临时降低相似度阈值: {original_threshold} → 0.3")
                    
                    for rec in recommendations[:10]:  # 只重试前10个
                        try:
                            task_id = self.create_single_task(rec)
                            if task_id:
                                created_ids.append(task_id)
                                logger.info(f"✅ 降低阈值后成功创建任务: {rec.get('title', '')[:50]}")
                                if len(created_ids) >= 3:
                                    break  # 创建3个就够了
                        except Exception as e:
                            pass
                    
                    # 恢复原阈值
                    self.guard.dedup.similarity_threshold = original_threshold
                    logger.info(f"🔧 恢复相似度阈值: {original_threshold}")
            except Exception as e:
                logger.error(f"强制重试时出错: {e}")
        
        stats = {
            'total_recommendations': len(recommendations),
            'created': len(created_ids),
            'blocked': blocked_count,
            'errors': error_count,
            'created_ids': created_ids,
            'block_rate': blocked_count / len(recommendations) * 100 if recommendations else 0
        }
        
        if stats['created'] == 0:
            logger.error("🚨 最终还是没有成功创建任何任务！请检查系统状态")
        else:
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
            
            # 安全层：如果 recommendations 是字符串，尝试 JSON 解析
            if isinstance(recommendations, str):
                try:
                    recommendations = json.loads(recommendations)
                    logger.info("成功解析字符串格式的推荐列表")
                except json.JSONDecodeError as e:
                    logger.error(f"推荐列表字符串解析失败: {e}")
                    return {'error': '推荐列表格式错误'}
            
            # 安全层：如果 recommendations 是字典但有 recommendations 键，提取出来
            if isinstance(recommendations, dict) and 'recommendations' in recommendations:
                recommendations = recommendations['recommendations']
                logger.info("从字典中提取推荐列表")
            
            # 确保是列表
            if not isinstance(recommendations, list):
                logger.error(f"推荐列表格式错误: 期望 list，实际得到 {type(recommendations)}")
                return {'error': '推荐列表格式错误'}
            
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
    # print("=" * 70)
    # print("SDS自动任务生成器 V4.6 - 集成三重保障")
    # print("=" * 70)
    
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
    
    # print("\n生成结果:")
    # print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

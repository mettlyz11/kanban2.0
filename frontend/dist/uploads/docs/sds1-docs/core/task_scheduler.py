"""
任务智能调度引擎 - SDS System v2.0
支持优先级动态调整、依赖关系自动解析
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import IntEnum
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TaskScheduler')


class PriorityLevel(IntEnum):
    """优先级枚举"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    BLOCKER = 5


@dataclass
class TaskDependency:
    """任务依赖关系"""
    task_id: int
    depends_on_task_id: int
    dependency_type: str = "required"  # required, optional
    created_at: datetime = None


@dataclass
class ScheduledTask:
    """调度任务"""
    task_id: int
    title: str
    priority_score: float
    priority_level: PriorityLevel
    dependencies: List[int]
    dependencies_completed: bool
    waiting_hours: float
    estimated_execution_time: float


class TaskScheduler:
    """
    任务智能调度引擎
    
    功能：
    1. 计算任务优先级分数
    2. 动态调整任务优先级
    3. 解析任务依赖关系
    4. 检查依赖完成状态
    5. 构建优化的执行队列
    """
    
    def __init__(self, db_connection=None):
        """
        初始化调度引擎
        
        Args:
            db_connection: 数据库连接对象
        """
        self.db = db_connection
        self.priority_weights = {
            'urgency': 0.4,      # 紧急度权重
            'importance': 0.3,   # 重要度权重
            'dependency_count': 0.2,  # 被依赖数量权重
            'waiting_time': 0.1  # 等待时间权重
        }
        self.default_timeout_hours = 24
        logger.info("TaskScheduler initialized")
    
    def _get_db_connection(self):
        """获取数据库连接"""
        if self.db is None:
            from lib.db_connector import get_db_connection
            self.db = get_db_connection()
        return self.db
    
    def calculate_priority_score(self, task_id: int) -> float:
        """
        计算任务优先级分数
        
        公式：
        优先级分数 = (紧急度 × 0.4) + (重要度 × 0.3) + (依赖任务数 × 0.2) + (等待时间因子 × 0.1)
        
        Args:
            task_id: 任务ID
            
        Returns:
            float: 优先级分数 (0.0 - 10.0)
        """
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # 获取任务基本信息
            cursor.execute("""
                SELECT id, title, description, priority, status, due_date, 
                       created_at, updated_at, goal_id
                FROM tasks 
                WHERE id = %s
            """, (task_id,))
            task = cursor.fetchone()
            
            if not task:
                logger.warning(f"Task {task_id} not found")
                return 0.0
            
            # 1. 计算紧急度 (0-10分)
            urgency_score = self._calculate_urgency(task)
            
            # 2. 计算重要度 (0-10分)
            importance_score = self._calculate_importance(task)
            
            # 3. 计算被依赖数量因子 (0-10分)
            dependency_score = self._calculate_dependency_factor(task_id)
            
            # 4. 计算等待时间因子 (0-10分)
            waiting_score = self._calculate_waiting_factor(task)
            
            # 加权计算总分数
            total_score = (
                urgency_score * self.priority_weights['urgency'] +
                importance_score * self.priority_weights['importance'] +
                dependency_score * self.priority_weights['dependency_count'] +
                waiting_score * self.priority_weights['waiting_time']
            )
            
            # 归一化到0-10范围
            final_score = min(10.0, max(0.0, total_score))
            
            logger.info(
                f"Task {task_id} priority calculation: "
                f"urgency={urgency_score:.2f}, importance={importance_score:.2f}, "
                f"dependency={dependency_score:.2f}, waiting={waiting_score:.2f}, "
                f"total={final_score:.2f}"
            )
            
            return final_score
            
        except Exception as e:
            logger.error(f"Error calculating priority for task {task_id}: {e}")
            return 0.0
        finally:
            cursor.close()
    
    def _calculate_urgency(self, task: Dict) -> float:
        """计算紧急度分数"""
        due_date = task.get('due_date')
        if not due_date:
            return 5.0  # 默认中等紧急度
        
        now = datetime.now()
        time_to_due = due_date - now
        
        if time_to_due.total_seconds() <= 0:
            return 10.0  # 已过期
        elif time_to_due.days <= 1:
            return 9.0
        elif time_to_due.days <= 3:
            return 7.0
        elif time_to_due.days <= 7:
            return 5.0
        elif time_to_due.days <= 14:
            return 3.0
        else:
            return 1.0
    
    def _calculate_importance(self, task: Dict) -> float:
        """计算重要度分数"""
        # 基于任务原始priority字段
        base_priority = task.get('priority', 2)  # 默认medium
        
        # 基于战略目标关联
        goal_id = task.get('goal_id')
        goal_factor = 1.5 if goal_id else 1.0
        
        # 基于标题关键词分析
        title = task.get('title', '').lower()
        keywords = ['紧急', '重要', '关键', '核心', '必须', '立即', 'critical', 'important', 'urgent']
        keyword_factor = 1.0
        for keyword in keywords:
            if keyword in title:
                keyword_factor = 1.3
                break
        
        # 计算重要度
        base_score = (base_priority - 1) * 2.5  # 1→0, 2→2.5, 3→5.0, 4→7.5, 5→10
        importance_score = min(10.0, base_score * goal_factor * keyword_factor)
        
        return importance_score
    
    def _calculate_dependency_factor(self, task_id: int) -> float:
        """计算被依赖数量因子"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 查询有多少任务依赖此任务
            cursor.execute("""
                SELECT COUNT(*) 
                FROM task_dependencies 
                WHERE depends_on_task_id = %s
            """, (task_id,))
            count = cursor.fetchone()[0]
            
            # 归一化到0-10分
            if count == 0:
                return 0.0
            elif count == 1:
                return 3.0
            elif count == 2:
                return 6.0
            elif count >= 3:
                return 10.0
            
        except Exception as e:
            logger.error(f"Error calculating dependency factor: {e}")
            return 0.0
        finally:
            cursor.close()
    
    def _calculate_waiting_factor(self, task: Dict) -> float:
        """计算等待时间因子"""
        created_at = task.get('created_at')
        if not created_at:
            return 0.0
        
        now = datetime.now()
        waiting_hours = (now - created_at).total_seconds() / 3600
        
        # 归一化到0-10分（24小时达到满分）
        waiting_score = min(10.0, (waiting_hours / 24) * 10)
        
        return waiting_score
    
    def adjust_priority_dynamically(self, task_id: int) -> bool:
        """
        动态调整任务优先级
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功调整
        """
        try:
            # 计算新的优先级分数
            new_score = self.calculate_priority_score(task_id)
            
            # 确定优先级级别
            if new_score >= 8.0:
                new_level = PriorityLevel.BLOCKER
            elif new_score >= 6.0:
                new_level = PriorityLevel.CRITICAL
            elif new_score >= 4.0:
                new_level = PriorityLevel.HIGH
            elif new_score >= 2.0:
                new_level = PriorityLevel.MEDIUM
            else:
                new_level = PriorityLevel.LOW
            
            # 更新数据库
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE tasks 
                SET priority_score = %s, 
                    priority = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (new_score, int(new_level), task_id))
            
            conn.commit()
            cursor.close()
            
            logger.info(
                f"Task {task_id} priority adjusted: "
                f"score={new_score:.2f}, level={new_level.name}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error adjusting priority for task {task_id}: {e}")
            return False
    
    def parse_dependencies(self, task_id: int) -> List[TaskDependency]:
        """
        解析任务依赖关系
        
        从任务描述中自动提取依赖关系，或从数据库中读取已定义的依赖
        
        Args:
            task_id: 任务ID
            
        Returns:
            List[TaskDependency]: 任务依赖关系列表
        """
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        dependencies = []
        
        try:
            # 1. 从数据库读取已定义的依赖
            cursor.execute("""
                SELECT task_id, depends_on_task_id, dependency_type, created_at
                FROM task_dependencies
                WHERE task_id = %s
            """, (task_id,))
            
            for row in cursor.fetchall():
                dependency = TaskDependency(
                    task_id=row['task_id'],
                    depends_on_task_id=row['depends_on_task_id'],
                    dependency_type=row['dependency_type'],
                    created_at=row['created_at']
                )
                dependencies.append(dependency)
            
            # 2. 从任务描述中自动提取潜在依赖
            cursor.execute("""
                SELECT description, title
                FROM tasks
                WHERE id = %s
            """, (task_id,))
            task = cursor.fetchone()
            
            if task and task.get('description'):
                auto_deps = self._extract_dependencies_from_text(
                    task_id, 
                    task.get('description', '') + ' ' + task.get('title', '')
                )
                dependencies.extend(auto_deps)
            
            logger.info(f"Task {task_id} has {len(dependencies)} dependencies")
            
            return dependencies
            
        except Exception as e:
            logger.error(f"Error parsing dependencies for task {task_id}: {e}")
            return []
        finally:
            cursor.close()
    
    def _extract_dependencies_from_text(self, task_id: int, text: str) -> List[TaskDependency]:
        """从文本中提取潜在的任务依赖关系"""
        import re
        dependencies = []
        
        # 查找类似 "依赖任务 #123" 或 "depends on task #456" 的模式
        patterns = [
            r'[依赖依賴].*?#(\d+)',
            r'depend.*?#(\d+)',
            r'完成.*?#(\d+).*后',
            r'after.*?#(\d+)',
            r'前置.*?#(\d+)',
            r'prerequisite.*?#(\d+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    depends_on_id = int(match)
                    # 检查依赖任务是否存在
                    conn = self._get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM tasks WHERE id = %s", (depends_on_id,))
                    if cursor.fetchone():
                        dependency = TaskDependency(
                            task_id=task_id,
                            depends_on_task_id=depends_on_id,
                            dependency_type='auto_detected',
                            created_at=datetime.now()
                        )
                        dependencies.append(dependency)
                    cursor.close()
                except ValueError:
                    continue
        
        return dependencies
    
    def check_dependency_completion(self, task_id: int) -> Tuple[bool, List[int]]:
        """
        检查依赖任务完成状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Tuple[bool, List[int]]: (是否所有必需依赖完成, 未完成的依赖任务ID列表)
        """
        dependencies = self.parse_dependencies(task_id)
        
        if not dependencies:
            return (True, [])
        
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        incomplete_deps = []
        
        try:
            for dep in dependencies:
                # 只检查必需的依赖
                if dep.dependency_type not in ['required', 'auto_detected']:
                    continue
                    
                cursor.execute("""
                    SELECT status
                    FROM tasks
                    WHERE id = %s
                """, (dep.depends_on_task_id,))
                result = cursor.fetchone()
                
                if not result or result['status'] not in ['completed', 'done']:
                    incomplete_deps.append(dep.depends_on_task_id)
            
            all_completed = len(incomplete_deps) == 0
            
            if all_completed:
                logger.info(f"Task {task_id}: All dependencies completed")
            else:
                logger.info(f"Task {task_id}: Incomplete dependencies: {incomplete_deps}")
            
            return (all_completed, incomplete_deps)
            
        except Exception as e:
            logger.error(f"Error checking dependency completion for task {task_id}: {e}")
            return (False, [])
        finally:
            cursor.close()
    
    def get_next_executable_task(self) -> Optional[ScheduledTask]:
        """
        获取下一个可执行的任务
        
        条件：
        1. 任务状态为 pending 或 ready
        2. 所有必需依赖已完成
        3. 按优先级分数排序
        
        Returns:
            Optional[ScheduledTask]: 下一个可执行的任务
        """
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # 获取所有待处理任务
            cursor.execute("""
                SELECT id, title, status, created_at, priority, priority_score
                FROM tasks
                WHERE status IN ('pending', 'ready', 'queued')
                ORDER BY priority_score DESC, created_at ASC
            """)
            
            tasks = cursor.fetchall()
            
            for task in tasks:
                task_id = task['id']
                
                # 检查依赖是否完成
                deps_completed, _ = self.check_dependency_completion(task_id)
                
                if deps_completed:
                    # 计算等待时间
                    waiting_hours = 0.0
                    if task['created_at']:
                        waiting_hours = (datetime.now() - task['created_at']).total_seconds() / 3600
                    
                    # 确定优先级级别
                    priority_score = task.get('priority_score', 0.0) or self.calculate_priority_score(task_id)
                    
                    if priority_score >= 8.0:
                        level = PriorityLevel.BLOCKER
                    elif priority_score >= 6.0:
                        level = PriorityLevel.CRITICAL
                    elif priority_score >= 4.0:
                        level = PriorityLevel.HIGH
                    elif priority_score >= 2.0:
                        level = PriorityLevel.MEDIUM
                    else:
                        level = PriorityLevel.LOW
                    
                    # 获取依赖列表
                    deps = self.parse_dependencies(task_id)
                    dep_ids = [d.depends_on_task_id for d in deps]
                    
                    scheduled_task = ScheduledTask(
                        task_id=task_id,
                        title=task['title'],
                        priority_score=priority_score,
                        priority_level=level,
                        dependencies=dep_ids,
                        dependencies_completed=True,
                        waiting_hours=waiting_hours,
                        estimated_execution_time=2.0  # 默认2小时
                    )
                    
                    logger.info(f"Next executable task: Task {task_id} - {task['title']}")
                    return scheduled_task
            
            logger.info("No executable tasks found")
            return None
            
        except Exception as e:
            logger.error(f"Error getting next executable task: {e}")
            return None
        finally:
            cursor.close()
    
    def build_execution_queue(self, max_tasks: int = 10) -> List[ScheduledTask]:
        """
        构建执行队列
        
        Args:
            max_tasks: 最大任务数
            
        Returns:
            List[ScheduledTask]: 优化的执行队列
        """
        queue = []
        processed_tasks = set()
        
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # 获取所有待处理任务，按优先级预排序
            cursor.execute("""
                SELECT id, title, status, created_at, priority, priority_score
                FROM tasks
                WHERE status IN ('pending', 'ready', 'queued')
                ORDER BY priority_score DESC, created_at ASC
            """)
            
            candidate_tasks = cursor.fetchall()
            
            for task in candidate_tasks:
                if len(queue) >= max_tasks:
                    break
                    
                task_id = task['id']
                
                if task_id in processed_tasks:
                    continue
                
                # 检查依赖是否完成
                deps_completed, incomplete_deps = self.check_dependency_completion(task_id)
                
                if not deps_completed:
                    # 依赖未完成，先处理依赖
                    for dep_id in incomplete_deps:
                        if dep_id not in processed_tasks:
                            # 递归检查依赖任务
                            dep_task = self._get_task_info(dep_id)
                            if dep_task:
                                # 先确保依赖任务在队列中
                                pass
                    continue
                
                # 计算优先级分数
                priority_score = task.get('priority_score', 0.0)
                if priority_score == 0.0:
                    priority_score = self.calculate_priority_score(task_id)
                
                # 确定优先级级别
                if priority_score >= 8.0:
                    level = PriorityLevel.BLOCKER
                elif priority_score >= 6.0:
                    level = PriorityLevel.CRITICAL
                elif priority_score >= 4.0:
                    level = PriorityLevel.HIGH
                elif priority_score >= 2.0:
                    level = PriorityLevel.MEDIUM
                else:
                    level = PriorityLevel.LOW
                
                # 计算等待时间
                waiting_hours = 0.0
                if task['created_at']:
                    waiting_hours = (datetime.now() - task['created_at']).total_seconds() / 3600
                
                # 获取依赖列表
                deps = self.parse_dependencies(task_id)
                dep_ids = [d.depends_on_task_id for d in deps]
                
                scheduled_task = ScheduledTask(
                    task_id=task_id,
                    title=task['title'],
                    priority_score=priority_score,
                    priority_level=level,
                    dependencies=dep_ids,
                    dependencies_completed=True,
                    waiting_hours=waiting_hours,
                    estimated_execution_time=2.0
                )
                
                queue.append(scheduled_task)
                processed_tasks.add(task_id)
            
            logger.info(f"Built execution queue with {len(queue)} tasks")
            return queue
            
        except Exception as e:
            logger.error(f"Error building execution queue: {e}")
            return []
        finally:
            cursor.close()
    
    def _get_task_info(self, task_id: int) -> Optional[Dict]:
        """获取任务信息"""
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT id, title, status, created_at, priority, priority_score
                FROM tasks
                WHERE id = %s
            """, (task_id,))
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting task info for {task_id}: {e}")
            return None
        finally:
            cursor.close()
    
    def bulk_update_priorities(self) -> int:
        """
        批量更新所有待处理任务的优先级
        
        Returns:
            int: 更新的任务数量
        """
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT id
                FROM tasks
                WHERE status IN ('pending', 'ready', 'queued', 'in_progress')
            """)
            
            task_ids = [row['id'] for row in cursor.fetchall()]
            
            updated_count = 0
            for task_id in task_ids:
                if self.adjust_priority_dynamically(task_id):
                    updated_count += 1
            
            logger.info(f"Bulk updated priorities for {updated_count}/{len(task_ids)} tasks")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error in bulk priority update: {e}")
            return 0
        finally:
            cursor.close()
    
    def get_scheduler_stats(self) -> Dict:
        """
        获取调度器统计信息
        
        Returns:
            Dict: 统计信息
        """
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        stats = {
            'total_pending': 0,
            'total_in_progress': 0,
            'avg_priority_score': 0.0,
            'tasks_with_dependencies': 0,
            'average_waiting_hours': 0.0
        }
        
        try:
            # 统计待处理任务
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM tasks
                WHERE status IN ('pending', 'ready', 'queued')
            """)
            stats['total_pending'] = cursor.fetchone()['count']
            
            # 统计进行中任务
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM tasks
                WHERE status = 'in_progress'
            """)
            stats['total_in_progress'] = cursor.fetchone()['count']
            
            # 平均优先级分数
            cursor.execute("""
                SELECT AVG(priority_score) as avg_score
                FROM tasks
                WHERE status IN ('pending', 'ready', 'queued', 'in_progress')
            """)
            stats['avg_priority_score'] = cursor.fetchone()['avg_score'] or 0.0
            
            # 有依赖的任务数
            cursor.execute("""
                SELECT COUNT(DISTINCT task_id) as count
                FROM task_dependencies
            """)
            stats['tasks_with_dependencies'] = cursor.fetchone()['count']
            
            # 平均等待时间
            cursor.execute("""
                SELECT AVG(TIMESTAMPDIFF(HOUR, created_at, NOW())) as avg_wait
                FROM tasks
                WHERE status IN ('pending', 'ready', 'queued')
            """)
            stats['average_waiting_hours'] = cursor.fetchone()['avg_wait'] or 0.0
            
            logger.info(f"Scheduler stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting scheduler stats: {e}")
            return stats
        finally:
            cursor.close()


if __name__ == "__main__":
    # 测试调度引擎
    scheduler = TaskScheduler()
    
    # 统计信息
    stats = scheduler.get_scheduler_stats()
    print("Scheduler Stats:", stats)
    
    # 批量更新优先级
    updated = scheduler.bulk_update_priorities()
    print(f"Updated {updated} task priorities")
    
    # 获取下一个可执行任务
    next_task = scheduler.get_next_executable_task()
    if next_task:
        print(f"Next task: {next_task.task_id} - {next_task.title}")
        print(f"  Priority score: {next_task.priority_score:.2f}")
        print(f"  Priority level: {next_task.priority_level.name}")
        print(f"  Waiting hours: {next_task.waiting_hours:.2f}")
    else:
        print("No executable tasks")
    
    # 构建执行队列
    queue = scheduler.build_execution_queue(max_tasks=5)
    print(f"\nExecution Queue ({len(queue)} tasks):")
    for i, task in enumerate(queue, 1):
        print(f"  {i}. Task {task.task_id}: {task.title} (score: {task.priority_score:.2f})")

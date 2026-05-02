"""
执行结果自动评估与反馈闭环机制 - SDS System v2.0
子任务完成率≥90%时自动标记完成
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import re
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ExecutionEvaluator')


@dataclass
class SubtaskStatus:
    """子任务状态"""
    task_id: int
    title: str
    status: str
    execution_log_length: int
    result_summary_length: int
    quality_score: float
    is_quality_acceptable: bool


@dataclass
class EvaluationResult:
    """评估结果"""
    parent_task_id: int
    total_subtasks: int
    completed_subtasks: int
    quality_acceptable_subtasks: int
    completion_rate: float
    can_auto_complete: bool
    auto_completed: bool
    feedback: List[str]
    suggestions: List[str]
    evaluated_at: datetime


@dataclass
class FeedbackLoop:
    """反馈闭环"""
    task_id: int
    original_status: str
    evaluation_result: EvaluationResult
    actions_taken: List[str]
    updated_task_fields: Dict
    loop_closed: bool


class ExecutionEvaluator:
    """
    执行结果自动评估器
    
    功能：
    1. 评估子任务完成率
    2. 检查自动完成条件（完成率≥90%）
    3. 自动标记任务完成
    4. 生成反馈闭环
    5. 计算执行质量分数
    """
    
    def __init__(self, db_connection=None):
        """
        初始化评估器
        
        Args:
            db_connection: 数据库连接对象
        """
        self.db = db_connection
        self.completion_threshold = 0.9  # 90%完成率阈值
        self.min_execution_log_length = 500  # 执行日志最小字数
        self.min_result_summary_length = 300  # 结果摘要最小字数
        
        # 质量评分权重
        self.quality_weights = {
            'execution_log_length': 0.3,
            'result_summary_length': 0.3,
            'has_attachments': 0.2,
            'task_duration': 0.2
        }
        
        logger.info("ExecutionEvaluator initialized")
    
    def _get_db_connection(self):
        """获取数据库连接"""
        if self.db is None:
            from lib.db_connector import get_db_connection
            self.db = get_db_connection()
        return self.db
    
    def evaluate_subtask_completion(self, parent_task_id: int) -> EvaluationResult:
        """
        评估子任务完成率
        
        Args:
            parent_task_id: 父任务ID
            
        Returns:
            EvaluationResult: 评估结果
        """
        logger.info(f"Evaluating subtask completion for parent task {parent_task_id}")
        
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # 获取所有子任务（通过parent_task_id关联）
            cursor.execute("""
                SELECT id, title, status, execution_log, result_summary, 
                       created_at, updated_at, priority
                FROM tasks
                WHERE parent_task_id = %s
                ORDER BY created_at ASC
            """, (parent_task_id,))
            
            subtasks = cursor.fetchall()
            
            if not subtasks:
                logger.info(f"No subtasks found for parent task {parent_task_id}")
                return EvaluationResult(
                    parent_task_id=parent_task_id,
                    total_subtasks=0,
                    completed_subtasks=0,
                    quality_acceptable_subtasks=0,
                    completion_rate=0.0,
                    can_auto_complete=False,
                    auto_completed=False,
                    feedback=["No subtasks found for this task"],
                    suggestions=["Consider breaking down the task into smaller subtasks"],
                    evaluated_at=datetime.now()
                )
            
            # 统计各项指标
            total_subtasks = len(subtasks)
            completed_subtasks = 0
            quality_acceptable_subtasks = 0
            subtask_statuses = []
            
            for subtask in subtasks:
                # 计算执行日志长度（中文字符）
                execution_log = subtask.get('execution_log') or ''
                exec_log_length = self._count_chinese_chars(execution_log)
                
                # 计算结果摘要长度
                result_summary = subtask.get('result_summary') or ''
                summary_length = self._count_chinese_chars(result_summary)
                
                # 计算质量分数
                quality_score = self.calculate_quality_score(
                    subtask['id'],
                    execution_log,
                    result_summary,
                    subtask.get('created_at'),
                    subtask.get('updated_at')
                )
                
                # 判断质量是否达标
                is_quality_acceptable = (
                    subtask['status'] in ['completed', 'done'] or
                    (subtask['status'] == 'in_progress' and
                     exec_log_length >= self.min_execution_log_length and
                     summary_length >= self.min_result_summary_length)
                )
                
                # 统计完成的子任务
                if subtask['status'] in ['completed', 'done']:
                    completed_subtasks += 1
                
                # 统计质量达标的子任务
                if is_quality_acceptable:
                    quality_acceptable_subtasks += 1
                
                subtask_status = SubtaskStatus(
                    task_id=subtask['id'],
                    title=subtask['title'],
                    status=subtask['status'],
                    execution_log_length=exec_log_length,
                    result_summary_length=summary_length,
                    quality_score=quality_score,
                    is_quality_acceptable=is_quality_acceptable
                )
                subtask_statuses.append(subtask_status)
            
            # 计算完成率
            completion_rate = quality_acceptable_subtasks / total_subtasks if total_subtasks > 0 else 0.0
            
            # 检查是否可以自动完成
            can_auto_complete = completion_rate >= self.completion_threshold
            
            # 生成反馈
            feedback = self._generate_feedback(
                parent_task_id,
                subtask_statuses,
                completion_rate
            )
            
            # 生成建议
            suggestions = self._generate_suggestions(
                subtask_statuses,
                completion_rate
            )
            
            logger.info(
                f"Evaluation for task {parent_task_id}: "
                f"total={total_subtasks}, completed={completed_subtasks}, "
                f"quality_ok={quality_acceptable_subtasks}, "
                f"rate={completion_rate:.2%}, can_auto_complete={can_auto_complete}"
            )
            
            return EvaluationResult(
                parent_task_id=parent_task_id,
                total_subtasks=total_subtasks,
                completed_subtasks=completed_subtasks,
                quality_acceptable_subtasks=quality_acceptable_subtasks,
                completion_rate=completion_rate,
                can_auto_complete=can_auto_complete,
                auto_completed=False,
                feedback=feedback,
                suggestions=suggestions,
                evaluated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error evaluating subtask completion for task {parent_task_id}: {e}")
            return EvaluationResult(
                parent_task_id=parent_task_id,
                total_subtasks=0,
                completed_subtasks=0,
                quality_acceptable_subtasks=0,
                completion_rate=0.0,
                can_auto_complete=False,
                auto_completed=False,
                feedback=[f"Evaluation error: {str(e)}"],
                suggestions=["Retry evaluation later"],
                evaluated_at=datetime.now()
            )
        finally:
            cursor.close()
    
    def _count_chinese_chars(self, text: str) -> int:
        """计算中文字符数"""
        if not text:
            return 0
        
        # 中文字符范围：\u4e00-\u9fa5
        chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
        
        # 英文字符按1/3计算
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        
        return chinese_chars + (english_chars // 3)
    
    def _generate_feedback(self, parent_task_id: int, subtasks: List[SubtaskStatus], completion_rate: float) -> List[str]:
        """生成评估反馈"""
        feedback = []
        
        # 总体完成情况
        feedback.append(
            f"Overall completion rate: {completion_rate:.2%} "
            f"(threshold: {self.completion_threshold:.0%})"
        )
        
        # 质量达标情况
        quality_ok_count = sum(1 for s in subtasks if s.is_quality_acceptable)
        feedback.append(
            f"Quality acceptable subtasks: {quality_ok_count}/{len(subtasks)}"
        )
        
        # 列出未达标子任务
        not_acceptable = [s for s in subtasks if not s.is_quality_acceptable]
        if not_acceptable:
            feedback.append("\nSubtasks NOT meeting quality standards:")
            for subtask in not_acceptable:
                issues = []
                if subtask.status not in ['completed', 'done']:
                    issues.append(f"status={subtask.status}")
                if subtask.execution_log_length < self.min_execution_log_length:
                    issues.append(
                        f"execution_log too short ({subtask.execution_log_length}/"
                        f"{self.min_execution_log_length} chars)"
                    )
                if subtask.result_summary_length < self.min_result_summary_length:
                    issues.append(
                        f"result_summary too short ({subtask.result_summary_length}/"
                        f"{self.min_result_summary_length} chars)"
                    )
                feedback.append(f"  - Task {subtask.task_id}: {', '.join(issues)}")
        
        return feedback
    
    def _generate_suggestions(self, subtasks: List[SubtaskStatus], completion_rate: float) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        if completion_rate >= self.completion_threshold:
            suggestions.append("Excellent! Task meets auto-completion criteria.")
        elif completion_rate >= 0.7:
            suggestions.append("Close to completion threshold. Focus on remaining subtasks.")
        else:
            suggestions.append("More work needed. Prioritize high-impact subtasks first.")
        
        # 具体改进建议
        low_quality = [s for s in subtasks if not s.is_quality_acceptable]
        if low_quality:
            suggestions.append(
                f"Need to improve documentation for {len(low_quality)} subtask(s): "
                f"ensure execution_log ≥{self.min_execution_log_length} chars "
                f"and result_summary ≥{self.min_result_summary_length} chars."
            )
        
        # 进度较慢的任务建议
        in_progress = [s for s in subtasks if s.status == 'in_progress']
        if len(in_progress) > 3:
            suggestions.append(
                f"Consider focusing on completing the {len(in_progress)} in-progress "
                f"tasks before starting new ones."
            )
        
        return suggestions
    
    def check_auto_complete_condition(self, task_id: int) -> Tuple[bool, EvaluationResult]:
        """
        检查自动完成条件
        
        Args:
            task_id: 任务ID
            
        Returns:
            Tuple[bool, EvaluationResult]: (是否满足条件, 评估结果)
        """
        evaluation = self.evaluate_subtask_completion(task_id)
        return (evaluation.can_auto_complete, evaluation)
    
    def auto_complete_task(self, task_id: int) -> bool:
        """
        自动标记任务完成
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功自动完成
        """
        logger.info(f"Attempting auto-complete for task {task_id}")
        
        # 检查是否满足自动完成条件
        can_complete, evaluation = self.check_auto_complete_condition(task_id)
        
        if not can_complete:
            logger.warning(
                f"Task {task_id} does not meet auto-completion criteria: "
                f"completion_rate={evaluation.completion_rate:.2%}"
            )
            return False
        
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 获取当前任务信息
            cursor.execute("""
                SELECT status, execution_log, result_summary
                FROM tasks
                WHERE id = %s
            """, (task_id,))
            task = cursor.fetchone()
            
            if not task:
                logger.error(f"Task {task_id} not found")
                return False
            
            if task[0] in ['completed', 'done']:
                logger.info(f"Task {task_id} is already completed")
                return True
            
            # 构建自动完成的执行日志
            current_exec_log = task[1] or ''
            auto_completion_note = (
                f"\n\n[AUTO-COMPLETED {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n"
                f"Subtask completion rate: {evaluation.completion_rate:.2%} "
                f"(threshold: {self.completion_threshold:.0%})\n"
                f"Total subtasks: {evaluation.total_subtasks}\n"
                f"Quality-acceptable subtasks: {evaluation.quality_acceptable_subtasks}\n"
                f"Feedback: {'; '.join(evaluation.feedback[:3])}"
            )
            
            # 构建结果摘要
            current_summary = task[2] or ''
            if len(current_summary) < self.min_result_summary_length:
                auto_summary = (
                    f"Task automatically completed with {evaluation.completion_rate:.2%} "
                    f"subtask completion rate. {evaluation.total_subtasks} subtasks, "
                    f"{evaluation.quality_acceptable_subtasks} meeting quality standards."
                )
                new_summary = current_summary + ('\n\n' if current_summary else '') + auto_summary
            else:
                new_summary = current_summary
            
            # 更新任务状态
            cursor.execute("""
                UPDATE tasks
                SET status = 'completed',
                    completion_rate = %s,
                    auto_completed = TRUE,
                    execution_log = CONCAT(COALESCE(execution_log, ''), %s),
                    result_summary = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (
                evaluation.completion_rate,
                auto_completion_note,
                new_summary,
                task_id
            ))
            
            conn.commit()
            
            logger.info(
                f"Task {task_id} auto-completed successfully: "
                f"completion_rate={evaluation.completion_rate:.2%}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error auto-completing task {task_id}: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
    
    def generate_feedback_loop(self, task_id: int, execution_result: Dict = None) -> FeedbackLoop:
        """
        生成反馈闭环
        
        Args:
            task_id: 任务ID
            execution_result: 执行结果（可选）
            
        Returns:
            FeedbackLoop: 反馈闭环
        """
        logger.info(f"Generating feedback loop for task {task_id}")
        
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # 获取任务当前状态
            cursor.execute("""
                SELECT id, title, status, execution_log, result_summary,
                       completion_rate, quality_score
                FROM tasks
                WHERE id = %s
            """, (task_id,))
            task = cursor.fetchone()
            
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            original_status = task['status']
            
            # 评估子任务完成情况
            evaluation = self.evaluate_subtask_completion(task_id)
            
            # 确定应采取的行动
            actions_taken = []
            updated_fields = {}
            
            # 1. 检查是否需要自动完成
            if evaluation.can_auto_complete and original_status not in ['completed', 'done']:
                auto_completed = self.auto_complete_task(task_id)
                if auto_completed:
                    actions_taken.append("Task auto-completed based on subtask quality threshold")
                    updated_fields['status'] = 'completed'
                    updated_fields['auto_completed'] = True
            
            # 2. 更新完成率
            if evaluation.completion_rate != task.get('completion_rate'):
                cursor.execute("""
                    UPDATE tasks
                    SET completion_rate = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (evaluation.completion_rate, task_id))
                conn.commit()
                actions_taken.append(f"Updated completion_rate to {evaluation.completion_rate:.2%}")
                updated_fields['completion_rate'] = evaluation.completion_rate
            
            # 3. 计算并更新质量分数
            quality_score = self.calculate_quality_score(
                task_id,
                task.get('execution_log', ''),
                task.get('result_summary', '')
            )
            if abs(quality_score - (task.get('quality_score') or 0)) > 0.01:
                cursor.execute("""
                    UPDATE tasks
                    SET quality_score = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (quality_score, task_id))
                conn.commit()
                actions_taken.append(f"Updated quality_score to {quality_score:.2f}")
                updated_fields['quality_score'] = quality_score
            
            # 4. 生成反馈建议并更新到任务
            feedback_text = '\n'.join(evaluation.feedback + evaluation.suggestions)
            if feedback_text:
                cursor.execute("""
                    UPDATE tasks
                    SET feedback_notes = COALESCE(feedback_notes, '') + %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (f"\n\n[FEEDBACK {datetime.now().strftime('%Y-%m-%d')}]\n{feedback_text}", task_id))
                conn.commit()
                actions_taken.append("Added feedback notes to task")
                updated_fields['feedback_notes'] = feedback_text
            
            loop_closed = len(actions_taken) > 0
            
            logger.info(
                f"Feedback loop for task {task_id}: "
                f"{len(actions_taken)} actions taken, loop_closed={loop_closed}"
            )
            
            return FeedbackLoop(
                task_id=task_id,
                original_status=original_status,
                evaluation_result=evaluation,
                actions_taken=actions_taken,
                updated_task_fields=updated_fields,
                loop_closed=loop_closed
            )
            
        except Exception as e:
            logger.error(f"Error generating feedback loop for task {task_id}: {e}")
            return FeedbackLoop(
                task_id=task_id,
                original_status='unknown',
                evaluation_result=EvaluationResult(
                    parent_task_id=task_id,
                    total_subtasks=0,
                    completed_subtasks=0,
                    quality_acceptable_subtasks=0,
                    completion_rate=0.0,
                    can_auto_complete=False,
                    auto_completed=False,
                    feedback=[],
                    suggestions=[],
                    evaluated_at=datetime.now()
                ),
                actions_taken=[],
                updated_task_fields={},
                loop_closed=False
            )
        finally:
            cursor.close()
    
    def calculate_quality_score(self, task_id: int, execution_log: str, 
                                 result_summary: str, created_at: datetime = None,
                                 updated_at: datetime = None) -> float:
        """
        计算执行质量分数 (0.0 - 10.0)
        
        Args:
            task_id: 任务ID
            execution_log: 执行日志
            result_summary: 结果摘要
            created_at: 创建时间
            updated_at: 更新时间
            
        Returns:
            float: 质量分数
        """
        scores = {}
        
        # 1. 执行日志长度分数
        exec_log_length = self._count_chinese_chars(execution_log)
        if exec_log_length >= self.min_execution_log_length * 2:
            scores['execution_log_length'] = 10.0
        elif exec_log_length >= self.min_execution_log_length:
            scores['execution_log_length'] = 7.0 + (exec_log_length / (self.min_execution_log_length * 2)) * 3.0
        elif exec_log_length >= self.min_execution_log_length / 2:
            scores['execution_log_length'] = 3.0 + (exec_log_length / self.min_execution_log_length) * 4.0
        else:
            scores['execution_log_length'] = (exec_log_length / (self.min_execution_log_length / 2)) * 3.0
        
        # 2. 结果摘要长度分数
        summary_length = self._count_chinese_chars(result_summary)
        if summary_length >= self.min_result_summary_length * 2:
            scores['result_summary_length'] = 10.0
        elif summary_length >= self.min_result_summary_length:
            scores['result_summary_length'] = 7.0 + (summary_length / (self.min_result_summary_length * 2)) * 3.0
        elif summary_length >= self.min_result_summary_length / 2:
            scores['result_summary_length'] = 3.0 + (summary_length / self.min_result_summary_length) * 4.0
        else:
            scores['result_summary_length'] = (summary_length / (self.min_result_summary_length / 2)) * 3.0
        
        # 3. 附件检查分数
        scores['has_attachments'] = self._check_task_attachments(task_id)
        
        # 4. 任务持续时间分数
        if created_at and updated_at:
            duration_hours = (updated_at - created_at).total_seconds() / 3600
            # 理想完成时间：1-24小时
            if 1 <= duration_hours <= 24:
                scores['task_duration'] = 10.0
            elif duration_hours < 1:
                scores['task_duration'] = duration_hours * 10  # 太快可能质量不足
            else:
                scores['task_duration'] = max(0.0, 10.0 - (duration_hours - 24) * 0.1)  # 超过24小时递减
        else:
            scores['task_duration'] = 5.0  # 默认中等分数
        
        # 加权计算总分
        total_score = sum(
            scores[key] * self.quality_weights[key]
            for key in self.quality_weights
        )
        
        return min(10.0, max(0.0, total_score))
    
    def _check_task_attachments(self, task_id: int) -> float:
        """检查任务是否有附件"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT COUNT(*)
                FROM attachments
                WHERE entity_type = 'task' AND entity_id = %s
            """, (task_id,))
            count = cursor.fetchone()[0]
            
            if count >= 3:
                return 10.0
            elif count >= 1:
                return 7.0
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error checking attachments for task {task_id}: {e}")
            return 0.0
        finally:
            cursor.close()
    
    def bulk_evaluate_tasks(self, status_filter: List[str] = None) -> List[FeedbackLoop]:
        """
        批量评估任务
        
        Args:
            status_filter: 状态过滤列表
            
        Returns:
            List[FeedbackLoop]: 反馈闭环列表
        """
        if status_filter is None:
            status_filter = ['in_progress', 'pending', 'ready']
        
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            placeholders = ', '.join(['%s'] * len(status_filter))
            cursor.execute(f"""
                SELECT id
                FROM tasks
                WHERE status IN ({placeholders})
                ORDER BY priority_score DESC, created_at ASC
            """, status_filter)
            
            task_ids = [row['id'] for row in cursor.fetchall()]
            
            logger.info(f"Bulk evaluating {len(task_ids)} tasks")
            
            feedback_loops = []
            for task_id in task_ids:
                loop = self.generate_feedback_loop(task_id)
                if loop.loop_closed:
                    feedback_loops.append(loop)
            
            logger.info(f"Bulk evaluation completed: {len(feedback_loops)} loops closed")
            return feedback_loops
            
        except Exception as e:
            logger.error(f"Error in bulk evaluation: {e}")
            return []
        finally:
            cursor.close()
    
    def get_evaluator_stats(self) -> Dict:
        """
        获取评估器统计信息
        
        Returns:
            Dict: 统计信息
        """
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        stats = {
            'total_tasks_evaluated': 0,
            'auto_completed_tasks': 0,
            'avg_completion_rate': 0.0,
            'avg_quality_score': 0.0,
            'tasks_meeting_threshold': 0
        }
        
        try:
            # 自动完成的任务数
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM tasks
                WHERE auto_completed = TRUE
            """)
            stats['auto_completed_tasks'] = cursor.fetchone()['count']
            
            # 平均完成率
            cursor.execute("""
                SELECT AVG(completion_rate) as avg_rate
                FROM tasks
                WHERE completion_rate IS NOT NULL
            """)
            stats['avg_completion_rate'] = cursor.fetchone()['avg_rate'] or 0.0
            
            # 平均质量分数
            cursor.execute("""
                SELECT AVG(quality_score) as avg_score
                FROM tasks
                WHERE quality_score IS NOT NULL
            """)
            stats['avg_quality_score'] = cursor.fetchone()['avg_score'] or 0.0
            
            # 达到完成阈值的任务数
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM tasks
                WHERE completion_rate >= %s
            """, (self.completion_threshold,))
            stats['tasks_meeting_threshold'] = cursor.fetchone()['count']
            
            logger.info(f"Evaluator stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting evaluator stats: {e}")
            return stats
        finally:
            cursor.close()


if __name__ == "__main__":
    # 测试评估器
    evaluator = ExecutionEvaluator()
    
    # 统计信息
    stats = evaluator.get_evaluator_stats()
    print("Evaluator Stats:", stats)
    
    # 测试单个任务评估（使用一个存在的任务ID）
    test_task_id = 100  # 示例任务ID
    
    print(f"\nEvaluating task {test_task_id}...")
    evaluation = evaluator.evaluate_subtask_completion(test_task_id)
    
    print(f"\nEvaluation Result for Task {test_task_id}:")
    print(f"  Total subtasks: {evaluation.total_subtasks}")
    print(f"  Completed: {evaluation.completed_subtasks}")
    print(f"  Quality acceptable: {evaluation.quality_acceptable_subtasks}")
    print(f"  Completion rate: {evaluation.completion_rate:.2%}")
    print(f"  Can auto-complete: {evaluation.can_auto_complete}")
    
    print("\nFeedback:")
    for item in evaluation.feedback:
        print(f"  - {item}")
    
    print("\nSuggestions:")
    for suggestion in evaluation.suggestions:
        print(f"  - {suggestion}")
    
    # 批量评估
    print("\nRunning bulk evaluation...")
    loops = evaluator.bulk_evaluate_tasks()
    print(f"Closed {len(loops)} feedback loops")
    
    for loop in loops[:3]:
        print(f"  Task {loop.task_id}: {len(loop.actions_taken)} actions")

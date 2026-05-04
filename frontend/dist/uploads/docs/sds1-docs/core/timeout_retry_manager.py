"""
超时检测与自动重试机制 - SDS System v2.0
失败任务自动生成诊断报告
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import IntEnum
import logging
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TimeoutRetryManager')


class RetryStrategy(IntEnum):
    """重试策略"""
    EXPONENTIAL = 1  # 指数退避
    LINEAR = 2       # 线性退避
    FIXED = 3        # 固定间隔


@dataclass
class TimeoutTask:
    """超时任务"""
    task_id: int
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    timeout_hours: float
    retry_count: int
    last_retry_at: Optional[datetime]
    failure_reason: str


@dataclass
class DiagnosticReport:
    """诊断报告"""
    task_id: int
    title: str
    detected_at: datetime
    timeout_hours: float
    retry_count: int
    failure_patterns: List[str]
    root_cause_analysis: str
    suggested_actions: List[str]
    estimated_fix_time: str
    priority_recommendation: str


@dataclass
class RetryResult:
    """重试结果"""
    task_id: int
    success: bool
    retry_count: int
    next_retry_time: Optional[datetime]
    diagnostic_report: Optional[DiagnosticReport]
    message: str


class TimeoutRetryManager:
    """
    超时检测与自动重试管理器
    
    功能：
    1. 检测超时任务
    2. 计算下一次重试时间（支持多种退避策略）
    3. 生成诊断报告
    4. 自动重试任务
    5. 分析失败模式
    6. 建议优化动作
    """
    
    def __init__(self, db_connection=None):
        """
        初始化超时重试管理器
        
        Args:
            db_connection: 数据库连接对象
        """
        self.db = db_connection
        self.default_timeout_hours = 24  # 默认24小时超时
        self.max_retries = 5  # 最大重试次数
        self.retry_strategy = RetryStrategy.EXPONENTIAL  # 默认指数退避
        
        # 重试间隔配置（小时）
        self.retry_intervals = {
            RetryStrategy.EXPONENTIAL: [1, 2, 4, 8, 16],  # 指数增长
            RetryStrategy.LINEAR: [1, 2, 3, 4, 5],         # 线性增长
            RetryStrategy.FIXED: [2, 2, 2, 2, 2]           # 固定间隔
        }
        
        logger.info("TimeoutRetryManager initialized")
    
    def _get_db_connection(self):
        """获取数据库连接"""
        if self.db is None:
            from lib.db_connector import get_db_connection
            self.db = get_db_connection()
        return self.db
    
    def detect_timeout_tasks(self, timeout_hours: float = None) -> List[TimeoutTask]:
        """
        检测超时任务
        
        Args:
            timeout_hours: 超时时间（小时），None则使用默认值
            
        Returns:
            List[TimeoutTask]: 超时任务列表
        """
        if timeout_hours is None:
            timeout_hours = self.default_timeout_hours
        
        logger.info(f"Detecting timeout tasks (timeout={timeout_hours}h)")
        
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        timeout_tasks = []
        
        try:
            # 查找超时的进行中任务
            cursor.execute("""
                SELECT 
                    t.id,
                    t.title,
                    t.status,
                    t.created_at,
                    t.updated_at,
                    t.retry_count,
                    t.last_retry_at,
                    t.failure_reason
                FROM tasks t
                WHERE 
                    t.status IN ('in_progress', 'pending')
                    AND t.updated_at < NOW() - INTERVAL %s HOUR
                    AND (t.retry_count IS NULL OR t.retry_count < %s)
                ORDER BY t.updated_at ASC
            """, (timeout_hours, self.max_retries))
            
            tasks = cursor.fetchall()
            
            for task in tasks:
                # 计算超时时间
                updated_at = task['updated_at'] or task['created_at']
                if updated_at:
                    actual_timeout_hours = (datetime.now() - updated_at).total_seconds() / 3600
                else:
                    actual_timeout_hours = timeout_hours
                
                timeout_task = TimeoutTask(
                    task_id=task['id'],
                    title=task['title'],
                    status=task['status'],
                    created_at=task['created_at'],
                    updated_at=task['updated_at'],
                    timeout_hours=actual_timeout_hours,
                    retry_count=task['retry_count'] or 0,
                    last_retry_at=task['last_retry_at'],
                    failure_reason=task['failure_reason'] or ''
                )
                timeout_tasks.append(timeout_task)
            
            logger.info(f"Detected {len(timeout_tasks)} timeout tasks")
            return timeout_tasks
            
        except Exception as e:
            logger.error(f"Error detecting timeout tasks: {e}")
            return []
        finally:
            cursor.close()
    
    def calculate_next_retry_time(self, retry_count: int) -> datetime:
        """
        计算下一次重试时间
        
        Args:
            retry_count: 当前重试次数
            
        Returns:
            datetime: 下一次重试时间
        """
        intervals = self.retry_intervals[self.retry_strategy]
        
        # 获取对应重试次数的间隔
        if retry_count < len(intervals):
            interval_hours = intervals[retry_count]
        else:
            interval_hours = intervals[-1]  # 使用最后一个间隔
        
        next_retry_time = datetime.now() + timedelta(hours=interval_hours)
        
        logger.debug(
            f"Next retry time for retry_count={retry_count}: "
            f"{next_retry_time} (interval={interval_hours}h)"
        )
        
        return next_retry_time
    
    def generate_diagnostic_report(self, task_id: int, failure_reason: str = '') -> DiagnosticReport:
        """
        生成诊断报告
        
        Args:
            task_id: 任务ID
            failure_reason: 失败原因
            
        Returns:
            DiagnosticReport: 诊断报告
        """
        logger.info(f"Generating diagnostic report for task {task_id}")
        
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # 获取任务信息
            cursor.execute("""
                SELECT id, title, status, created_at, updated_at, 
                       retry_count, execution_log, failure_reason
                FROM tasks
                WHERE id = %s
            """, (task_id,))
            task = cursor.fetchone()
            
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            # 计算超时时间
            updated_at = task['updated_at'] or task['created_at']
            if updated_at:
                timeout_hours = (datetime.now() - updated_at).total_seconds() / 3600
            else:
                timeout_hours = self.default_timeout_hours
            
            retry_count = task.get('retry_count') or 0
            
            # 分析失败模式
            failure_patterns = self.analyze_failure_patterns(task_id, task)
            
            # 根因分析
            root_cause = self._generate_root_cause_analysis(
                task, failure_patterns, timeout_hours
            )
            
            # 建议优化动作
            suggested_actions = self.suggest_optimization_actions(
                failure_patterns, retry_count
            )
            
            # 估计修复时间
            estimated_fix_time = self._estimate_fix_time(failure_patterns)
            
            # 优先级建议
            priority_recommendation = self._get_priority_recommendation(
                retry_count, timeout_hours, failure_patterns
            )
            
            report = DiagnosticReport(
                task_id=task_id,
                title=task['title'],
                detected_at=datetime.now(),
                timeout_hours=timeout_hours,
                retry_count=retry_count,
                failure_patterns=failure_patterns,
                root_cause_analysis=root_cause,
                suggested_actions=suggested_actions,
                estimated_fix_time=estimated_fix_time,
                priority_recommendation=priority_recommendation
            )
            
            # 保存诊断报告到数据库
            self._save_diagnostic_report(task_id, report)
            
            logger.info(f"Diagnostic report generated for task {task_id}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating diagnostic report for task {task_id}: {e}")
            return DiagnosticReport(
                task_id=task_id,
                title=f"Task {task_id}",
                detected_at=datetime.now(),
                timeout_hours=0,
                retry_count=0,
                failure_patterns=[],
                root_cause_analysis=f"Failed to generate diagnostic report: {str(e)}",
                suggested_actions=["Retry diagnostic report generation"],
                estimated_fix_time="Unknown",
                priority_recommendation="Normal"
            )
        finally:
            cursor.close()
    
    def analyze_failure_patterns(self, task_id: int, task: Dict = None) -> List[str]:
        """
        分析失败模式
        
        Args:
            task_id: 任务ID
            task: 任务信息（可选）
            
        Returns:
            List[str]: 失败模式列表
        """
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        patterns = []
        
        try:
            if task is None:
                cursor.execute("""
                    SELECT id, title, status, execution_log, failure_reason, retry_count
                    FROM tasks
                    WHERE id = %s
                """, (task_id,))
                task = cursor.fetchone()
            
            if not task:
                return patterns
            
            execution_log = task.get('execution_log') or ''
            failure_reason = task.get('failure_reason') or ''
            retry_count = task.get('retry_count') or 0
            
            # 分析执行日志中的错误模式
            error_patterns = {
                'connection_error': ['连接失败', 'connection failed', 'timeout', '超时', '网络错误'],
                'authentication_error': ['认证失败', '权限不足', 'authentication', '权限', 'unauthorized'],
                'resource_not_found': ['不存在', 'not found', '404', '找不到'],
                'validation_error': ['验证失败', 'validation', '参数错误', 'invalid'],
                'database_error': ['数据库错误', 'database', 'sql error', 'duplicate'],
                'api_error': ['API错误', 'api limit', 'rate limit', '配额'],
                'insufficient_documentation': ['execution_log', '日志太短', '摘要太短'],
                'dependency_issue': ['依赖', 'dependency', 'prerequisite']
            }
            
            combined_text = (execution_log + ' ' + failure_reason).lower()
            
            for pattern_name, keywords in error_patterns.items():
                for keyword in keywords:
                    if keyword.lower() in combined_text:
                        patterns.append(pattern_name)
                        break
            
            # 基于重试次数的模式
            if retry_count >= 3:
                patterns.append('persistent_failure')
            elif retry_count >= 1:
                patterns.append('recurring_issue')
            
            # 去重
            patterns = list(dict.fromkeys(patterns))
            
            logger.info(f"Task {task_id} failure patterns: {patterns}")
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing failure patterns for task {task_id}: {e}")
            return ['analysis_failed']
        finally:
            cursor.close()
    
    def _generate_root_cause_analysis(self, task: Dict, patterns: List[str], 
                                        timeout_hours: float) -> str:
        """生成根因分析"""
        analysis_parts = []
        
        # 超时分析
        if timeout_hours >= 72:
            analysis_parts.append(
                f"Severe timeout detected: {timeout_hours:.1f}h. Task may be stuck "
                "or blocked by external dependencies."
            )
        elif timeout_hours >= 24:
            analysis_parts.append(
                f"Moderate timeout detected: {timeout_hours:.1f}h. Progress may be "
                "slower than expected."
            )
        
        # 失败模式分析
        pattern_descriptions = {
            'connection_error': 'Network connectivity issues detected. This may be '
                                'due to firewall rules, VPN requirements, or service '
                                'outages.',
            'authentication_error': 'Authentication or permission issues detected. '
                                    'Check API keys, credentials, and access permissions.',
            'resource_not_found': 'Resource not found errors. Verify URLs, file paths, '
                                  'and database references.',
            'validation_error': 'Input validation issues. Check data formats, required '
                                'fields, and parameter constraints.',
            'database_error': 'Database-related errors. Check connections, query '
                              'performance, and data integrity.',
            'api_error': 'API usage issues. May need rate limit adjustments or '
                         'alternative API endpoints.',
            'insufficient_documentation': 'Task documentation is insufficient. Need '
                                          'more detailed execution logs and summaries.',
            'dependency_issue': 'Dependency resolution problems. Verify prerequisite '
                                'tasks and resource availability.',
            'persistent_failure': 'Multiple retry attempts failed. This indicates a '
                                  'systemic issue requiring human intervention.',
            'recurring_issue': 'Task experienced repeated failures. Pattern suggests '
                               'need for process improvement.'
        }
        
        for pattern in patterns:
            if pattern in pattern_descriptions:
                analysis_parts.append(pattern_descriptions[pattern])
        
        # 如果没有特定模式，提供通用分析
        if not analysis_parts:
            analysis_parts.append(
                "No specific failure patterns detected. The task may be blocked by "
                "unforeseen circumstances, require human decision-making, or simply "
                "need more time to complete."
            )
        
        return '\n\n'.join(analysis_parts)
    
    def suggest_optimization_actions(self, patterns: List[str], retry_count: int) -> List[str]:
        """
        建议优化动作
        
        Args:
            patterns: 失败模式列表
            retry_count: 重试次数
            
        Returns:
            List[str]: 建议动作列表
        """
        suggestions = []
        
        # 基于失败模式的建议
        pattern_suggestions = {
            'connection_error': [
                "Verify network connectivity and firewall settings",
                "Check if VPN connection is required",
                "Test endpoint availability manually",
                "Consider adding retry with exponential backoff"
            ],
            'authentication_error': [
                "Validate API keys and credentials",
                "Check permission levels for the task",
                "Verify token expiration dates",
                "Consider rotating security credentials"
            ],
            'resource_not_found': [
                "Verify URLs and file paths",
                "Check if required databases are accessible",
                "Validate external service endpoints",
                "Confirm resource hasn't been deleted/moved"
            ],
            'validation_error': [
                "Review input data formats",
                "Check for missing required fields",
                "Validate parameter constraints",
                "Add input validation before execution"
            ],
            'database_error': [
                "Check database connection pool settings",
                "Optimize slow queries",
                "Verify transaction isolation levels",
                "Check for deadlock conditions"
            ],
            'api_error': [
                "Review API rate limits and quotas",
                "Implement request throttling",
                "Consider alternative API endpoints",
                "Cache frequent API responses"
            ],
            'insufficient_documentation': [
                "Add more detailed execution logging",
                "Expand result summary content",
                "Include attachment references",
                "Document decision points and reasoning"
            ],
            'dependency_issue': [
                "Map and document all task dependencies",
                "Verify dependency task completion",
                "Consider parallel execution where possible",
                "Add dependency health checks"
            ],
            'persistent_failure': [
                "Escalate to human intervention",
                "Review task scope and objectives",
                "Consider alternative approaches",
                "Schedule task review meeting"
            ],
            'recurring_issue': [
                "Document the recurring problem",
                "Implement preventive measures",
                "Add monitoring alerts for this pattern",
                "Consider process redesign"
            ]
        }
        
        for pattern in patterns:
            if pattern in pattern_suggestions:
                suggestions.extend(pattern_suggestions[pattern])
        
        # 基于重试次数的建议
        if retry_count >= self.max_retries:
            suggestions.append(
                "MAX RETRIES REACHED: Task requires immediate human review. "
                "No further automatic retries will be scheduled."
            )
        elif retry_count >= 3:
            suggestions.append(
                "High retry count detected. Consider task reassignment or "
                "methodology change before next retry."
            )
        
        # 去重并限制数量
        unique_suggestions = list(dict.fromkeys(suggestions))
        return unique_suggestions[:10]
    
    def _estimate_fix_time(self, patterns: List[str]) -> str:
        """估计修复时间"""
        if not patterns:
            return "1-2 hours (simple investigation)"
        
        # 基于模式估计时间
        complexity_scores = {
            'connection_error': 2,
            'authentication_error': 3,
            'resource_not_found': 1,
            'validation_error': 2,
            'database_error': 4,
            'api_error': 3,
            'insufficient_documentation': 1,
            'dependency_issue': 2,
            'persistent_failure': 8,
            'recurring_issue': 4
        }
        
        total_score = sum(complexity_scores.get(p, 2) for p in patterns)
        
        if total_score <= 2:
            return "30 minutes - 1 hour"
        elif total_score <= 5:
            return "1-3 hours"
        elif total_score <= 10:
            return "3-8 hours"
        else:
            return "1-2 business days (complex issue)"
    
    def _get_priority_recommendation(self, retry_count: int, timeout_hours: float,
                                       patterns: List[str]) -> str:
        """获取优先级建议"""
        if retry_count >= self.max_retries:
            return "CRITICAL - Immediate human intervention required"
        elif timeout_hours >= 72 or 'persistent_failure' in patterns:
            return "HIGH - Urgent review recommended"
        elif timeout_hours >= 24 or 'recurring_issue' in patterns:
            return "MEDIUM - Should be reviewed today"
        else:
            return "NORMAL - Can be handled in next batch"
    
    def _save_diagnostic_report(self, task_id: int, report: DiagnosticReport) -> bool:
        """保存诊断报告到数据库"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 构建报告内容
            report_content = (
                f"=== DIAGNOSTIC REPORT - Task {task_id} ===\n"
                f"Generated: {report.detected_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Timeout: {report.timeout_hours:.1f} hours\n"
                f"Retry Count: {report.retry_count}\n\n"
                f"--- Failure Patterns ---\n"
                f"{', '.join(report.failure_patterns) if report.failure_patterns else 'None detected'}\n\n"
                f"--- Root Cause Analysis ---\n"
                f"{report.root_cause_analysis}\n\n"
                f"--- Suggested Actions ---\n"
            )
            
            for i, action in enumerate(report.suggested_actions, 1):
                report_content += f"{i}. {action}\n"
            
            report_content += (
                f"\n--- Estimation ---\n"
                f"Estimated Fix Time: {report.estimated_fix_time}\n"
                f"Priority Recommendation: {report.priority_recommendation}\n"
            )
            
            # 更新任务表
            cursor.execute("""
                UPDATE tasks
                SET diagnostic_report = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (report_content, task_id))
            
            conn.commit()
            logger.info(f"Diagnostic report saved for task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving diagnostic report for task {task_id}: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
    
    def retry_task(self, task_id: int) -> RetryResult:
        """
        重试任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            RetryResult: 重试结果
        """
        logger.info(f"Attempting to retry task {task_id}")
        
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # 获取当前任务信息
            cursor.execute("""
                SELECT id, title, status, retry_count, last_retry_at, failure_reason
                FROM tasks
                WHERE id = %s
            """, (task_id,))
            task = cursor.fetchone()
            
            if not task:
                return RetryResult(
                    task_id=task_id,
                    success=False,
                    retry_count=0,
                    next_retry_time=None,
                    diagnostic_report=None,
                    message="Task not found"
                )
            
            retry_count = task.get('retry_count') or 0
            
            # 检查是否达到最大重试次数
            if retry_count >= self.max_retries:
                logger.warning(f"Task {task_id} reached max retries ({self.max_retries})")
                
                # 生成诊断报告
                report = self.generate_diagnostic_report(task_id)
                
                return RetryResult(
                    task_id=task_id,
                    success=False,
                    retry_count=retry_count,
                    next_retry_time=None,
                    diagnostic_report=report,
                    message=f"Max retries ({self.max_retries}) reached. Manual intervention required."
                )
            
            # 计算下一次重试时间
            next_retry_time = self.calculate_next_retry_time(retry_count)
            
            # 生成诊断报告
            report = self.generate_diagnostic_report(task_id)
            
            # 更新任务状态
            new_retry_count = retry_count + 1
            
            retry_note = (
                f"\n\n[RETRY #{new_retry_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n"
                f"Previous status: {task['status']}\n"
                f"Next retry scheduled: {next_retry_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            
            cursor.execute("""
                UPDATE tasks
                SET retry_count = %s,
                    last_retry_at = NOW(),
                    execution_log = CONCAT(COALESCE(execution_log, ''), %s),
                    status = 'pending',
                    updated_at = NOW()
                WHERE id = %s
            """, (new_retry_count, retry_note, task_id))
            
            conn.commit()
            
            logger.info(
                f"Task {task_id} retry #{new_retry_count} scheduled: "
                f"next retry at {next_retry_time}"
            )
            
            return RetryResult(
                task_id=task_id,
                success=True,
                retry_count=new_retry_count,
                next_retry_time=next_retry_time,
                diagnostic_report=report,
                message=f"Task retry #{new_retry_count} scheduled successfully"
            )
            
        except Exception as e:
            logger.error(f"Error retrying task {task_id}: {e}")
            conn.rollback()
            
            return RetryResult(
                task_id=task_id,
                success=False,
                retry_count=0,
                next_retry_time=None,
                diagnostic_report=None,
                message=f"Retry failed: {str(e)}"
            )
        finally:
            cursor.close()
    
    def process_timeout_tasks(self) -> List[RetryResult]:
        """
        处理所有超时任务
        
        Returns:
            List[RetryResult]: 重试结果列表
        """
        logger.info("Starting timeout task processing")
        
        # 检测超时任务
        timeout_tasks = self.detect_timeout_tasks()
        
        if not timeout_tasks:
            logger.info("No timeout tasks detected")
            return []
        
        logger.info(f"Processing {len(timeout_tasks)} timeout tasks")
        
        results = []
        for timeout_task in timeout_tasks:
            result = self.retry_task(timeout_task.task_id)
            results.append(result)
        
        # 统计
        success_count = sum(1 for r in results if r.success)
        logger.info(
            f"Timeout processing complete: {success_count}/{len(results)} "
            f"tasks retried successfully"
        )
        
        return results
    
    def get_manager_stats(self) -> Dict:
        """
        获取管理器统计信息
        
        Returns:
            Dict: 统计信息
        """
        conn = self._get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        stats = {
            'total_timeout_detected': 0,
            'total_retries': 0,
            'max_retry_reached': 0,
            'avg_retry_count': 0.0,
            'tasks_with_diagnostic': 0
        }
        
        try:
            # 总重试次数
            cursor.execute("""
                SELECT COUNT(*) as count, SUM(retry_count) as total
                FROM tasks
                WHERE retry_count > 0
            """)
            result = cursor.fetchone()
            stats['total_retries'] = result['total'] or 0
            stats['total_timeout_detected'] = result['count'] or 0
            
            # 达到最大重试次数的任务数
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM tasks
                WHERE retry_count >= %s
            """, (self.max_retries,))
            stats['max_retry_reached'] = cursor.fetchone()['count']
            
            # 平均重试次数
            if stats['total_timeout_detected'] > 0:
                stats['avg_retry_count'] = stats['total_retries'] / stats['total_timeout_detected']
            
            # 有诊断报告的任务数
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM tasks
                WHERE diagnostic_report IS NOT NULL AND diagnostic_report != ''
            """)
            stats['tasks_with_diagnostic'] = cursor.fetchone()['count']
            
            logger.info(f"Timeout manager stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting manager stats: {e}")
            return stats
        finally:
            cursor.close()


if __name__ == "__main__":
    # 测试超时重试管理器
    manager = TimeoutRetryManager()
    
    # 统计信息
    stats = manager.get_manager_stats()
    print("Timeout Manager Stats:", stats)
    
    # 检测超时任务
    print("\nDetecting timeout tasks...")
    timeout_tasks = manager.detect_timeout_tasks()
    
    print(f"Found {len(timeout_tasks)} timeout tasks:")
    for task in timeout_tasks[:5]:
        print(
            f"  - Task {task.task_id}: {task.title[:40]}... "
            f"(timeout={task.timeout_hours:.1f}h, retries={task.retry_count})"
        )
    
    # 处理超时任务（测试，不实际执行）
    print("\nProcessing timeout tasks (simulation mode)...")
    print("In production, this would retry eligible tasks automatically")
    
    # 生成诊断报告示例（使用一个任务ID）
    if timeout_tasks:
        test_task_id = timeout_tasks[0].task_id
        print(f"\nGenerating diagnostic report for task {test_task_id}...")
        report = manager.generate_diagnostic_report(test_task_id)
        
        print(f"\nDiagnostic Report for Task {report.task_id}:")
        print(f"  Title: {report.title}")
        print(f"  Timeout: {report.timeout_hours:.1f}h")
        print(f"  Retry Count: {report.retry_count}")
        print(f"  Failure Patterns: {report.failure_patterns}")
        print(f"\n  Root Cause Analysis:\n{report.root_cause_analysis[:200]}...")
        print(f"\n  Suggested Actions:")
        for i, action in enumerate(report.suggested_actions[:5], 1):
            print(f"    {i}. {action}")
        print(f"\n  Priority: {report.priority_recommendation}")

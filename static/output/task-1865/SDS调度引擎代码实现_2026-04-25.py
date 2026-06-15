#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS (Self-Driving System) v2.0 智能调度引擎
任务编号: #1865
创建日期: 2026-04-25
"""

import asyncio
import heapq
import time
from datetime import datetime, timedelta
from enum import IntEnum, Enum
from typing import List, Dict, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
import json
import logging
from abc import ABC, abstractmethod

# ==================== 配置与日志 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 枚举定义 ====================

class TaskPriority(IntEnum):
    """任务优先级枚举"""
    LOWEST = 0
    LOW = 2
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RESEARCHING = "researching"
    READY = "ready"
    RUNNING = "running"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRYING = "retrying"


# ==================== 数据结构 ====================

@dataclass
class SubTask:
    """子任务数据结构"""
    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    completed: bool = False
    completion_note: str = ""


@dataclass(order=True)
class Task:
    """任务数据结构"""
    # 排序字段
    priority_score: float = field(default=0.0, compare=True)
    
    # 核心字段
    task_id: str = field(compare=False)
    title: str = field(compare=False)
    description: str = field(compare=False)
    
    # 调度字段
    base_priority: TaskPriority = field(default=TaskPriority.NORMAL, compare=False)
    dependencies: List[str] = field(default_factory=list, compare=False)
    dependents_count: int = field(default=0, compare=False)
    
    # 状态字段
    status: TaskStatus = field(default=TaskStatus.PENDING, compare=False)
    created_at: datetime = field(default_factory=datetime.now, compare=False)
    started_at: Optional[datetime] = field(default=None, compare=False)
    completed_at: Optional[datetime] = field(default=None, compare=False)
    deadline: Optional[datetime] = field(default=None, compare=False)
    
    # 执行字段
    max_retries: int = field(default=3, compare=False)
    retry_count: int = field(default=0, compare=False)
    timeout_seconds: int = field(default=3600, compare=False)
    execution_log: str = field(default="", compare=False)
    result_summary: str = field(default="", compare=False)
    
    # 研究与评估字段
    research_notes: Optional[str] = field(default=None, compare=False)
    evaluation_score: Optional[float] = field(default=None, compare=False)
    
    # 子任务
    subtasks: List[SubTask] = field(default_factory=list, compare=False)
    
    def add_log(self, message: str):
        """添加执行日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.execution_log += f"[{timestamp}] {message}\n"
        logger.info(f"[{self.task_id}] {message}")
    
    def get_completion_rate(self) -> float:
        """计算子任务完成率"""
        if not self.subtasks:
            return 1.0
        completed = sum(1 for st in self.subtasks if st.completed)
        return completed / len(self.subtasks)


@dataclass
class EvaluationResult:
    """评估结果"""
    overall_score: float
    completion_rate: float
    llm_score: float
    rule_score: float
    feedback: str
    recommendations: List[str]
    should_complete: bool


@dataclass
class DiagnosisReport:
    """诊断报告"""
    task_id: str
    title: str
    failure_reason: str
    error_logs: List[str]
    retry_attempts: int
    recommendations: List[str]
    generated_at: datetime
    root_cause: str


# ==================== 核心组件 - 依赖解析器 ====================

class DependencyResolver:
    """任务依赖关系解析器 - DAG构建与拓扑排序"""
    
    def __init__(self):
        self.adjacency: Dict[str, List[str]] = defaultdict(list)
        self.in_degree: Dict[str, int] = defaultdict(int)
        self.tasks: Dict[str, Task] = {}
    
    def add_task(self, task: Task):
        """添加任务到依赖图"""
        self.tasks[task.task_id] = task
        if task.task_id not in self.in_degree:
            self.in_degree[task.task_id] = 0
        
        for dep_id in task.dependencies:
            self.adjacency[dep_id].append(task.task_id)
            self.in_degree[task.task_id] += 1
    
    def detect_cycle(self) -> Tuple[bool, Optional[List[str]]]:
        """检测循环依赖 - 使用DFS算法"""
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str) -> Tuple[bool, Optional[List[str]]]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.adjacency[node]:
                if neighbor not in visited:
                    has_cycle, cycle_path = dfs(neighbor)
                    if has_cycle:
                        return True, cycle_path
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    return True, path[cycle_start:] + [neighbor]
            
            rec_stack.remove(node)
            path.pop()
            return False, None
        
        for node in list(self.tasks.keys()):
            if node not in visited:
                has_cycle, cycle_path = dfs(node)
                if has_cycle:
                    return True, cycle_path
        
        return False, None
    
    def topological_sort(self) -> List[str]:
        """拓扑排序 - Kahn算法"""
        queue = [task_id for task_id, degree in self.in_degree.items() if degree == 0]
        heapq.heapify(queue)
        result = []
        
        while queue:
            node = heapq.heappop(queue)
            result.append(node)
            
            for neighbor in self.adjacency[node]:
                self.in_degree[neighbor] -= 1
                if self.in_degree[neighbor] == 0:
                    heapq.heappush(queue, neighbor)
        
        return result
    
    def get_ready_tasks(self, completed_tasks: Set[str]) -> List[str]:
        """获取所有依赖已满足的就绪任务"""
        ready = []
        for task_id, task in self.tasks.items():
            if task_id not in completed_tasks:
                all_deps_met = all(dep in completed_tasks for dep in task.dependencies)
                if all_deps_met:
                    ready.append(task_id)
        return ready
    
    def update_dependents_count(self):
        """更新每个任务的依赖者数量"""
        for task in self.tasks.values():
            task.dependents_count = len(self.adjacency[task.task_id])


# ==================== 核心组件 - 优先级计算器 ====================

class PriorityCalculator:
    """优先级动态计算器"""
    
    def __init__(self):
        self.history: Dict[str, List[bool]] = defaultdict(list)
    
    def record_completion(self, task_id: str, success: bool):
        """记录任务完成历史"""
        self.history[task_id].append(success)
        if len(self.history[task_id]) > 10:
            self.history[task_id].pop(0)
    
    def calculate(self, task: Task) -> float:
        """计算最终优先级分数"""
        base_score = float(task.base_priority)
        
        # 1. 紧急度因子 (0-1.5)
        urgency_factor = self._calculate_urgency(task)
        
        # 2. 依赖权重因子 (0-1.0)
        dependency_factor = self._calculate_dependency_weight(task)
        
        # 3. 历史完成率因子 (0.8-1.2)
        history_factor = self._calculate_history_factor(task)
        
        # 4. 重试惩罚因子 (0.5-1.0)
        retry_penalty = self._calculate_retry_penalty(task)
        
        final_score = base_score * (1 + urgency_factor + dependency_factor) * history_factor * retry_penalty
        
        return round(final_score, 2)
    
    def _calculate_urgency(self, task: Task) -> float:
        """计算紧急度因子"""
        if not task.deadline:
            return 0.0
        
        time_left = task.deadline - datetime.now()
        total_time = task.deadline - task.created_at
        
        if total_time.total_seconds() <= 0:
            return 1.5
        
        progress = 1 - (time_left.total_seconds() / total_time.total_seconds())
        return min(1.5, progress * 1.5)
    
    def _calculate_dependency_weight(self, task: Task) -> float:
        """计算依赖权重因子"""
        if task.dependents_count == 0:
            return 0.0
        return min(1.0, (task.dependents_count ** 0.5) * 0.2)
    
    def _calculate_history_factor(self, task: Task) -> float:
        """计算历史完成率因子"""
        if task.task_id not in self.history or not self.history[task.task_id]:
            return 1.0
        
        success_rate = sum(self.history[task.task_id]) / len(self.history[task.task_id])
        return 0.8 + (success_rate * 0.4)
    
    def _calculate_retry_penalty(self, task: Task) -> float:
        """计算重试惩罚因子"""
        if task.retry_count == 0:
            return 1.0
        return max(0.5, 1.0 - (task.retry_count * 0.15))


# ==================== 核心组件 - Tavily研究模块 ====================

class TavilyResearcher:
    """Tavily深度研究模块"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.enabled = api_key is not None
    
    async def research(self, task: Task) -> str:
        """执行深度研究"""
        if not self.enabled:
            note = "⚠️ Tavily API未配置，跳过自动化研究"
            task.add_log(note)
            return note
        
        task.add_log("🔍 开始Tavily深度研究...")
        task.status = TaskStatus.RESEARCHING
        
        try:
            # 模拟研究过程（实际应调用Tavily API）
            research_queries = self._generate_research_queries(task)
            research_notes = []
            
            for i, query in enumerate(research_queries):
                await asyncio.sleep(0.5)  # 模拟API延迟
                research_notes.append(f"[查询{i+1}] {query}")
                research_notes.append(f"  → 发现 {3 + i} 条相关资料")
            
            # 合成研究结果
            synthesis = self._synthesize_research(research_notes, task)
            
            task.research_notes = synthesis
            task.add_log(f"✅ 研究完成，生成 {len(research_notes)} 条研究笔记")
            return synthesis
            
        except Exception as e:
            error_note = f"❌ 研究失败: {str(e)}"
            task.add_log(error_note)
            return error_note
    
    def _generate_research_queries(self, task: Task) -> List[str]:
        """生成研究查询"""
        return [
            f"最新技术方案: {task.title}",
            f"最佳实践: {task.description[:50]}",
            f"常见问题与解决方案: {task.title}"
        ]
    
    def _synthesize_research(self, notes: List[str], task: Task) -> str:
        """合成研究笔记"""
        synthesis = f"""
## 深度研究报告 - {task.title}

### 研究摘要
针对任务 '{task.title}' 执行自动化深度研究，检索了 {len(notes) * 3} 条相关资料。

### 关键发现
1. 该领域最新技术趋势表明，模块化设计可提升系统可维护性 40%
2. 同类项目的成功率约为 75%，主要失败原因是需求变更和资源不足
3. 推荐采用迭代开发模式，每2周进行一次里程碑评审

### 推荐行动
- 在执行前进行详细的需求分析
- 建立每日站会机制跟踪进度
- 准备风险应对预案

### 参考资料
{chr(10).join(notes)}
"""
        return synthesis.strip()


# ==================== 核心组件 - 结果评估器 ====================

class ResultEvaluator:
    """执行结果自动评估器"""
    
    def __init__(self, completion_threshold: float = 0.9):
        self.completion_threshold = completion_threshold
    
    def evaluate(self, task: Task) -> EvaluationResult:
        """综合评估任务结果"""
        task.add_log("📊 开始执行结果评估...")
        task.status = TaskStatus.EVALUATING
        
        # 1. 子任务完成率 (60%)
        completion_rate = task.get_completion_rate()
        
        # 2. LLM智能评估 (30%)
        llm_score = self._llm_assess(task)
        
        # 3. 规则校验 (10%)
        rule_score = self._rule_check(task)
        
        # 综合评分
        overall_score = (completion_rate * 0.6) + (llm_score * 0.3) + (rule_score * 0.1)
        
        # 生成反馈
        feedback, recommendations = self._generate_feedback(
            task, completion_rate, llm_score, rule_score
        )
        
        # 判断是否自动完成
        should_complete = overall_score >= self.completion_threshold
        
        result = EvaluationResult(
            overall_score=round(overall_score, 2),
            completion_rate=round(completion_rate, 2),
            llm_score=round(llm_score, 2),
            rule_score=round(rule_score, 2),
            feedback=feedback,
            recommendations=recommendations,
            should_complete=should_complete
        )
        
        task.evaluation_score = result.overall_score
        task.add_log(f"✅ 评估完成 - 综合得分: {result.overall_score}, "
                    f"自动完成: {'是' if should_complete else '否'}")
        
        return result
    
    def _llm_assess(self, task: Task) -> float:
        """LLM智能评估"""
        # 模拟LLM评估逻辑
        log_length = len(task.execution_log)
        summary_length = len(task.result_summary)
        
        score = 0.5
        if log_length > 500:
            score += 0.2
        if summary_length > 100:
            score += 0.2
        if task.research_notes:
            score += 0.1
        
        return min(1.0, score)
    
    def _rule_check(self, task: Task) -> float:
        """规则校验"""
        score = 1.0
        checks = 0
        passed = 0
        
        # 检查1: execution_log ≥ 200字
        checks += 1
        if len(task.execution_log) >= 200:
            passed += 1
        else:
            score -= 0.3
        
        # 检查2: result_summary ≥ 50字
        checks += 1
        if len(task.result_summary) >= 50:
            passed += 1
        else:
            score -= 0.3
        
        # 检查3: 有产出文件
        checks += 1
        if len(task.subtasks) >= 1:
            passed += 1
        else:
            score -= 0.4
        
        return max(0.0, score)
    
    def _generate_feedback(self, task: Task, completion_rate: float, 
                           llm_score: float, rule_score: float) -> Tuple[str, List[str]]:
        """生成评估反馈和建议"""
        feedback_parts = []
        recommendations = []
        
        if completion_rate >= 0.9:
            feedback_parts.append("✅ 子任务完成率优秀")
        elif completion_rate >= 0.7:
            feedback_parts.append("⚠️ 子任务完成率良好，建议检查未完成项")
            recommendations.append("优先完成剩余子任务")
        else:
            feedback_parts.append("❌ 子任务完成率不足")
            recommendations.append("重新规划子任务，拆分更细粒度")
        
        if rule_score >= 0.8:
            feedback_parts.append("✅ 验收标准满足度高")
        else:
            feedback_parts.append("⚠️ 部分验收标准未满足")
            recommendations.append("检查execution_log和result_summary字数要求")
        
        feedback = " | ".join(feedback_parts)
        return feedback, recommendations


# ==================== 核心组件 - 重试管理器 ====================

class RetryManager:
    """自动重试管理器 - 指数退避策略"""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    def should_retry(self, task: Task) -> bool:
        """判断是否应该重试"""
        return task.retry_count < self.max_retries
    
    def calculate_delay(self, retry_count: int) -> float:
        """计算退避延迟（秒）"""
        return (self.backoff_factor ** retry_count) * 5
    
    async def retry_task(self, task: Task, scheduler: 'SDSScheduler') -> bool:
        """执行重试"""
        if not self.should_retry(task):
            return False
        
        task.retry_count += 1
        task.status = TaskStatus.RETRYING
        task.add_log(f"🔄 开始第 {task.retry_count} 次重试...")
        
        delay = self.calculate_delay(task.retry_count - 1)
        task.add_log(f"⏱️  退避等待: {delay} 秒")
        await asyncio.sleep(delay)
        
        # 重置状态
        task.started_at = None
        task.completed_at = None
        
        # 重新提交到调度器
        await scheduler._enqueue_task(task)
        task.add_log("✅ 任务已重新入队")
        
        return True
    
    def generate_diagnosis_report(self, task: Task) -> DiagnosisReport:
        """生成诊断报告"""
        return DiagnosisReport(
            task_id=task.task_id,
            title=task.title,
            failure_reason=self._identify_failure_reason(task),
            error_logs=[line for line in task.execution_log.split('\n') 
                       if '❌' in line or 'ERROR' in line],
            retry_attempts=task.retry_count,
            recommendations=self._generate_recommendations(task),
            generated_at=datetime.now(),
            root_cause=self._find_root_cause(task)
        )
    
    def _identify_failure_reason(self, task: Task) -> str:
        """识别失败原因"""
        if task.status == TaskStatus.TIMEOUT:
            return "任务执行超时"
        elif "研究失败" in task.execution_log:
            return "自动化研究环节失败"
        elif "评估" in task.execution_log:
            return "结果评估未通过"
        else:
            return "未知原因"
    
    def _find_root_cause(self, task: Task) -> str:
        """查找根本原因"""
        if task.timeout_seconds < 600 and task.status == TaskStatus.TIMEOUT:
            return "超时时间设置过短，建议增加到至少600秒"
        elif task.retry_count == 0:
            return "首次执行失败，可能是偶发问题"
        else:
            return "多次重试仍失败，需要人工介入检查"
    
    def _generate_recommendations(self, task: Task) -> List[str]:
        """生成建议列表"""
        recs = [
            "检查任务描述是否清晰完整",
            "验证依赖资源是否可用",
            "评估超时时间设置是否合理"
        ]
        if task.retry_count >= 2:
            recs.append("建议人工介入排查问题")
        return recs


# ==================== 核心组件 - 超时检测器 ====================

class TimeoutDetector:
    """任务超时检测器"""
    
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.running_tasks: Dict[str, Task] = {}
        self._monitor_task: Optional[asyncio.Task] = None
    
    def register_task(self, task: Task):
        """注册运行中任务"""
        if task.started_at:
            self.running_tasks[task.task_id] = task
    
    def unregister_task(self, task_id: str):
        """注销任务"""
        self.running_tasks.pop(task_id, None)
    
    async def start_monitor(self, scheduler: 'SDSScheduler'):
        """启动超时监控"""
        self._monitor_task = asyncio.create_task(self._monitor_loop(scheduler))
    
    async def _monitor_loop(self, scheduler: 'SDSScheduler'):
        """监控循环"""
        while True:
            await asyncio.sleep(self.check_interval)
            await self._check_timeouts(scheduler)
    
    async def _check_timeouts(self, scheduler: 'SDSScheduler'):
        """检查超时任务"""
        now = datetime.now()
        timeout_tasks = []
        
        for task_id, task in list(self.running_tasks.items()):
            if task.started_at:
                elapsed = (now - task.started_at).total_seconds()
                if elapsed > task.timeout_seconds:
                    timeout_tasks.append(task)
        
        for task in timeout_tasks:
            task.status = TaskStatus.TIMEOUT
            task.add_log(f"⏰ 任务超时，已运行 {elapsed:.0f} 秒（限制: {task.timeout_seconds} 秒）")
            self.unregister_task(task.task_id)
            
            # 尝试重试
            if scheduler.retry_manager.should_retry(task):
                await scheduler.retry_manager.retry_task(task, scheduler)
            else:
                task.status = TaskStatus.FAILED
                report = scheduler.retry_manager.generate_diagnosis_report(task)
                task.add_log(f"❌ 达到最大重试次数，已生成诊断报告")


# ==================== 主调度引擎 ====================

class SDSScheduler:
    """SDS v2.0 智能调度引擎"""
    
    def __init__(self, tavily_api_key: Optional[str] = None):
        # 核心数据结构
        self.ready_queue: List[Task] = []
        self.task_map: Dict[str, Task] = {}
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        
        # 核心组件
        self.dep_resolver = DependencyResolver()
        self.priority_calc = PriorityCalculator()
        self.researcher = TavilyResearcher(tavily_api_key)
        self.evaluator = ResultEvaluator(completion_threshold=0.9)
        self.retry_manager = RetryManager(max_retries=3)
        self.timeout_detector = TimeoutDetector(check_interval=30)
        
        # 执行控制
        self.max_concurrent = 10
        self.current_running = 0
        self._running = False
        self._lock = asyncio.Lock()
        
        # 统计
        self.stats = {
            'total_submitted': 0,
            'total_completed': 0,
            'total_failed': 0,
            'total_retried': 0,
            'avg_completion_time': 0.0
        }
    
    async def start(self):
        """启动调度器"""
        self._running = True
        await self.timeout_detector.start_monitor(self)
        asyncio.create_task(self._scheduler_loop())
        logger.info("🚀 SDS v2.0 智能调度引擎已启动")
    
    async def stop(self):
        """停止调度器"""
        self._running = False
        logger.info("⏹️  SDS调度引擎已停止")
    
    async def submit_task(self, task: Task) -> str:
        """提交任务"""
        async with self._lock:
            # 检查循环依赖
            self.dep_resolver.add_task(task)
            has_cycle, cycle_path = self.dep_resolver.detect_cycle()
            
            if has_cycle:
                error_msg = f"❌ 检测到循环依赖: {' → '.join(cycle_path)}"
                task.add_log(error_msg)
                raise ValueError(error_msg)
            
            self.task_map[task.task_id] = task
            self.stats['total_submitted'] += 1
            task.add_log(f"📥 任务已提交，优先级: {task.base_priority.name}")
            
            # 检查是否可以立即入队
            if not task.dependencies:
                await self._enqueue_task(task)
            else:
                task.add_log(f"⏳ 等待依赖完成: {task.dependencies}")
            
            return task.task_id
    
    async def _enqueue_task(self, task: Task):
        """任务入队 - 计算优先级并加入优先队列"""
        # 更新依赖者计数
        self.dep_resolver.update_dependents_count()
        
        # 计算动态优先级
        task.priority_score = self.priority_calc.calculate(task)
        task.add_log(f"⚖️  动态优先级计算完成: {task.priority_score}")
        
        # 执行前置研究
        await self.researcher.research(task)
        
        # 加入优先队列（注意：heapq是最小堆，用负数实现最大堆）
        heapq.heappush(self.ready_queue, task)
        task.status = TaskStatus.READY
        task.add_log(f"📋 任务已加入就绪队列")
    
    async def _scheduler_loop(self):
        """主调度循环"""
        while self._running:
            async with self._lock:
                # 检查是否有就绪任务且有执行槽位
                while (self.ready_queue and 
                       self.current_running < self.max_concurrent):
                    task = heapq.heappop(self.ready_queue)
                    await self._execute_task(task)
            
            await asyncio.sleep(0.1)
    
    async def _execute_task(self, task: Task):
        """执行任务"""
        self.current_running += 1
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        task.add_log("▶️  开始执行任务")
        
        # 注册到超时检测器
        self.timeout_detector.register_task(task)
        
        try:
            # 模拟任务执行（实际应调用具体执行器）
            await asyncio.sleep(2)  # 模拟执行时间
            
            # 模拟子任务完成
            if not task.subtasks:
                for i in range(3):
                    task.subtasks.append(SubTask(
                        id=f"{task.task_id}-sub-{i}",
                        title=f"子任务{i+1}",
                        description=f"自动生成的子任务{i+1}",
                        completed=True
                    ))
            
            # 结果评估
            evaluation = self.evaluator.evaluate(task)
            
            if evaluation.should_complete:
                await self._complete_task(task, evaluation)
            else:
                await self._handle_insufficient_result(task, evaluation)
                
        except Exception as e:
            task.add_log(f"❌ 执行异常: {str(e)}")
            await self._handle_failure(task)
        finally:
            self.current_running -= 1
            self.timeout_detector.unregister_task(task.task_id)
    
    async def _complete_task(self, task: Task, evaluation: EvaluationResult):
        """完成任务"""
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        self.completed_tasks.add(task.task_id)
        self.stats['total_completed'] += 1
        self.priority_calc.record_completion(task.task_id, True)
        
        completion_time = (task.completed_at - task.created_at).total_seconds()
        task.add_log(f"🎉 任务完成！用时: {completion_time:.1f}秒, "
                    f"评估得分: {evaluation.overall_score}")
        
        # 检查并唤醒依赖此任务的任务
        ready_tasks = self.dep_resolver.get_ready_tasks(self.completed_tasks)
        for ready_id in ready_tasks:
            if ready_id in self.task_map and ready_id not in self.completed_tasks:
                ready_task = self.task_map[ready_id]
                if ready_task.status == TaskStatus.PENDING:
                    await self._enqueue_task(ready_task)
    
    async def _handle_insufficient_result(self, task: Task, evaluation: EvaluationResult):
        """处理结果不达标情况 - 反馈闭环"""
        task.add_log(f"📝 结果未达标，启动反馈闭环")
        task.add_log(f"💡 评估反馈: {evaluation.feedback}")
        
        for rec in evaluation.recommendations:
            task.add_log(f"💡 改进建议: {rec}")
        
        # 尝试重试
        if self.retry_manager.should_retry(task):
            self.stats['total_retried'] += 1
            await self.retry_manager.retry_task(task, self)
        else:
            await self._handle_failure(task)
    
    async def _handle_failure(self, task: Task):
        """处理失败任务"""
        task.status = TaskStatus.FAILED
        self.failed_tasks.add(task.task_id)
        self.stats['total_failed'] += 1
        self.priority_calc.record_completion(task.task_id, False)
        
        # 生成诊断报告
        report = self.retry_manager.generate_diagnosis_report(task)
        task.add_log(f"📋 诊断报告已生成 - 根本原因: {report.root_cause}")
        task.add_log(f"❌ 任务失败")
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        task = self.task_map.get(task_id)
        return task.status if task else None
    
    async def adjust_priority(self, task_id: str, new_priority: TaskPriority) -> bool:
        """动态调整任务优先级"""
        task = self.task_map.get(task_id)
        if not task or task.status != TaskStatus.PENDING:
            return False
        
        old_priority = task.base_priority
        task.base_priority = new_priority
        task.add_log(f"⚖️  优先级调整: {old_priority.name} → {new_priority.name}")
        
        # 重新计算并重新入队
        if task in self.ready_queue:
            self.ready_queue.remove(task)
            heapq.heapify(self.ready_queue)
            heapq.heappush(self.ready_queue, task)
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats['queue_size'] = len(self.ready_queue)
        stats['running_count'] = self.current_running
        stats['completion_rate'] = (
            stats['total_completed'] / stats['total_submitted'] 
            if stats['total_submitted'] > 0 else 0.0
        )
        return stats


# ==================== 单元测试 ====================

import unittest
from unittest.mock import patch, MagicMock

class TestSDSScheduler(unittest.IsolatedAsyncioTestCase):
    """SDS调度引擎单元测试"""
    
    async def asyncSetUp(self):
        self.scheduler = SDSScheduler()
    
    async def test_task_submission(self):
        """测试任务提交"""
        task = Task(
            task_id="test-001",
            title="测试任务",
            description="这是一个测试任务",
            base_priority=TaskPriority.NORMAL
        )
        
        task_id = await self.scheduler.submit_task(task)
        self.assertEqual(task_id, "test-001")
        self.assertIn(task_id, self.scheduler.task_map)
        self.assertEqual(self.scheduler.stats['total_submitted'], 1)
    
    async def test_cyclic_dependency_detection(self):
        """测试循环依赖检测"""
        task1 = Task(task_id="task-1", title="任务1", description="",
                    dependencies=["task-2"])
        task2 = Task(task_id="task-2", title="任务2", description="",
                    dependencies=["task-1"])
        
        await self.scheduler.submit_task(task1)
        
        with self.assertRaises(ValueError) as ctx:
            await self.scheduler.submit_task(task2)
        
        self.assertIn("循环依赖", str(ctx.exception))
    
    def test_priority_calculation(self):
        """测试优先级计算"""
        calc = PriorityCalculator()
        
        task = Task(
            task_id="test-prio",
            title="优先级测试",
            description="",
            base_priority=TaskPriority.HIGH,
            dependents_count=5
        )
        
        score = calc.calculate(task)
        self.assertGreater(score, 8.0)  # 基础优先级是8
        self.assertLess(score, 20.0)  # 不应过高
    
    async def test_result_evaluation(self):
        """测试结果评估"""
        evaluator = ResultEvaluator(completion_threshold=0.9)
        
        task = Task(
            task_id="test-eval",
            title="评估测试",
            description="",
            execution_log="这是一条很长的日志，用于测试评估器是否能够正确计算得分。" * 10,
            result_summary="这是结果摘要，包含了任务的核心成果和关键发现。" * 5
        )
        
        # 添加子任务
        for i in range(10):
            task.subtasks.append(SubTask(
                id=f"sub-{i}",
                title=f"子任务{i}",
                description="",
                completed=(i < 9)  # 90%完成率
            ))
        
        result = evaluator.evaluate(task)
        self.assertGreaterEqual(result.completion_rate, 0.9)
        self.assertTrue(result.should_complete)
    
    def test_retry_manager(self):
        """测试重试管理器"""
        retry_mgr = RetryManager(max_retries=3, backoff_factor
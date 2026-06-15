#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw 多智能体协作工作流框架原型
Version: 0.1.0
Author: 刘宇宙团队
Date: 2026-04-24
"""

import asyncio
import json
import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Callable
from abc import ABC, abstractmethod

# ==================== 基础定义 ====================

class MessageType(Enum):
    TASK_ASSIGN = "task_assign"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    STATE_UPDATE = "state_update"
    RESULT_SUBMIT = "result_submit"
    ARBITER_DECISION = "arbiter_decision"
    ERROR = "error"

class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REWORK = "rework"

class AgentStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"

@dataclass
class Message:
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.TASK_ASSIGN
    timestamp: float = field(default_factory=time.time)
    sender: str = "system"
    receiver: str = "all"
    payload: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Task:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    required_skills: List[str] = field(default_factory=list)
    priority: int = 1
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    assignee: Optional[str] = None
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

@dataclass
class Agent(ABC):
    agent_id: str
    name: str
    role: str
    skills: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[Task] = None
    success_count: int = 0
    total_count: int = 0

    @abstractmethod
    async def execute(self, task: Task) -> Any:
        """执行任务的抽象方法，由具体Agent实现"""
        pass

    async def run(self, task: Task) -> Task:
        """运行任务的包装方法"""
        self.status = AgentStatus.BUSY
        self.current_task = task
        task.status = TaskStatus.RUNNING
        task.updated_at = time.time()
        
        try:
            result = await self.execute(task)
            task.result = result
            task.status = TaskStatus.COMPLETED
            self.success_count += 1
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
        finally:
            self.total_count += 1
            self.status = AgentStatus.IDLE
            self.current_task = None
            task.updated_at = time.time()
        
        return task

# ==================== 核心组件 ====================

class MessageBus:
    """消息总线：实现组件间的异步通信"""
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.queue = asyncio.Queue()

    def subscribe(self, message_type: MessageType, callback: Callable):
        """订阅消息类型"""
        if message_type.value not in self.subscribers:
            self.subscribers[message_type.value] = []
        self.subscribers[message_type.value].append(callback)

    async def publish(self, message: Message):
        """发布消息"""
        await self.queue.put(message)

    async def run(self):
        """运行消息分发循环"""
        while True:
            message = await self.queue.get()
            callbacks = self.subscribers.get(message.message_type.value, [])
            for callback in callbacks:
                asyncio.create_task(callback(message))
            self.queue.task_done()

class GlobalState:
    """全局状态管理器"""
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.agents: Dict[str, Agent] = {}
        self.version: int = 0
        self._lock = asyncio.Lock()

    async def add_task(self, task: Task):
        async with self._lock:
            self.tasks[task.task_id] = task
            self.version += 1

    async def update_task(self, task_id: str, **kwargs):
        async with self._lock:
            if task_id in self.tasks:
                for k, v in kwargs.items():
                    setattr(self.tasks[task_id], k, v)
                self.tasks[task_id].updated_at = time.time()
                self.version += 1

    async def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    async def add_agent(self, agent: Agent):
        async with self._lock:
            self.agents[agent.agent_id] = agent
            self.version += 1

    async def get_idle_agents(self, skill: str) -> List[Agent]:
        return [
            a for a in self.agents.values()
            if a.status == AgentStatus.IDLE and skill in a.skills
        ]

    async def get_all_tasks(self) -> List[Task]:
        return list(self.tasks.values())

class TaskAllocator:
    """任务分配器"""
    def __init__(self, state: GlobalState, bus: MessageBus):
        self.state = state
        self.bus = bus
        self.bus.subscribe(MessageType.STATE_UPDATE, self._on_state_update)

    async def _on_state_update(self, message: Message):
        """状态更新时触发任务分配"""
        await self.allocate_pending_tasks()

    async def allocate_pending_tasks(self):
        """分配所有待处理的任务"""
        tasks = await self.state.get_all_tasks()
        pending_tasks = [t for t in tasks if t.status == TaskStatus.PENDING]
        
        for task in pending_tasks:
            # 检查依赖是否完成
            deps_completed = all(
                (await self.state.get_task(dep_id)).status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )
            if not deps_completed:
                continue

            # 寻找匹配的空闲Agent
            for skill in task.required_skills:
                idle_agents = await self.state.get_idle_agents(skill)
                if idle_agents:
                    # 选择成功率最高的Agent
                    best_agent = max(idle_agents, key=lambda a: a.success_count / max(a.total_count, 1))
                    await self._assign_task(task, best_agent)
                    break

    async def _assign_task(self, task: Task, agent: Agent):
        """分配任务给指定Agent"""
        await self.state.update_task(
            task.task_id,
            status=TaskStatus.ASSIGNED,
            assignee=agent.agent_id
        )
        
        message = Message(
            message_type=MessageType.TASK_ASSIGN,
            sender="task-allocator",
            receiver=agent.agent_id,
            payload={"task_id": task.task_id, "task": task.__dict__}
        )
        await self.bus.publish(message)
        # print(f"✅ 任务 [{task.name}] 已分配给 Agent [{agent.name}]")

class ResultArbiter:
    """结果仲裁器"""
    def __init__(self, state: GlobalState, bus: MessageBus, accept_threshold: float = 0.8):
        self.state = state
        self.bus = bus
        self.accept_threshold = accept_threshold
        self.bus.subscribe(MessageType.TASK_COMPLETE, self._on_task_complete)

    async def _on_task_complete(self, message: Message):
        task_id = message.payload["task_id"]
        task = await self.state.get_task(task_id)
        if not task:
            return

        # 模拟LLM评估质量，实际实现调用LLM
        quality_score = await self._evaluate_quality(task)
        # print(f"⚖️  任务 [{task.name}] 质量评分: {quality_score:.2f}")

        if quality_score >= self.accept_threshold:
            # 验收通过
            await self.state.update_task(task_id, status=TaskStatus.COMPLETED)
            decision_msg = Message(
                message_type=MessageType.ARBITER_DECISION,
                sender="result-arbiter",
                receiver=task.assignee,
                payload={"task_id": task_id, "decision": "accepted", "score": quality_score}
            )
            await self.bus.publish(decision_msg)
            # print(f"✅ 任务 [{task.name}] 验收通过")
        else:
            # 验收不通过，返工
            await self.state.update_task(task_id, status=TaskStatus.REWORK)
            decision_msg = Message(
                message_type=MessageType.ARBITER_DECISION,
                sender="result-arbiter",
                receiver=task.assignee,
                payload={"task_id": task_id, "decision": "rework", "score": quality_score, "feedback": "质量不足，请优化后重新提交"}
            )
            await self.bus.publish(decision_msg)
            # print(f"🔄 任务 [{task.name}] 验收不通过，要求返工")

    async def _evaluate_quality(self, task: Task) -> float:
        """评估任务结果质量，模拟返回0.7-1.0的随机分数"""
        import random
        # 实际场景中这里调用LLM基于验收标准评估
        return 0.7 + random.random() * 0.3

class ResultAggregator:
    """结果聚合器"""
    def __init__(self, state: GlobalState, bus: MessageBus):
        self.state = state
        self.bus = bus
        self.bus.subscribe(MessageType.ARBITER_DECISION, self._on_arbiter_decision)

    async def _on_arbiter_decision(self, message: Message):
        if message.payload["decision"] != "accepted":
            return

        # 检查所有任务是否都完成
        all_tasks = await self.state.get_all_tasks()
        all_completed = all(t.status == TaskStatus.COMPLETED for t in all_tasks)
        
        if all_completed:
            results = {t.name: t.result for t in all_tasks}
            final_result = await self._aggregate(results)
            # print("\n🎉 所有任务完成，最终结果聚合成功!")
            # print(json.dumps(final_result, ensure_ascii=False, indent=2))

    async def _aggregate(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """聚合多个任务的结果"""
        return {
            "status": "success",
            "total_tasks": len(results),
            "results": results,
            "summary": "多Agent协作任务已全部完成"
        }

# ==================== 场景验证：代码审查自动化 ====================

class StaticAnalysisAgent(Agent):
    """静态分析Agent"""
    async def execute(self, task: Task) -> Dict:
        # print(f"🔍 {self.name} 正在执行静态代码分析...")
        await asyncio.sleep(2)  # 模拟执行时间
        return {
            "lint_errors": 3,
            "security_issues": 1,
            "complexity_score": 7.2,
            "files_analyzed": 12
        }

class TestCoverageAgent(Agent):
    """测试覆盖Agent"""
    async def execute(self, task: Task) -> Dict:
        # print(f"🧪 {self.name} 正在检查测试覆盖率...")
        await asyncio.sleep(1.5)  # 模拟执行时间
        return {
            "overall_coverage": "87.3%",
            "uncovered_files": 2,
            "test_cases": 156,
            "failed_tests": 3
        }

class ArchitectureComplianceAgent(Agent):
    """架构合规Agent"""
    async def execute(self, task: Task) -> Dict:
        # print(f"🏗️  {self.name} 正在检查架构合规性...")
        await asyncio.sleep(1)  # 模拟执行时间
        return {
            "dependency_violations": 0,
            "architecture_score": 9.1,
            "circular_imports": 0,
            "compliant": True
        }

class CodeStyleAgent(Agent):
    """代码风格Agent"""
    async def execute(self, task: Task) -> Dict:
        # print(f"📝 {self.name} 正在检查代码风格...")
        await asyncio.sleep(0.8)  # 模拟执行时间
        return {
            "style_issues": 15,
            "naming_violations": 2,
            "missing_comments": 5,
            "formatting_score": 8.5
        }

class ReportGenerationAgent(Agent):
    """报告生成Agent"""
    async def execute(self, task: Task) -> Dict:
        # print(f"✅ {self.name} 正在生成审查报告...")
        await asyncio.sleep(1.2)  # 模拟执行时间
        return {
            "report_url": "https://github.com/example/pr/123/review",
            "overall_score": 8.3,
            "recommendations": [
                "修复3个lint错误",
                "补充2个未覆盖文件的测试",
                "完善5处缺失的注释"
            ],
            "approval_status": "approved_with_comments"
        }

# ==================== 框架运行示例 ====================

async def main():
    # print("🚀 OpenClaw 多智能体协作工作流框架启动")
    # print("=" * 60)

    # 初始化核心组件
    bus = MessageBus()
    state = GlobalState()
    allocator = TaskAllocator(state, bus)
    arbiter = ResultArbiter(state, bus, accept_threshold=0.75)
    aggregator = ResultAggregator(state, bus)

    # 启动消息总线
    asyncio.create_task(bus.run())

    # 注册Agent (5个)
    agents = [
        StaticAnalysisAgent(agent_id="static-001", name="静态分析专家", role="代码审查", skills=["static_analysis"]),
        TestCoverageAgent(agent_id="test-001", name="测试覆盖专家", role="代码审查", skills=["test_coverage"]),
        ArchitectureComplianceAgent(agent_id="arch-001", name="架构合规专家", role="代码审查", skills=["architecture"]),
        CodeStyleAgent(agent_id="style-001", name="代码风格专家", role="代码审查", skills=["code_style"]),
        ReportGenerationAgent(agent_id="report-001", name="报告生成专家", role="代码审查", skills=["report_generation"]),
    ]
    for agent in agents:
        await state.add_agent(agent)
    # print(f"✅ 已注册 {len(agents)} 个智能体")

    # 创建代码审查任务 (并行执行前4个，最后一个依赖前4个)
    tasks = [
        Task(name="静态代码分析", description="运行lint和安全扫描", required_skills=["static_analysis"], priority=1),
        Task(name="测试覆盖检查", description="检查单元测试覆盖率", required_skills=["test_coverage"], priority=1),
        Task(name="架构合规检查", description="检查架构规范和依赖", required_skills=["architecture"], priority=1),
        Task(name="代码风格检查", description="检查编码规范和注释", required_skills=["code_style"], priority=1),
        Task(name="审查报告生成", description="整合所有结果生成报告", required_skills=["report_generation"], 
             dependencies=["静态代码分析", "测试覆盖检查", "架构合规检查", "代码风格检查"], priority=2),
    ]
    # 处理依赖，转换为task_id
    task_name_to_id = {t.name: t.task_id for t in tasks}
    for task in tasks:
        task.dependencies = [task_name_to_id[name] for name in task.dependencies if name in task_name_to_id]
        await state.add_task(task)
    # print(f"✅ 已创建 {len(tasks)} 个代码审查子任务")

    # 开始任务分配
    await bus.publish(Message(message_type=MessageType.STATE_UPDATE, sender="system"))

    # 运行直到所有任务完成
    while True:
        all_tasks = await state.get_all_tasks()
        if all(t.status == TaskStatus.COMPLETED for t in all_tasks):
            break
        await asyncio.sleep(0.5)

    # print("\n" + "=" * 60)
    # print("🏁 代码审查自动化场景验证完成!")

if __name__ == "__main__":
    asyncio.run(main())

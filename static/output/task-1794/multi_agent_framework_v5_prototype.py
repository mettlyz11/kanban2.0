#!/usr/bin/env python3
"""
Multi-Agent Collaboration Framework v5.0 - Prototype Implementation
====================================================================
基于2026年最佳实践的编排式+分层式混合架构原型

核心特性:
1. Meta-Orchestrator + Domain Orchestrator 分层编排
2. 5种执行模式 (Sequential/Parallel/Pipeline/Swarm/Debate)
3. Agent性能画像与自适应调度
4. 四级记忆架构
5. A2A + MCP 混合通信协议
6. 完整基准测试框架

运行方式: python3 multi_agent_framework_v5_prototype.py
"""

import asyncio
import json
import time
import uuid
import random
import statistics
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import copy

# =============================================================================
# 基础数据模型
# =============================================================================

class ExecutionMode(Enum):
    """执行模式枚举"""
    SEQUENTIAL = "sequential"    # 串行执行 (v4.3默认)
    PARALLEL = "parallel"        # 并行执行
    PIPELINE = "pipeline"        # 流水线
    SWARM = "swarm"              # 群体协作 (多Agent投票)
    DEBATE = "debate"            # 辩论模式


class AgentStatus(Enum):
    """Agent状态"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    DEGRADED = "degraded"
    OFFLINE = "offline"


@dataclass
class Task:
    """任务定义"""
    id: str
    description: str
    task_type: str
    priority: str = "medium"  # critical/high/medium/low
    required_capabilities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    timeout_seconds: int = 300
    expected_output: str = ""
    metadata: Dict = field(default_factory=dict)


@dataclass
class SubTask:
    """子任务"""
    id: str
    parent_id: str
    description: str
    required_capabilities: List[str]
    dependencies: List[str] = field(default_factory=list)
    assigned_agent: Optional[str] = None
    status: str = "pending"  # pending/running/completed/failed
    result: Any = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class AgentProfile:
    """Agent性能画像"""
    agent_id: str
    name: str
    capabilities: List[str]
    max_concurrent: int = 1
    success_rate: float = 0.9
    avg_latency_ms: float = 2000.0
    cost_per_task: float = 0.05
    current_load: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    health_status: AgentStatus = AgentStatus.IDLE
    context_cache: Dict = field(default_factory=dict)
    specialization: str = "general"

    @property
    def capability_score(self) -> float:
        """综合能力评分 (0-1)"""
        return (
            self.success_rate * 0.35 +
            (1.0 - min(self.current_load, 1.0)) * 0.25 +
            (1.0 / (1.0 + self.avg_latency_ms / 3000)) * 0.20 +
            (1.0 / (1.0 + self.cost_per_task * 10)) * 0.20
        )

    def update_performance(self, success: bool, latency_ms: float):
        """更新性能指标"""
        self.tasks_completed += 1
        if not success:
            self.tasks_failed += 1
        # 指数移动平均
        self.success_rate = 0.9 * self.success_rate + 0.1 * (1.0 if success else 0.0)
        self.avg_latency_ms = 0.9 * self.avg_latency_ms + 0.1 * latency_ms


@dataclass
class ExecutionResult:
    """执行结果"""
    task_id: str
    status: str  # success/partial/failed
    output: Any
    agent_id: str
    duration_ms: float
    tokens_used: int = 0
    confidence: float = 0.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    test_name: str
    mode: ExecutionMode
    total_duration_ms: float
    agent_count: int
    success_count: int
    failure_count: int
    avg_task_duration_ms: float
    throughput: float  # tasks/minute
    token_efficiency: float
    results: List[ExecutionResult] = field(default_factory=list)


# =============================================================================
# A2A 通信协议
# =============================================================================

class A2AMessage:
    """Agent-to-Agent 消息"""
    
    def __init__(self, from_agent: str, to_agent: str, msg_type: str, payload: Dict):
        self.message_id = f"msg-{uuid.uuid4().hex[:8]}"
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.type = msg_type  # request/response/delegate/notify/consensus
        self.timestamp = datetime.now().isoformat()
        self.payload = payload

    def to_dict(self) -> Dict:
        return {
            "message_id": self.message_id,
            "from": self.from_agent,
            "to": self.to_agent,
            "type": self.type,
            "timestamp": self.timestamp,
            "payload": self.payload
        }


class MessageBus:
    """A2A消息总线"""
    
    def __init__(self):
        self.channels: Dict[str, List[A2AMessage]] = {}
        self.message_count = 0
    
    def send(self, msg: A2AMessage):
        """发送消息"""
        if msg.to_agent not in self.channels:
            self.channels[msg.to_agent] = []
        self.channels[msg.to_agent].append(msg)
        self.message_count += 1
    
    def receive(self, agent_id: str) -> List[A2AMessage]:
        """接收消息"""
        msgs = self.channels.get(agent_id, [])
        self.channels[agent_id] = []
        return msgs
    
    def broadcast(self, from_agent: str, payload: Dict, exclude: List[str] = None):
        """广播消息"""
        exclude = exclude or []
        for agent_id in self.channels:
            if agent_id not in exclude:
                self.send(A2AMessage(from_agent, agent_id, "notify", payload))


# =============================================================================
# 四级记忆系统
# =============================================================================

class FourTierMemory:
    """四级记忆架构"""
    
    def __init__(self):
        # Layer 1: 感知记忆 (短期缓冲)
        self.sensory_buffer: List[Dict] = []
        
        # Layer 2: 工作记忆 (当前上下文)
        self.working_memory: Dict[str, Any] = {}
        
        # Layer 3: 语义记忆 (知识图谱)
        self.semantic_graph: Dict[str, Dict] = {
            "concepts": {},
            "relations": []
        }
        
        # Layer 4: 情节记忆 (历史记录)
        self.episodic_memory: List[Dict] = []
    
    def store_working(self, key: str, value: Any):
        """存储工作记忆"""
        self.working_memory[key] = {
            "value": value,
            "timestamp": time.time(),
            "access_count": 0
        }
    
    def retrieve_working(self, key: str) -> Optional[Any]:
        """检索工作记忆"""
        if key in self.working_memory:
            self.working_memory[key]["access_count"] += 1
            return self.working_memory[key]["value"]
        return None
    
    def store_episodic(self, event: Dict):
        """存储情节记忆"""
        event["timestamp"] = time.time()
        event["id"] = f"evt-{uuid.uuid4().hex[:8]}"
        self.episodic_memory.append(event)
        # 保留最近1000条
        if len(self.episodic_memory) > 1000:
            self.episodic_memory = self.episodic_memory[-1000:]
    
    def similar_episodes(self, query: str, top_k: int = 5) -> List[Dict]:
        """检索相似历史事件 (简化实现)"""
        # 基于关键词匹配
        scores = []
        query_words = set(query.lower().split())
        for ep in self.episodic_memory:
            ep_text = json.dumps(ep).lower()
            ep_words = set(ep_text.split())
            score = len(query_words & ep_words) / max(len(query_words), 1)
            scores.append((ep, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [ep for ep, _ in scores[:top_k]]


# =============================================================================
# Agent 实现
# =============================================================================

class BaseAgent:
    """Agent基类 v2.0"""
    
    def __init__(self, profile: AgentProfile, memory: FourTierMemory, bus: MessageBus):
        self.profile = profile
        self.memory = memory
        self.bus = bus
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.message_handlers: Dict[str, Callable] = {
            "request": self._handle_request,
            "delegate": self._handle_delegate,
            "consensus": self._handle_consensus,
            "notify": self._handle_notify
        }
    
    async def execute(self, subtask: SubTask) -> ExecutionResult:
        """执行子任务 (由子类实现)"""
        raise NotImplementedError
    
    async def process_messages(self):
        """处理消息队列"""
        msgs = self.bus.receive(self.profile.agent_id)
        for msg in msgs:
            handler = self.message_handlers.get(msg.type)
            if handler:
                await handler(msg)
    
    async def _handle_request(self, msg: A2AMessage):
        """处理请求"""
        pass
    
    async def _handle_delegate(self, msg: A2AMessage):
        """处理委托"""
        pass
    
    async def _handle_consensus(self, msg: A2AMessage):
        """处理共识请求"""
        pass
    
    async def _handle_notify(self, msg: A2AMessage):
        """处理通知"""
        pass
    
    def can_accept_task(self) -> bool:
        """是否可以接受新任务"""
        return (
            self.profile.health_status in [AgentStatus.IDLE, AgentStatus.BUSY]
            and len(self.running_tasks) < self.profile.max_concurrent
        )


class ResearchAgent(BaseAgent):
    """研究Agent v2.0 - 增强版"""
    
    def __init__(self, agent_id: str, memory: FourTierMemory, bus: MessageBus):
        profile = AgentProfile(
            agent_id=agent_id,
            name=f"Research-{agent_id[-4:]}",
            capabilities=["web_search", "data_collection", "literature_review", "trend_analysis"],
            max_concurrent=2,
            specialization="research"
        )
        super().__init__(profile, memory, bus)
        self.mock_knowledge_base = self._init_knowledge()
    
    def _init_knowledge(self) -> Dict:
        return {
            "AI": ["机器学习", "深度学习", "强化学习", "Transformer"],
            "materials": ["催化剂", "电池材料", "纳米材料", "计算化学"],
            "business": ["融资", "市场分析", "竞品调研", "商业模式"]
        }
    
    async def execute(self, subtask: SubTask) -> ExecutionResult:
        start = time.time()
        self.profile.health_status = AgentStatus.BUSY
        
        # 模拟研究执行
        await asyncio.sleep(random.uniform(0.5, 1.5))  # 模拟网络延迟
        
        query = subtask.description
        findings = []
        
        # 基于知识库生成模拟结果
        for domain, items in self.mock_knowledge_base.items():
            if any(kw in query.lower() for kw in domain.split()):
                findings.extend(items)
        
        if not findings:
            findings = [f"关于'{query}'的研究发现", "相关文献综述", "市场趋势数据"]
        
        # 模拟偶尔失败
        success = random.random() > 0.08  # 92%成功率
        duration = (time.time() - start) * 1000
        
        self.profile.update_performance(success, duration)
        self.profile.health_status = AgentStatus.IDLE
        
        return ExecutionResult(
            task_id=subtask.id,
            status="success" if success else "failed",
            output={
                "findings": findings,
                "sources": random.randint(3, 8),
                "confidence": random.uniform(0.82, 0.96)
            },
            agent_id=self.profile.agent_id,
            duration_ms=duration,
            tokens_used=random.randint(800, 2500),
            confidence=random.uniform(0.82, 0.96) if success else 0.0
        )


class AnalysisAgent(BaseAgent):
    """分析Agent v2.0"""
    
    def __init__(self, agent_id: str, memory: FourTierMemory, bus: MessageBus):
        profile = AgentProfile(
            agent_id=agent_id,
            name=f"Analysis-{agent_id[-4:]}",
            capabilities=["data_analysis", "strategy_planning", "report_generation", "risk_assessment"],
            max_concurrent=1,
            specialization="analysis"
        )
        super().__init__(profile, memory, bus)
    
    async def execute(self, subtask: SubTask) -> ExecutionResult:
        start = time.time()
        self.profile.health_status = AgentStatus.BUSY
        
        await asyncio.sleep(random.uniform(0.8, 2.0))
        
        prior_results = subtask.metadata.get("prior_results", {})
        findings = prior_results.get("findings", [])
        
        # 模拟分析过程
        key_points = [
            "核心发现1: 数据趋势分析完成",
            "核心发现2: 风险评估通过",
            "核心发现3: 策略建议已生成"
        ]
        
        success = random.random() > 0.12  # 88%成功率
        duration = (time.time() - start) * 1000
        
        self.profile.update_performance(success, duration)
        self.profile.health_status = AgentStatus.IDLE
        
        return ExecutionResult(
            task_id=subtask.id,
            status="success" if success else "failed",
            output={
                "key_points": key_points,
                "recommendations": ["建议A", "建议B", "建议C"],
                "risk_level": random.choice(["low", "medium", "high"]),
                "analyzed_findings": len(findings)
            },
            agent_id=self.profile.agent_id,
            duration_ms=duration,
            tokens_used=random.randint(1200, 3500),
            confidence=random.uniform(0.85, 0.95) if success else 0.0
        )


class ExecutionAgent(BaseAgent):
    """执行Agent v2.0"""
    
    def __init__(self, agent_id: str, memory: FourTierMemory, bus: MessageBus):
        profile = AgentProfile(
            agent_id=agent_id,
            name=f"Execution-{agent_id[-4:]}",
            capabilities=["file_operations", "kanban_sync", "data_entry", "status_update"],
            max_concurrent=3,
            specialization="execution"
        )
        super().__init__(profile, memory, bus)
    
    async def execute(self, subtask: SubTask) -> ExecutionResult:
        start = time.time()
        self.profile.health_status = AgentStatus.BUSY
        
        await asyncio.sleep(random.uniform(0.3, 1.0))
        
        success = random.random() > 0.05  # 95%成功率
        duration = (time.time() - start) * 1000
        
        self.profile.update_performance(success, duration)
        self.profile.health_status = AgentStatus.IDLE
        
        return ExecutionResult(
            task_id=subtask.id,
            status="success" if success else "failed",
            output={"operations_completed": random.randint(1, 5), "sync_status": "ok"},
            agent_id=self.profile.agent_id,
            duration_ms=duration,
            tokens_used=random.randint(200, 800),
            confidence=0.95 if success else 0.0
        )


class CreativeAgent(BaseAgent):
    """创意Agent v5.0 新增"""
    
    def __init__(self, agent_id: str, memory: FourTierMemory, bus: MessageBus):
        profile = AgentProfile(
            agent_id=agent_id,
            name=f"Creative-{agent_id[-4:]}",
            capabilities=["content_generation", "design", "innovation", "brainstorming"],
            max_concurrent=1,
            specialization="creative"
        )
        super().__init__(profile, memory, bus)
    
    async def execute(self, subtask: SubTask) -> ExecutionResult:
        start = time.time()
        self.profile.health_status = AgentStatus.BUSY
        
        await asyncio.sleep(random.uniform(1.0, 2.5))
        
        success = random.random() > 0.10  # 90%成功率
        duration = (time.time() - start) * 1000
        
        self.profile.update_performance(success, duration)
        self.profile.health_status = AgentStatus.IDLE
        
        return ExecutionResult(
            task_id=subtask.id,
            status="success" if success else "failed",
            output={
                "ideas": ["创意方案A", "创意方案B", "创意方案C"],
                "innovation_score": random.uniform(0.75, 0.95)
            },
            agent_id=self.profile.agent_id,
            duration_ms=duration,
            tokens_used=random.randint(1500, 4000),
            confidence=random.uniform(0.80, 0.92) if success else 0.0
        )


class VerifierAgent(BaseAgent):
    """验证Agent v5.0 新增 - 结果验证与交叉检查"""
    
    def __init__(self, agent_id: str, memory: FourTierMemory, bus: MessageBus):
        profile = AgentProfile(
            agent_id=agent_id,
            name=f"Verifier-{agent_id[-4:]}",
            capabilities=["result_verification", "cross_check", "quality_assurance", "consensus_arbitration"],
            max_concurrent=2,
            specialization="verification"
        )
        super().__init__(profile, memory, bus)
    
    async def execute(self, subtask: SubTask) -> ExecutionResult:
        start = time.time()
        self.profile.health_status = AgentStatus.BUSY
        
        await asyncio.sleep(random.uniform(0.5, 1.2))
        
        results_to_verify = subtask.metadata.get("results", [])
        
        # 模拟验证逻辑
        verified_count = len(results_to_verify)
        issues_found = random.randint(0, max(0, verified_count - 1))
        
        success = random.random() > 0.08  # 92%成功率
        duration = (time.time() - start) * 1000
        
        self.profile.update_performance(success, duration)
        self.profile.health_status = AgentStatus.IDLE
        
        return ExecutionResult(
            task_id=subtask.id,
            status="success" if success else "failed",
            output={
                "verified_count": verified_count,
                "issues_found": issues_found,
                "verification_passed": issues_found == 0,
                "confidence_adjustment": random.uniform(-0.05, 0.05)
            },
            agent_id=self.profile.agent_id,
            duration_ms=duration,
            tokens_used=random.randint(500, 1500),
            confidence=0.90 if success else 0.0
        )
    
    async def verify_consensus(self, results: List[ExecutionResult]) -> Dict:
        """验证多Agent共识结果"""
        outputs = [r.output for r in results if r.status == "success"]
        if not outputs:
            return {"consensus": False, "confidence": 0.0, "issues": ["无有效结果"]}
        
        # 简化共识检测
        return {
            "consensus": len(outputs) >= len(results) * 0.7,
            "confidence": statistics.mean([r.confidence for r in results if r.status == "success"]),
            "agreement_ratio": len(outputs) / len(results),
            "issues": []
        }


# =============================================================================
# 编排器实现
# =============================================================================

class DomainOrchestrator:
    """领域编排器 - 管理特定领域的Agent集群"""
    
    def __init__(self, domain: str, bus: MessageBus, memory: FourTierMemory):
        self.domain = domain
        self.bus = bus
        self.memory = memory
        self.agents: Dict[str, BaseAgent] = {}
        self.task_queue: List[SubTask] = []
    
    def register_agent(self, agent: BaseAgent):
        """注册Agent"""
        self.agents[agent.profile.agent_id] = agent
        # print(f"  [Domain:{self.domain}] 注册Agent: {agent.profile.name}")
    
    def select_best_agent(self, subtask: SubTask) -> Optional[BaseAgent]:
        """基于性能画像选择最优Agent"""
        candidates = []
        for agent in self.agents.values():
            if not agent.can_accept_task():
                continue
            # 计算匹配度
            capability_match = len(
                set(agent.profile.capabilities) & set(subtask.required_capabilities)
            ) / max(len(subtask.required_capabilities), 1)
            
            score = (
                capability_match * 0.4 +
                agent.profile.capability_score * 0.35 +
                (1.0 - agent.profile.current_load) * 0.25
            )
            candidates.append((agent, score))
        
        if not candidates:
            return None
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    async def execute_subtask(self, subtask: SubTask) -> ExecutionResult:
        """执行单个子任务"""
        agent = self.select_best_agent(subtask)
        if not agent:
            return ExecutionResult(
                task_id=subtask.id,
                status="failed",
                output={"error": "无可用Agent"},
                agent_id="none",
                duration_ms=0,
                confidence=0.0
            )
        
        subtask.assigned_agent = agent.profile.agent_id
        subtask.start_time = time.time()
        
        result = await agent.execute(subtask)
        
        subtask.end_time = time.time()
        subtask.status = "completed" if result.status == "success" else "failed"
        subtask.result = result
        
        return result


class MetaOrchestrator:
    """元编排器 - 系统顶层协调"""
    
    def __init__(self):
        self.bus = MessageBus()
        self.memory = FourTierMemory()
        self.domains: Dict[str, DomainOrchestrator] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.execution_history: List[Dict] = []
    
    def register_domain(self, domain: str, orch: DomainOrchestrator):
        """注册领域编排器"""
        self.domains[domain] = orch
        # print(f"✅ 注册领域编排器: {domain}")
    
    def decompose_task(self, task: Task) -> List[SubTask]:
        """任务分解 - 自动DAG生成"""
        # 基于任务类型和描述自动分解
        subtasks = []
        
        if task.task_type == "compound_research":
            # 复合研究任务: 搜索 + 分析 + 验证
            subtasks = [
                SubTask(
                    id=f"{task.id}-search",
                    parent_id=task.id,
                    description=f"搜索: {task.description}",
                    required_capabilities=["web_search", "data_collection"]
                ),
                SubTask(
                    id=f"{task.id}-analyze",
                    parent_id=task.id,
                    description=f"分析: {task.description}",
                    required_capabilities=["data_analysis", "strategy_planning"],
                    dependencies=[f"{task.id}-search"]
                ),
                SubTask(
                    id=f"{task.id}-verify",
                    parent_id=task.id,
                    description=f"验证: {task.description}",
                    required_capabilities=["result_verification"],
                    dependencies=[f"{task.id}-analyze"]
                )
            ]
        elif task.task_type == "batch_execution":
            # 批量执行: 多个独立子任务
            for i in range(5):
                subtasks.append(SubTask(
                    id=f"{task.id}-exec-{i}",
                    parent_id=task.id,
                    description=f"执行子任务 {i+1}: {task.description}",
                    required_capabilities=["file_operations", "kanban_sync"]
                ))
        elif task.task_type == "creative_strategy":
            # 创意策略: 创意 + 分析
            subtasks = [
                SubTask(
                    id=f"{task.id}-creative",
                    parent_id=task.id,
                    description=f"创意生成: {task.description}",
                    required_capabilities=["content_generation", "innovation"]
                ),
                SubTask(
                    id=f"{task.id}-analyze",
                    parent_id=task.id,
                    description=f"策略分析: {task.description}",
                    required_capabilities=["strategy_planning"],
                    dependencies=[f"{task.id}-creative"]
                )
            ]
        elif task.task_type == "consensus_decision":
            # 共识决策: 多Agent并行分析
            for i in range(4):
                subtasks.append(SubTask(
                    id=f"{task.id}-analyze-{i}",
                    parent_id=task.id,
                    description=f"视角{i+1}分析: {task.description}",
                    required_capabilities=["data_analysis", "risk_assessment"]
                ))
        else:
            # 默认单任务
            subtasks = [SubTask(
                id=f"{task.id}-main",
                parent_id=task.id,
                description=task.description,
                required_capabilities=task.required_capabilities
            )]
        
        return subtasks
    
    def determine_execution_mode(self, subtasks: List[SubTask], task: Task) -> ExecutionMode:
        """确定执行模式 - 严格使用任务指定的模式"""
        # 严格遵循任务指定的模式，不再自动覆盖
        # SEQUENTIAL 就是真串行，不做智能转换
        return task.mode
    
    async def execute_task(self, task: Task) -> Dict:
        """执行任务"""
        # print(f"\n{'='*70}")
        # print(f"🚀 Meta-Orchestrator 执行任务: {task.description}")
        # print(f"   任务ID: {task.id} | 模式: {task.mode.value}")
        # print(f"{'='*70}")
        
        # 1. 分解任务
        subtasks = self.decompose_task(task)
        # print(f"📦 任务分解为 {len(subtasks)} 个子任务")
        
        # 2. 确定执行模式
        mode = self.determine_execution_mode(subtasks, task)
        # print(f"⚙️  执行模式: {mode.value}")
        
        # 3. 执行
        start_time = time.time()
        
        if mode == ExecutionMode.SEQUENTIAL:
            results = await self._execute_sequential(subtasks)
        elif mode == ExecutionMode.PARALLEL:
            results = await self._execute_parallel(subtasks)
        elif mode == ExecutionMode.PIPELINE:
            results = await self._execute_pipeline(subtasks)
        elif mode == ExecutionMode.SWARM:
            results = await self._execute_swarm(subtasks)
        elif mode == ExecutionMode.DEBATE:
            results = await self._execute_debate(subtasks)
        else:
            results = await self._execute_sequential(subtasks)
        
        total_duration = (time.time() - start_time) * 1000
        
        # 4. 结果聚合
        success_count = sum(1 for r in results if r.status == "success")
        
        result_summary = {
            "task_id": task.id,
            "mode": mode.value,
            "total_subtasks": len(subtasks),
            "success_count": success_count,
            "failure_count": len(subtasks) - success_count,
            "total_duration_ms": total_duration,
            "agent_involved": list(set(r.agent_id for r in results)),
            "results": [self._result_to_dict(r) for r in results],
            "timestamp": datetime.now().isoformat()
        }
        
        # 记录历史
        self.execution_history.append(result_summary)
        self.memory.store_episodic(result_summary)
        
        # print(f"\n✅ 任务完成: {success_count}/{len(subtasks)} 成功")
        # print(f"⏱️  总耗时: {total_duration:.0f}ms")
        # print(f"📨 消息交换: {self.bus.message_count} 条")
        
        return result_summary
    
    async def _execute_sequential(self, subtasks: List[SubTask]) -> List[ExecutionResult]:
        """串行执行"""
        results = []
        for st in subtasks:
            result = await self._dispatch_subtask(st)
            results.append(result)
            # 传递结果给后续依赖任务
            for next_st in subtasks:
                if st.id in next_st.dependencies:
                    next_st.metadata["prior_results"] = result.output
        return results
    
    async def _execute_parallel(self, subtasks: List[SubTask]) -> List[ExecutionResult]:
        """并行执行"""
        tasks = [self._dispatch_subtask(st) for st in subtasks]
        return await asyncio.gather(*tasks)
    
    async def _execute_pipeline(self, subtasks: List[SubTask]) -> List[ExecutionResult]:
        """流水线执行"""
        # 构建DAG拓扑排序
        executed = {}
        results = []
        
        while len(executed) < len(subtasks):
            ready = [st for st in subtasks 
                     if st.id not in executed 
                     and all(dep in executed for dep in st.dependencies)]
            
            if not ready:
                break
            
            # 并行执行就绪任务
            tasks = []
            for st in ready:
                # 传递依赖结果
                if st.dependencies:
                    dep_results = [executed[dep_id] for dep_id in st.dependencies]
                    st.metadata["prior_results"] = dep_results[-1].output if dep_results else {}
                tasks.append(self._dispatch_subtask(st))
            
            batch_results = await asyncio.gather(*tasks)
            for st, result in zip(ready, batch_results):
                executed[st.id] = result
                results.append(result)
        
        return results
    
    async def _execute_swarm(self, subtasks: List[SubTask]) -> List[ExecutionResult]:
        """群体协作 - 多Agent并行+共识聚合"""
        # 并行执行所有子任务
        tasks = [self._dispatch_subtask(st) for st in subtasks]
        results = await asyncio.gather(*tasks)
        
        # 共识验证
        verifier = self._find_verifier()
        if verifier:
            consensus = await verifier.verify_consensus(results)
            # print(f"   🗳️  共识验证: {'通过' if consensus['consensus'] else '未通过'} "
                  f"(置信度: {consensus['confidence']:.2f})")
        
        return results
    
    async def _execute_debate(self, subtasks: List[SubTask]) -> List[ExecutionResult]:
        """辩论模式 - 多轮迭代"""
        # 第一轮: 各Agent独立分析
        tasks = [self._dispatch_subtask(st) for st in subtasks]
        round1_results = await asyncio.gather(*tasks)
        
        # 第二轮: 基于第一轮结果进行反驳/修正
        # print("   🔄 辩论第2轮: 基于首轮结果修正...")
        for st in subtasks:
            st.metadata["round1_results"] = [r.output for r in round1_results]
        
        tasks = [self._dispatch_subtask(st) for st in subtasks]
        round2_results = await asyncio.gather(*tasks)
        
        return round2_results
    
    async def _dispatch_subtask(self, subtask: SubTask) -> ExecutionResult:
        """分发子任务到对应领域"""
        # 根据能力需求选择领域
        domain = self._select_domain(subtask.required_capabilities)
        domain_orch = self.domains.get(domain)
        
        if not domain_orch:
            return ExecutionResult(
                task_id=subtask.id,
                status="failed",
                output={"error": f"未找到领域编排器: {domain}"},
                agent_id="none",
                duration_ms=0,
                confidence=0.0
            )
        
        return await domain_orch.execute_subtask(subtask)
    
    def _select_domain(self, capabilities: List[str]) -> str:
        """根据能力选择领域"""
        domain_map = {
            "research": ["web_search", "data_collection", "literature_review", "trend_analysis"],
            "execution": ["file_operations", "kanban_sync", "data_entry", "status_update"],
            "creative": ["content_generation", "design", "innovation", "brainstorming"]
        }
        
        scores = {}
        for domain, caps in domain_map.items():
            match = len(set(capabilities) & set(caps))
            scores[domain] = match
        
        # 默认选择匹配度最高的，如果没有匹配则选research
        if scores:
            best = max(scores, key=scores.get)
            if scores[best] > 0:
                return best
        return "research"
    
    def _find_verifier(self) -> Optional[VerifierAgent]:
        """查找验证Agent"""
        for domain_orch in self.domains.values():
            for agent in domain_orch.agents.values():
                if isinstance(agent, VerifierAgent):
                    return agent
        return None
    
    def _result_to_dict(self, result: ExecutionResult) -> Dict:
        return {
            "task_id": result.task_id,
            "status": result.status,
            "agent_id": result.agent_id,
            "duration_ms": result.duration_ms,
            "tokens_used": result.tokens_used,
            "confidence": result.confidence
        }


# =============================================================================
# 基准测试框架
# =============================================================================

class BenchmarkRunner:
    """基准测试运行器"""
    
    def __init__(self, meta_orch: MetaOrchestrator):
        self.meta_orch = meta_orch
        self.results: List[BenchmarkResult] = []
    
    async def run_benchmark(self, test_name: str, tasks: List[Task], iterations: int = 3) -> BenchmarkResult:
        """运行基准测试"""
        # print(f"\n{'='*70}")
        # print(f"📊 基准测试: {test_name}")
        # print(f"   任务数: {len(tasks)} | 迭代次数: {iterations}")
        # print(f"{'='*70}")
        
        all_results = []
        iteration_times = []
        
        for i in range(iterations):
            # print(f"\n🔄 迭代 {i+1}/{iterations}")
            iter_start = time.time()
            
            for task in tasks:
                result = await self.meta_orch.execute_task(task)
                all_results.append(result)
            
            iter_duration = (time.time() - iter_start) * 1000
            iteration_times.append(iter_duration)
        
        # 统计分析
        total_subtasks = sum(r["total_subtasks"] for r in all_results)
        success_count = sum(r["success_count"] for r in all_results)
        failure_count = sum(r["failure_count"] for r in all_results)
        avg_duration = statistics.mean(iteration_times)
        
        # 计算吞吐量
        total_minutes = avg_duration / 1000 / 60
        throughput = len(tasks) / total_minutes if total_minutes > 0 else 0
        
        # Token效率
        total_tokens = sum(
            sum(sub.get("tokens_used", 0) for sub in r["results"])
            for r in all_results
        )
        token_per_task = total_tokens / max(total_subtasks, 1)
        
        benchmark = BenchmarkResult(
            test_name=test_name,
            mode=tasks[0].mode if tasks else ExecutionMode.SEQUENTIAL,
            total_duration_ms=avg_duration,
            agent_count=len(self.meta_orch.domains),
            success_count=success_count,
            failure_count=failure_count,
            avg_task_duration_ms=avg_duration / max(len(tasks), 1),
            throughput=throughput,
            token_efficiency=token_per_task
        )
        
        self.results.append(benchmark)
        return benchmark
    
    def print_report(self):
        """打印测试报告"""
        # print(f"\n{'='*70}")
        # print("📈 基准测试综合报告")
        # print(f"{'='*70}")
        
        for r in self.results:
            # print(f"\n  📋 {r.test_name}")
            # print(f"     模式: {r.mode.value}")
            # print(f"     总耗时: {r.total_duration_ms:.0f}ms")
            # print(f"     Agent数: {r.agent_count}")
            # print(f"     成功/失败: {r.success_count}/{r.failure_count}")
            # print(f"     平均任务耗时: {r.avg_task_duration_ms:.0f}ms")
            # print(f"     吞吐量: {r.throughput:.1f} 任务/分钟")
            # print(f"     Token效率: {r.token_efficiency:.0f} tokens/任务")


# =============================================================================
# 主程序: 初始化系统 + 运行基准测试
# =============================================================================

async def main():
    # print("="*70)
    # print("  🤖 OpenClaw Multi-Agent Framework v5.0")
    # print("  原型系统启动 + 基准测试")
    # print("="*70)
    
    # 初始化系统
    meta_orch = MetaOrchestrator()
    
    # 创建共享组件
    bus = meta_orch.bus
    memory = meta_orch.memory
    
    # ── 创建领域编排器 ──
    research_domain = DomainOrchestrator("research", bus, memory)
    execution_domain = DomainOrchestrator("execution", bus, memory)
    creative_domain = DomainOrchestrator("creative", bus, memory)
    
    # ── 注册Agent ──
    # print("\n📋 注册Agent中...")
    
    # Research域: 2个Research Agent + 1个Analysis Agent
    research_domain.register_agent(ResearchAgent("research_01", memory, bus))
    research_domain.register_agent(ResearchAgent("research_02", memory, bus))
    research_domain.register_agent(AnalysisAgent("analysis_01", memory, bus))
    research_domain.register_agent(VerifierAgent("verifier_01", memory, bus))
    
    # Execution域: 2个Execution Agent
    execution_domain.register_agent(ExecutionAgent("exec_01", memory, bus))
    execution_domain.register_agent(ExecutionAgent("exec_02", memory, bus))
    execution_domain.register_agent(ExecutionAgent("exec_03", memory, bus))
    
    # Creative域: 1个Creative Agent + 1个Analysis Agent
    creative_domain.register_agent(CreativeAgent("creative_01", memory, bus))
    creative_domain.register_agent(AnalysisAgent("analysis_02", memory, bus))
    creative_domain.register_agent(VerifierAgent("verifier_02", memory, bus))
    
    # 注册到Meta-Orchestrator
    meta_orch.register_domain("research", research_domain)
    meta_orch.register_domain("execution", execution_domain)
    meta_orch.register_domain("creative", creative_domain)
    
    # print(f"\n✅ 系统初始化完成")
    # print(f"   领域数: {len(meta_orch.domains)}")
    total_agents = sum(len(d.agents) for d in meta_orch.domains.values())
    # print(f"   Agent总数: {total_agents}")
    
    # ── 运行基准测试 ──
    benchmark = BenchmarkRunner(meta_orch)
    
    # 测试1: 复合研究任务 (串行 vs 流水线)
    # print("\n" + "─"*70)
    # print("测试1: 复合研究任务对比")
    # print("─"*70)
    
    # v4.3风格: 串行
    sequential_tasks = [
        Task(id="seq-research-1", description="分析AI材料科学论文发表策略",
             task_type="compound_research", mode=ExecutionMode.SEQUENTIAL),
        Task(id="seq-research-2", description="调研北航AI实验室合作机会",
             task_type="compound_research", mode=ExecutionMode.SEQUENTIAL),
    ]
    seq_result = await benchmark.run_benchmark("串行模式_复合研究", sequential_tasks, iterations=2)
    
    # v5.0风格: 流水线
    pipeline_tasks = [
        Task(id="pipe-research-1", description="分析AI材料科学论文发表策略",
             task_type="compound_research", mode=ExecutionMode.PIPELINE),
        Task(id="pipe-research-2", description="调研北航AI实验室合作机会",
             task_type="compound_research", mode=ExecutionMode.PIPELINE),
    ]
    pipe_result = await benchmark.run_benchmark("流水线模式_复合研究", pipeline_tasks, iterations=2)
    
    # 测试2: 批量执行任务 (串行 vs 并行)
    # print("\n" + "─"*70)
    # print("测试2: 批量执行任务对比")
    # print("─"*70)
    
    # 串行
    seq_batch = [Task(id=f"seq-batch-{i}", description="批量看板同步",
                      task_type="batch_execution", mode=ExecutionMode.SEQUENTIAL)
                 for i in range(3)]
    seq_batch_result = await benchmark.run_benchmark("串行模式_批量执行", seq_batch, iterations=2)
    
    # 并行
    par_batch = [Task(id=f"par-batch-{i}", description="批量看板同步",
                      task_type="batch_execution", mode=ExecutionMode.PARALLEL)
                 for i in range(3)]
    par_batch_result = await benchmark.run_benchmark("并行模式_批量执行", par_batch, iterations=2)
    
    # 测试3: 群体协作 (Swarm)
    # print("\n" + "─"*70)
    # print("测试3: 共识决策任务 (Swarm模式)")
    # print("─"*70)
    
    swarm_tasks = [
        Task(id="swarm-1", description="评估和光智成融资策略风险",
             task_type="consensus_decision", mode=ExecutionMode.SWARM)
    ]
    swarm_result = await benchmark.run_benchmark("群体协作_共识决策", swarm_tasks, iterations=2)
    
    # 测试4: 辩论模式
    # print("\n" + "─"*70)
    # print("测试4: 争议性分析 (辩论模式)")
    # print("─"*70)
    
    debate_tasks = [
        Task(id="debate-1", description="AI材料发现vs传统实验方法优劣分析",
             task_type="consensus_decision", mode=ExecutionMode.DEBATE)
    ]
    debate_result = await benchmark.run_benchmark("辩论模式_争议分析", debate_tasks, iterations=2)
    
    # ── 打印综合报告 ──
    benchmark.print_report()
    
    # ── 性能对比总结 ──
    # print(f"\n{'='*70}")
    # print("📊 v4.3 vs v5.0 性能对比总结")
    # print(f"{'='*70}")
    
    # print("\n【复合研究任务】")
    # print(f"  串行模式 (v4.3风格): 总耗时 {seq_result.total_duration_ms:.0f}ms")
    # print(f"  流水线模式 (v5.0):    总耗时 {pipe_result.total_duration_ms:.0f}ms")
    if seq_result.total_duration_ms > 0:
        improvement = (1 - pipe_result.total_duration_ms / seq_result.total_duration_ms) * 100
        # print(f"  ⬆️  效率提升: {improvement:.1f}%")
    
    # print("\n【批量执行任务】")
    # print(f"  串行模式 (v4.3风格): 总耗时 {seq_batch_result.total_duration_ms:.0f}ms")
    # print(f"  并行模式 (v5.0):      总耗时 {par_batch_result.total_duration_ms:.0f}ms")
    if seq_batch_result.total_duration_ms > 0:
        improvement = (1 - par_batch_result.total_duration_ms / seq_batch_result.total_duration_ms) * 100
        # print(f"  ⬆️  效率提升: {improvement:.1f}%")
    
    # print("\n【系统吞吐量对比】")
    # print(f"  串行吞吐量: {seq_result.throughput:.1f} 任务/分钟")
    # print(f"  并行吞吐量: {par_batch_result.throughput:.1f} 任务/分钟")
    if seq_result.throughput > 0:
        # print(f"  ⬆️  吞吐量提升: {(par_batch_result.throughput / seq_result.throughput - 1) * 100:.1f}%")
    
    # print("\n【模式特性对比】")
    # print(f"  Swarm模式 平均耗时: {swarm_result.avg_task_duration_ms:.0f}ms")
    # print(f"  Debate模式 平均耗时: {debate_result.avg_task_duration_ms:.0f}ms")
    
    # print(f"\n{'='*70}")
    # print("✅ 基准测试完成!")
    # print("="*70)
    
    # 保存详细结果
    output = {
        "timestamp": datetime.now().isoformat(),
        "system_version": "5.0",
        "benchmarks": [
            {
                "test_name": r.test_name,
                "mode": r.mode.value,
                "total_duration_ms": r.total_duration_ms,
                "success_count": r.success_count,
                "failure_count": r.failure_count,
                "throughput": r.throughput,
                "token_efficiency": r.token_efficiency
            }
            for r in benchmark.results
        ]
    }
    
    output_file = "/Users/mettlyz/.openclaw/workspace/output/task-1794/benchmark_results_v5.json"
    with open(output_file, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    # print(f"\n💾 详细结果已保存: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
V5.0 智能编排器 (Smart Orchestrator)
=====================================
替代V4.3星型Orchestrator，实现混合编排模式

核心升级:
1. 动态路由表：基于Agent能力注册自动更新
2. DAG工作流：支持并行、条件分支、循环
3. 负载均衡：实时监控Agent负载，智能分配
4. 熔断降级：Agent故障时自动切换备用Agent
5. Memory Bus集成：统一记忆共享

版本: v5.0
日期: 2026-04-24
"""

import json
import time
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger('V5_Orchestrator')


# ===========================
# 枚举与数据结构
# ===========================

class AgentStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    OVERLOADED = "overloaded"


class DispatchMode(Enum):
    STAR = "star"       # 星型编排（兼容V4.3）
    HIERARCHY = "hierarchy"  # 分层编排
    MESH = "mesh"       # 网格模式（2026最佳实践）


@dataclass
class AgentCapability:
    """Agent能力描述"""
    agent_id: str
    name: str
    capabilities: List[str] = field(default_factory=list)
    concurrency: int = 1
    success_rate: float = 0.9
    avg_latency_ms: int = 2000
    model: str = ""
    backup_for: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.ACTIVE
    load: float = 0.0
    current_tasks: int = 0

    @property
    def available_slots(self) -> int:
        return max(0, self.concurrency - self.current_tasks)

    @property
    def health_score(self) -> float:
        """Agent健康评分: 综合考虑成功率、负载和状态"""
        if self.status == AgentStatus.INACTIVE:
            return 0.0
        status_penalty = {
            AgentStatus.ACTIVE: 1.0,
            AgentStatus.DEGRADED: 0.7,
            AgentStatus.OVERLOADED: 0.3,
            AgentStatus.INACTIVE: 0.0
        }
        load_penalty = 1.0 - self.load * 0.5  # 满载时扣50%
        return self.success_rate * status_penalty.get(self.status, 0.5) * load_penalty


@dataclass
class Task:
    """任务定义"""
    task_id: str
    title: str
    description: str
    task_type: str  # research, analysis, execution, wiki
    priority: int = 2  # 0最高
    timeout_seconds: int = 300
    requires: List[str] = field(default_factory=list)  # 前置任务ID
    expected_output: str = ""


@dataclass
class ACPMessage:
    """ACP v2.0 消息"""
    version: str = "2.0"
    message_id: str = field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:8]}")
    from_agent: str = ""
    to_agent: str = ""
    msg_type: str = "task_dispatch"
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    payload: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)


@dataclass
class TraceSpan:
    """OpenTelemetry风格的Trace Span"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation: str
    agent_id: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "running"
    duration_ms: Optional[float] = None
    metadata: Dict = field(default_factory=dict)


# ===========================
# Agent注册中心
# ===========================

class AgentRegistry:
    """Agent动态注册与发现中心"""

    def __init__(self):
        self._agents: Dict[str, AgentCapability] = {}
        self._capability_index: Dict[str, List[str]] = defaultdict(list)

    def register(self, agent: AgentCapability):
        """注册Agent"""
        self._agents[agent.agent_id] = agent
        for cap in agent.capabilities:
            self._capability_index[cap.lower()].append(agent.agent_id)
        logger.info(f"📝 注册Agent: {agent.name} ({agent.agent_id}) - 能力: {', '.join(agent.capabilities)}")

    def unregister(self, agent_id: str):
        """注销Agent"""
        if agent_id in self._agents:
            agent = self._agents.pop(agent_id)
            for cap in agent.capabilities:
                if agent_id in self._capability_index[cap.lower()]:
                    self._capability_index[cap.lower()].remove(agent_id)
            logger.info(f"🗑️ 注销Agent: {agent_id}")

    def find_by_capability(self, capability: str) -> List[str]:
        """按能力查找Agent"""
        return self._capability_index.get(capability.lower(), [])

    def get(self, agent_id: str) -> Optional[AgentCapability]:
        return self._agents.get(agent_id)

    def list_active(self) -> List[AgentCapability]:
        return [a for a in self._agents.values() if a.status == AgentStatus.ACTIVE]

    def get_all(self) -> Dict[str, AgentCapability]:
        return dict(self._agents)

    def to_json(self) -> Dict:
        return {
            agent_id: asdict(agent) for agent_id, agent in self._agents.items()
        }


# ===========================
# 负载均衡器
# ===========================

class LoadBalancer:
    """智能负载均衡器"""

    def select(self, required_capabilities: List[str], registry: AgentRegistry) -> Optional[str]:
        """
        选择最优Agent
        
        算法: 健康评分 + 可用槽位 + 能力匹配度
        """
        candidates = []
        
        for cap in required_capabilities:
            agent_ids = registry.find_by_capability(cap)
            candidates.extend(agent_ids)
        
        if not candidates:
            return None
        
        # 去重
        candidates = list(set(candidates))
        
        best_agent = None
        best_score = -1.0
        
        for agent_id in candidates:
            agent = registry.get(agent_id)
            if not agent or agent.status in (AgentStatus.INACTIVE, AgentStatus.OVERLOADED):
                continue
            if agent.available_slots <= 0:
                continue
            
            score = agent.health_score
            # 优先选择并发能力更高的
            score *= (1 + agent.available_slots * 0.1)
            
            if score > best_score:
                best_score = score
                best_agent = agent_id
        
        return best_agent


# ===========================
# 熔断器
# ===========================

class CircuitBreaker:
    """Agent级熔断器"""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures: Dict[str, int] = defaultdict(int)
        self._last_failure_time: Dict[str, float] = {}
        self._circuit_open: Dict[str, bool] = {}

    def record_success(self, agent_id: str):
        self._failures[agent_id] = 0
        self._circuit_open[agent_id] = False

    def record_failure(self, agent_id: str):
        self._failures[agent_id] += 1
        self._last_failure_time[agent_id] = time.time()
        
        if self._failures[agent_id] >= self.failure_threshold:
            self._circuit_open[agent_id] = True
            logger.warning(f"🔌 熔断器开启: {agent_id} (连续失败{self._failures[agent_id]}次)")

    def is_available(self, agent_id: str) -> bool:
        if agent_id not in self._circuit_open or not self._circuit_open[agent_id]:
            return True
        
        # 检查是否过了恢复超时
        elapsed = time.time() - self._last_failure_time.get(agent_id, 0)
        if elapsed >= self.recovery_timeout:
            self._circuit_open[agent_id] = False
            self._failures[agent_id] = 0
            logger.info(f"🔓 熔断器关闭: {agent_id} (恢复)")
            return True
        
        return False

    def handle_failure(self, agent_id: str, error: Exception):
        self.record_failure(agent_id)


# ===========================
# 记忆总线 (Memory Bus)
# ===========================

class MemoryBus:
    """
    统一记忆总线
    
    整合V4.3分散的记忆系统:
    • 短期记忆: TTL过期自动清理
    • 长期记忆: 结构化存储
    • 共享上下文: Agent间实时共享
    """

    def __init__(self):
        self._short_term: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expire_time)
        self._long_term: Dict[str, Any] = {}
        self._shared_context: Dict[str, Any] = {}
        self._access_log: List[Dict] = []

    def store_short(self, key: str, value: Any, ttl_seconds: int = 3600):
        self._short_term[key] = (value, time.time() + ttl_seconds)

    def store_long(self, key: str, value: Any):
        self._long_term[key] = value

    def store_context(self, key: str, value: Any):
        self._shared_context[key] = value

    def get_short(self, key: str) -> Optional[Any]:
        if key in self._short_term:
            value, expire = self._short_term[key]
            if time.time() < expire:
                self._access_log.append({"type": "short", "key": key, "ts": time.time()})
                return value
            else:
                del self._short_term[key]
        return None

    def get_long(self, key: str) -> Optional[Any]:
        self._access_log.append({"type": "long", "key": key, "ts": time.time()})
        return self._long_term.get(key)

    def get_context(self, key: str) -> Optional[Any]:
        self._access_log.append({"type": "context", "key": key, "ts": time.time()})
        return self._shared_context.get(key)

    def query(self, query: str, scope: str = "all") -> List[Dict]:
        """统一查询接口"""
        results = []
        if scope in ("short", "all"):
            for key, (value, expire) in self._short_term.items():
                if time.time() < expire and query.lower() in key.lower():
                    results.append({"key": key, "value": value, "type": "short"})
        if scope in ("long", "all"):
            for key, value in self._long_term.items():
                if query.lower() in key.lower():
                    results.append({"key": key, "value": value, "type": "long"})
        if scope in ("context", "all"):
            for key, value in self._shared_context.items():
                if query.lower() in key.lower():
                    results.append({"key": key, "value": value, "type": "context"})
        return results

    def cleanup_expired(self):
        """清理过期短期记忆"""
        now = time.time()
        expired = [k for k, (_, exp) in self._short_term.items() if now >= exp]
        for k in expired:
            del self._short_term[k]
        return len(expired)


# ===========================
# DAG工作流引擎
# ===========================

class DAGNode:
    """DAG节点"""
    def __init__(self, node_id: str, task: Task, agent_id: str, parallel: bool = False):
        self.node_id = node_id
        self.task = task
        self.agent_id = agent_id
        self.parallel = parallel
        self.dependencies: Set[str] = set()
        self.status = "pending"
        self.result: Optional[Any] = None
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    @property
    def duration_ms(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None


class DAGWorkflowEngine:
    """DAG工作流引擎 - 支持并行协作"""

    def __init__(self, registry: AgentRegistry, load_balancer: LoadBalancer,
                 circuit_breaker: CircuitBreaker, memory_bus: MemoryBus):
        self.registry = registry
        self.load_balancer = load_balancer
        self.circuit_breaker = circuit_breaker
        self.memory_bus = memory_bus
        self._nodes: Dict[str, DAGNode] = {}
        self._edges: Dict[str, List[str]] = defaultdict(list)  # parent -> children
        self._reverse_edges: Dict[str, List[str]] = defaultdict(list)  # child -> parents
        self.trace_spans: List[TraceSpan] = []

    def add_node(self, task: Task, parallel: bool = False) -> str:
        """添加节点"""
        node_id = task.task_id
        agent_id = self.load_balancer.select([task.task_type], self.registry)
        if not agent_id:
            # 尝试找备用Agent
            for agent in self.registry.list_active():
                if task.task_type in agent.capabilities:
                    agent_id = agent.agent_id
                    break
        
        node = DAGNode(node_id, task, agent_id or "unknown", parallel)
        self._nodes[node_id] = node
        
        # 添加依赖
        for dep_id in task.requires:
            node.dependencies.add(dep_id)
            self._edges[dep_id].append(node_id)
            self._reverse_edges[node_id].append(dep_id)
        
        return node_id

    def get_ready_nodes(self) -> List[DAGNode]:
        """获取所有就绪节点（依赖已全部完成）"""
        ready = []
        for node in self._nodes.values():
            if node.status != "pending":
                continue
            deps_met = all(
                self._nodes[dep].status == "completed"
                for dep in node.dependencies
                if dep in self._nodes
            )
            if deps_met:
                ready.append(node)
        return ready

    def is_complete(self) -> bool:
        return all(n.status in ("completed", "failed") for n in self._nodes.values())

    def collect_results(self) -> Dict:
        return {
            node_id: {
                "status": node.status,
                "agent_id": node.agent_id,
                "duration_ms": node.duration_ms,
                "result": node.result
            }
            for node_id, node in self._nodes.items()
        }

    async def _execute_node(self, node: DAGNode, trace_id: str) -> bool:
        """执行单个节点"""
        if not self.circuit_breaker.is_available(node.agent_id):
            # 尝试备用Agent
            agent = self.registry.get(node.agent_id)
            if agent and agent.backup_for:
                logger.info(f"  🔄 {node.agent_id} 熔断，切换到备用Agent")
                node.agent_id = agent.backup_for[0]
        
        node.status = "running"
        node.start_time = time.time()
        
        # 创建Trace Span
        span = TraceSpan(
            trace_id=trace_id,
            span_id=str(uuid.uuid4())[:8],
            parent_span_id=None,
            operation="agent_execute",
            agent_id=node.agent_id,
            start_time=node.start_time,
            metadata={"task_id": node.task.task_id, "task_type": node.task.task_type}
        )
        
        try:
            # 模拟Agent执行（实际应用中调用真实Agent）
            agent = self.registry.get(node.agent_id)
            if not agent:
                raise ValueError(f"Agent {node.agent_id} not found")
            
            # 模拟执行延迟
            delay = agent.avg_latency_ms / 1000.0 * (0.8 + 0.4 * hash(node.node_id) % 100 / 100)
            await asyncio.sleep(delay)
            
            # 模拟成功率
            if hash(node.node_id) % 100 < agent.success_rate * 100:
                node.status = "completed"
                node.result = {"status": "success", "agent": node.agent_id, "task": node.task.title}
                self.circuit_breaker.record_success(node.agent_id)
                node.end_time = time.time()
                logger.info(f"  ✅ {node.node_id} 完成 [{node.agent_id}] ({node.duration_ms:.0f}ms)")
            else:
                node.status = "failed"
                node.result = {"status": "failed", "error": "Simulated failure"}
                self.circuit_breaker.record_failure(node.agent_id)
                node.end_time = time.time()
                logger.warning(f"  ❌ {node.node_id} 失败 [{node.agent_id}] ({node.duration_ms:.0f}ms)")
                
        except Exception as e:
            node.status = "failed"
            node.result = {"status": "error", "error": str(e)}
            self.circuit_breaker.record_failure(node.agent_id)
            node.end_time = time.time()
            logger.error(f"  ❌ {node.node_id} 异常 [{node.agent_id}]: {e}")
        
        if node.end_time is None:
            node.end_time = time.time()
        span.end_time = node.end_time
        span.duration_ms = node.duration_ms
        span.status = node.status
        self.trace_spans.append(span)
        
        return node.status == "completed"

    async def execute(self, trace_id: str = None) -> Dict:
        """执行DAG工作流"""
        if not trace_id:
            trace_id = str(uuid.uuid4())[:8]
        
        logger.info(f"🚀 开始DAG执行 (Trace: {trace_id})")
        logger.info(f"   节点数: {len(self._nodes)}, 边数: {sum(len(v) for v in self._edges.values())}")
        
        start_time = time.time()
        
        while not self.is_complete():
            ready = self.get_ready_nodes()
            if not ready:
                # 检查是否有未完成但有未完成依赖的节点（死锁检测）
                pending = [n for n in self._nodes.values() if n.status == "pending"]
                if pending:
                    logger.warning(f"  ⚠️ 检测到{len(pending)}个节点无法执行（依赖未满足）")
                    for n in pending:
                        n.status = "failed"
                        n.result = {"status": "blocked", "reason": "Dependency not met"}
                break
            
            # 分组：并行节点和串行节点
            parallel_nodes = [n for n in ready if n.parallel]
            serial_nodes = [n for n in ready if not n.parallel]
            
            # 并行执行
            if parallel_nodes:
                logger.info(f"  ⚡ 并行执行 {len(parallel_nodes)} 个节点")
                tasks = [self._execute_node(n, trace_id) for n in parallel_nodes]
                await asyncio.gather(*tasks)
            
            # 串行执行
            for node in serial_nodes:
                logger.info(f"  📦 串行执行 {node.node_id}")
                await self._execute_node(node, trace_id)
        
        total_time = (time.time() - start_time) * 1000
        results = self.collect_results()
        results["_meta"] = {
            "trace_id": trace_id,
            "total_time_ms": total_time,
            "total_nodes": len(self._nodes),
            "completed": sum(1 for n in self._nodes.values() if n.status == "completed"),
            "failed": sum(1 for n in self._nodes.values() if n.status == "failed"),
            "trace_spans": len(self.trace_spans)
        }
        
        logger.info(f"🏁 DAG执行完成: {total_time:.0f}ms, "
                   f"完成: {results['_meta']['completed']}, "
                   f"失败: {results['_meta']['failed']}")
        
        return results


# ===========================
# 智能编排器 (主入口)
# ===========================

class SmartOrchestrator:
    """
    V5.0 智能编排器 - 替代V4.3星型Orchestrator
    """

    def __init__(self, mode: DispatchMode = DispatchMode.MESH):
        self.mode = mode
        self.registry = AgentRegistry()
        self.load_balancer = LoadBalancer()
        self.circuit_breaker = CircuitBreaker()
        self.memory_bus = MemoryBus()
        self.dag_engine = DAGWorkflowEngine(
            self.registry, self.load_balancer, self.circuit_breaker, self.memory_bus
        )
        self.dispatch_log: List[Dict] = []

    def setup_default_agents(self):
        """设置默认4类Agent（V4.3兼容）"""
        agents = [
            AgentCapability("research_agent", "研究代理",
                          capabilities=["research", "search", "paper"],
                          concurrency=2, success_rate=0.92, avg_latency_ms=2500,
                          model="moonshot/kimi-k2.6", backup_for=["analysis_agent"]),
            AgentCapability("analysis_agent", "分析代理",
                          capabilities=["analysis", "strategy", "report"],
                          concurrency=1, success_rate=0.88, avg_latency_ms=2300,
                          model="alicodingplan/kimi-k2.5", backup_for=["research_agent"]),
            AgentCapability("execution_agent", "执行代理",
                          capabilities=["execution", "file", "sync", "upload"],
                          concurrency=3, success_rate=0.95, avg_latency_ms=1500,
                          model="huoshanCoding/ark-code-latest", backup_for=["wiki_agent"]),
            AgentCapability("wiki_agent", "知识库代理",
                          capabilities=["wiki", "knowledge", "graph", "index"],
                          concurrency=1, success_rate=0.90, avg_latency_ms=2000,
                          model="dmxapi/kimi-k2.5-free", backup_for=["analysis_agent"]),
        ]
        for agent in agents:
            self.registry.register(agent)

    async def dispatch_task(self, task: Task) -> Dict:
        """分发单个任务"""
        trace_id = str(uuid.uuid4())[:8]
        logger.info(f"📤 分发任务: {task.title} (Trace: {trace_id})")
        
        dag = self.dag_engine
        dag.add_node(task, parallel=False)
        result = await dag.execute(trace_id)
        
        # 存储到Memory Bus
        self.memory_bus.store_short(f"result:{task.task_id}", result, ttl_seconds=7200)
        
        self.dispatch_log.append({
            "task_id": task.task_id,
            "trace_id": trace_id,
            "timestamp": datetime.now().isoformat(),
            "result": result
        })
        
        return result

    async def dispatch_collaborative_task(self, tasks: List[Task], parallel_groups: List[List[int]] = None) -> Dict:
        """
        分发协作任务（多Agent协作）
        
        parallel_groups: [[0,1], [2,3]] 表示索引0和1的任务可并行，2和3可并行
        """
        trace_id = str(uuid.uuid4())[:8]
        logger.info(f"📤 分发协作任务: {len(tasks)}个 (Trace: {trace_id})")
        
        dag = self.dag_engine
        
        # 添加所有节点
        for i, task in enumerate(tasks):
            is_parallel = False
            if parallel_groups:
                for group in parallel_groups:
                    if i in group and len(group) > 1:
                        is_parallel = True
                        break
            dag.add_node(task, parallel=is_parallel)
        
        result = await dag.execute(trace_id)
        
        # 存储到Memory Bus
        self.memory_bus.store_long(f"collaborative:{trace_id}", result)
        
        self.dispatch_log.append({
            "type": "collaborative",
            "trace_id": trace_id,
            "timestamp": datetime.now().isoformat(),
            "result": result
        })
        
        return result

    def get_status(self) -> Dict:
        """获取编排器状态"""
        return {
            "mode": self.mode.value,
            "agents": self.registry.to_json(),
            "memory_bus_stats": {
                "short_term": len(self._short_term_keys()),
                "long_term": len(self.memory_bus._long_term),
                "context": len(self.memory_bus._shared_context),
                "access_log": len(self.memory_bus._access_log)
            },
            "dispatch_log_count": len(self.dispatch_log),
            "trace_spans": len(self.dag_engine.trace_spans)
        }

    def _short_term_keys(self):
        return list(self.memory_bus._short_term.keys())

    def to_report(self) -> Dict:
        """生成编排器报告"""
        agents = self.registry.get_all()
        return {
            "version": "5.0",
            "timestamp": datetime.now().isoformat(),
            "dispatch_mode": self.mode.value,
            "total_agents": len(agents),
            "agents": {
                aid: {
                    "name": a.name,
                    "capabilities": a.capabilities,
                    "concurrency": a.concurrency,
                    "success_rate": a.success_rate,
                    "status": a.status.value,
                    "load": a.load,
                    "health_score": a.health_score
                }
                for aid, a in agents.items()
            },
            "circuit_breaker_status": {
                agent_id: self.circuit_breaker.is_available(agent_id)
                for agent_id in agents
            },
            "memory_bus": {
                "short_term_items": len(self.memory_bus._short_term),
                "long_term_items": len(self.memory_bus._long_term),
                "context_items": len(self.memory_bus._shared_context),
                "total_queries": len(self.memory_bus._access_log)
            },
            "total_dispatches": len(self.dispatch_log),
            "total_trace_spans": len(self.dag_engine.trace_spans)
        }


# ===========================
# 主函数 - 演示与测试
# ===========================

async def main():
    """V5.0 智能编排器演示"""
    print("\n" + "=" * 70)
    print("  🌟 V5.0 智能编排器演示 🌟")
    print("  T1: AI助手优化 - 多智能体协作框架升级")
    print("=" * 70 + "\n")

    orchestrator = SmartOrchestrator(mode=DispatchMode.MESH)
    orchestrator.setup_default_agents()

    # ─── 测试1: 单Agent任务 ───
    print("📦 测试1: 单Agent任务 (Research)")
    print("-" * 50)
    task1 = Task(
        task_id="t1-single",
        title="搜索2026年多智能体协作最新论文",
        description="搜索arXiv和Google Scholar上的最新论文",
        task_type="research"
    )
    result1 = await orchestrator.dispatch_task(task1)
    print(f"  结果: {result1.get('_meta', {}).get('total_time_ms', 0):.0f}ms\n")

    # ─── 测试2: 2Agent串行协作 ───
    print("📦 测试2: 2Agent串行协作 (Research → Analysis)")
    print("-" * 50)
    task2a = Task(
        task_id="t2-research",
        title="多智能体协作架构研究",
        description="研究主流多智能体协作框架",
        task_type="research"
    )
    task2b = Task(
        task_id="t2-analysis",
        title="多智能体协作架构分析",
        description="基于研究结果进行深度分析",
        task_type="analysis",
        requires=["t2-research"]
    )
    result2 = await orchestrator.dispatch_collaborative_task([task2a, task2b])
    print(f"  结果: {result2.get('_meta', {}).get('total_time_ms', 0):.0f}ms\n")

    # ─── 测试3: 2Agent并行协作 ───
    print("📦 测试3: 2Agent并行协作 (Research + Analysis 独立)")
    print("-" * 50)
    orchestrator2 = SmartOrchestrator(mode=DispatchMode.MESH)
    orchestrator2.setup_default_agents()
    task3a = Task(
        task_id="t3-research",
        title="搜索AI材料科学最新进展",
        description="搜索AI在材料科学领域的最新应用",
        task_type="research"
    )
    task3b = Task(
        task_id="t3-analysis",
        title="分析和光智成竞品分析",
        description="分析和光智成的主要竞品",
        task_type="analysis"
    )
    result3 = await orchestrator2.dispatch_collaborative_task([task3a, task3b], parallel_groups=[[0, 1]])
    print(f"  结果: {result3.get('_meta', {}).get('total_time_ms', 0):.0f}ms\n")

    # ─── 测试4: 4Agent DAG协作 ───
    print("📦 测试4: 4Agent完整协作 (DAG)")
    print("-" * 50)
    orchestrator3 = SmartOrchestrator(mode=DispatchMode.MESH)
    orchestrator3.setup_default_agents()
    
    task4a = Task(task_id="t4-research", title="研究", description="研究", task_type="research")
    task4b = Task(task_id="t4-analysis", title="分析", description="分析", task_type="analysis", requires=["t4-research"])
    task4c = Task(task_id="t4-wiki", title="Wiki更新", description="更新知识库", task_type="wiki", requires=["t4-research"])
    task4d = Task(task_id="t4-execution", title="执行", description="执行操作", task_type="execution", requires=["t4-analysis", "t4-wiki"])
    
    # DAG结构: research → (analysis, wiki) → execution
    result4 = await orchestrator3.dispatch_collaborative_task(
        [task4a, task4b, task4c, task4d],
        parallel_groups=[[1, 2]]  # analysis和wiki可并行
    )
    meta4 = result4.get('_meta', {})
    print(f"  结果: {meta4.get('total_time_ms', 0):.0f}ms, "
          f"完成: {meta4.get('completed', 0)}/{meta4.get('total_nodes', 0)}\n")

    # ─── Memory Bus测试 ───
    print("📦 Memory Bus 测试")
    print("-" * 50)
    orchestrator.memory_bus.store_short("test:key1", "短期测试数据", ttl_seconds=60)
    orchestrator.memory_bus.store_long("test:key2", "长期测试数据")
    orchestrator.memory_bus.store_context("test:key3", "共享上下文数据")
    
    q1 = orchestrator.memory_bus.query("test", "all")
    print(f"  查询结果: {len(q1)} 条记忆")
    for item in q1:
        print(f"    [{item['type']}] {item['key']}: {item['value']}")
    print()

    # ─── 状态报告 ───
    report = orchestrator.to_report()
    print("📊 V5.0 编排器状态报告:")
    print("-" * 50)
    print(f"  版本: {report['version']}")
    print(f"  编排模式: {report['dispatch_mode']}")
    print(f"  Agent数量: {report['total_agents']}")
    print(f"  总调度次数: {report['total_dispatches']}")
    print(f"  Trace Spans: {report['total_trace_spans']}")
    print(f"  Memory Bus: 短期={report['memory_bus']['short_term_items']}, "
          f"长期={report['memory_bus']['long_term_items']}, "
          f"上下文={report['memory_bus']['context_items']}")
    
    print("\n" + "=" * 70)
    print("  ✅ V5.0 智能编排器演示完成!")
    print("=" * 70 + "\n")

    # 保存结果
    import os
    output_dir = "/Users/mettlyz/.openclaw/workspace/output/task-1794"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, "v5_orchestrator_demo_result.json")
    with open(output_file, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"💾 结果已保存到: {output_file}")

    return report


if __name__ == "__main__":
    asyncio.run(main())

# openclaw_control_framework_source

> 任务: 搭建OpenClaw子代理的控制框架 [04291956]
> 附件类型: 核心工程代码包
> 生成时间: 2026-05-04 17:24

# 核心工程代码包：OpenClaw子代理控制框架

**版本**: 1.0.0  
**任务ID**: 04291956  
**发布日期**: 2025-07-17  

---

## 一、项目目录结构与模块依赖说明

### 1.1 目录结构

```
openclaw-subagent-framework/
├── README.md
├── requirements.txt
├── config/
│   ├── default.yaml
│   ├── development.yaml
│   └── production.yaml
├── src/
│   ├── __init__.py
│   ├── controller.py          # 主控制器
│   ├── router.py              # 路由与消息分发引擎
│   ├── lifecycle.py           # 生命周期管理与心跳监控
│   ├── agent_registry.py      # 子代理注册表
│   ├── message_types.py       # 消息类型定义
│   └── utils/
│       ├── __init__.py
│       ├── logger.py          # 日志工具
│       └── timer.py           # 定时器工具
├── tests/
│   ├── __init__.py
│   ├── test_controller.py
│   ├── test_router.py
│   └── test_lifecycle.py
├── scripts/
│   ├── start.sh               # Linux/Mac启动脚本
│   ├── start.bat              # Windows启动脚本
│   └── health_check.sh        # 健康检查脚本
└── docker/
    ├── Dockerfile
    └── docker-compose.yml
```

### 1.2 模块依赖说明

| 模块 | 依赖关系 | 说明 |
|------|----------|------|
| `controller.py` | `router.py`, `lifecycle.py`, `agent_registry.py` | 主控制器依赖路由引擎和生命周期管理器 |
| `router.py` | `message_types.py` | 路由引擎依赖消息类型定义 |
| `lifecycle.py` | `utils/timer.py`, `utils/logger.py` | 生命周期管理依赖定时器和日志工具 |
| `agent_registry.py` | 无 | 独立模块，提供子代理注册与查询功能 |
| `message_types.py` | 无 | 纯数据定义模块 |

---

## 二、主控制器实现 (`src/controller.py`)

```python
"""
主控制器模块 - OpenClaw子代理控制框架核心
负责初始化系统、协调子代理注册、路由消息、管理生命周期
"""

import asyncio
import signal
import sys
from typing import Dict, Optional
from dataclasses import dataclass, field

from .router import MessageRouter
from .lifecycle import LifecycleManager
from .agent_registry import AgentRegistry
from .message_types import Message, MessageType, AgentStatus
from .utils.logger import get_logger

logger = get_logger("controller")

@dataclass
class ControllerConfig:
    """控制器配置"""
    host: str = "0.0.0.0"
    port: int = 8080
    heartbeat_interval: int = 30  # 心跳间隔（秒）
    max_agents: int = 100
    enable_tls: bool = False
    cert_path: Optional[str] = None
    key_path: Optional[str] = None
    log_level: str = "INFO"
    agent_timeout: int = 90  # 子代理超时时间（秒）

class OpenClawController:
    """
    OpenClaw控制框架主控制器
    
    负责：
    - 系统初始化与配置加载
    - 子代理注册与注销管理
    - 消息路由与分发
    - 生命周期监控与健康检查
    - 优雅关闭与资源清理
    """
    
    def __init__(self, config: Optional[ControllerConfig] = None):
        self.config = config or ControllerConfig()
        self.registry = AgentRegistry(max_agents=self.config.max_agents)
        self.router = MessageRouter(self.registry)
        self.lifecycle = LifecycleManager(
            registry=self.registry,
            heartbeat_interval=self.config.heartbeat_interval,
            agent_timeout=self.config.agent_timeout
        )
        self._running = False
        self._server = None
        self._shutdown_event = asyncio.Event()
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
    
    def _handle_signal(self, signum, frame):
        """处理系统信号"""
        logger.info(f"收到信号 {signum}，准备优雅关闭...")
        self._shutdown_event.set()
    
    async def initialize(self) -> bool:
        """
        初始化控制器
        
        返回: 初始化成功返回True，失败返回False
        """
        try:
            logger.info(f"初始化OpenClaw控制器 (host={self.config.host}, port={self.config.port})")
            
            # 初始化子模块
            await self.router.initialize()
            await self.lifecycle.initialize()
            
            # 启动心跳监控
            asyncio.create_task(self.lifecycle.start_monitoring())
            
            logger.info("控制器初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"控制器初始化失败: {str(e)}")
            return False
    
    async def start(self) -> None:
        """
        启动控制器主循环
        包含消息处理循环和生命周期管理
        """
        if self._running:
            logger.warning("控制器已在运行中")
            return
        
        self._running = True
        logger.info("启动OpenClaw控制器主循环")
        
        try:
            # 启动消息处理循环
            await self._message_processing_loop()
            
        except asyncio.CancelledError:
            logger.info("消息处理循环被取消")
        except Exception as e:
            logger.error(f"控制器运行异常: {str(e)}")
        finally:
            await self.shutdown()
    
    async def _message_processing_loop(self) -> None:
        """消息处理主循环"""
        while not self._shutdown_event.is_set():
            try:
                # 模拟消息接收（实际应替换为网络IO）
                message = await self._receive_message()
                if message:
                    asyncio.create_task(self._process_message(message))
                
                # 短暂休眠避免CPU空转
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"消息处理循环异常: {str(e)}")
                await asyncio.sleep(1)
    
    async def _receive_message(self) -> Optional[Message]:
        """
        接收消息（占位方法，实际应实现网络监听）
        当前用于测试目的
        """
        # 实际实现应替换为TCP/HTTP/WebSocket监听
        return None
    
    async def _process_message(self, message: Message) -> None:
        """
        处理接收到的消息
        
        参数:
            message: 待处理的消息
        """
        try:
            result = await self.router.route(message)
            if not result.success:
                logger.warning(f"消息路由失败: {result.error}")
        except Exception as e:
            logger.error(f"消息处理异常: {str(e)}")
    
    async def register_agent(self, agent_id: str, agent_type: str, 
                            endpoint: str, metadata: Optional[Dict] = None) -> bool:
        """
        注册新的子代理
        
        参数:
            agent_id: 子代理唯一标识
            agent_type: 子代理类型（如 'worker', 'monitor', 'executor'）
            endpoint: 子代理通信端点
            metadata: 附加元数据
            
        返回: 注册成功返回True
        """
        return await self.registry.register(
            agent_id=agent_id,
            agent_type=agent_type,
            endpoint=endpoint,
            metadata=metadata or {}
        )
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """
        注销子代理
        
        参数:
            agent_id: 子代理唯一标识
            
        返回: 注销成功返回True
        """
        return await self.registry.unregister(agent_id)
    
    async def shutdown(self) -> None:
        """优雅关闭控制器"""
        if not self._running:
            return
        
        logger.info("开始关闭OpenClaw控制器...")
        self._running = False
        
        # 停止生命周期监控
        await self.lifecycle.stop_monitoring()
        
        # 关闭所有子代理连接
        await self.registry.shutdown_all_agents()
        
        # 关闭路由引擎
        await self.router.shutdown()
        
        # 清理资源
        self._server = None
        self._shutdown_event.clear()
        
        logger.info("OpenClaw控制器已关闭")


# 命令行入口
if __name__ == "__main__":
    async def main():
        config = ControllerConfig(
            host="0.0.0.0",
            port=8080,
            heartbeat_interval=30,
            max_agents=50
        )
        controller = OpenClawController(config)
        
        if await controller.initialize():
            # 注册一些测试代理
            await controller.register_agent(
                agent_id="agent-001",
                agent_type="worker",
                endpoint="tcp://localhost:9001",
                metadata={"version": "1.0", "capabilities": ["compute", "storage"]}
            )
            await controller.register_agent(
                agent_id="agent-002",
                agent_type="monitor",
                endpoint="tcp://localhost:9002",
                metadata={"version": "1.1", "capabilities": ["metrics", "logging"]}
            )
            
            await controller.start()
        else:
            logger.error("控制器初始化失败，退出")
            sys.exit(1)
    
    asyncio.run(main())
```

---

## 三、子代理路由与消息分发引擎 (`src/router.py`)

```python
"""
消息路由引擎 - 负责根据消息类型和目标将消息分发到对应的子代理
"""

import asyncio
from typing import Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from .agent_registry import AgentRegistry
from .message_types import Message, MessageType, RouteResult, AgentInfo

class RoutingStrategy(Enum):
    """路由策略"""
    ROUND_ROBIN = "round_robin"      # 轮询
    LEAST_CONNECTIONS = "least_conn" # 最少连接
    RANDOM = "random"                # 随机
    HASH_BASED = "hash_based"        # 基于哈希
    BROADCAST = "broadcast"          # 广播

@dataclass
class RoutingRule:
    """路由规则"""
    message_type: MessageType
    target_agent_types: List[str]
    strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN
    priority: int = 0
    timeout: int = 30
    retry_count: int = 3
    filter_func: Optional[Callable] = None

class MessageRouter:
    """
    消息路由器
    
    负责：
    - 定义路由规则
    - 根据规则选择目标子代理
    - 执行消息分发
    - 处理路由失败重试
    """
    
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self._rules: Dict[MessageType, RoutingRule] = {}
        self._middlewares: List[Callable] = []
        self._round_robin_counters: Dict[str, int] = {}
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """初始化路由引擎"""
        self._register_default_rules()
        logger.info("路由引擎初始化完成")
    
    def _register_default_rules(self) -> None:
        """注册默认路由规则"""
        self.add_rule(RoutingRule(
            message_type=MessageType.TASK_ASSIGN,
            target_agent_types=["worker", "executor"],
            strategy=RoutingStrategy.LEAST_CONNECTIONS,
            priority=10
        ))
        self.add_rule(RoutingRule(
            message_type=MessageType.STATUS_REPORT,
            target_agent_types=["monitor"],
            strategy=RoutingStrategy.ROUND_ROBIN,
            priority=5
        ))
        self.add_rule(RoutingRule(
            message_type=MessageType.HEARTBEAT,
            target_agent_types=["*"],  # 所有代理
            strategy=RoutingStrategy.BROADCAST,
            priority=1
        ))
        self.add_rule(RoutingRule(
            message_type=MessageType.COMMAND,
            target_agent_types=["worker", "monitor", "executor"],
            strategy=RoutingStrategy.HASH_BASED,
            priority=8
        ))
    
    def add_rule(self, rule: RoutingRule) -> None:
        """添加路由规则"""
        self._rules[rule.message_type] = rule
        logger.debug(f"添加路由规则: {rule.message_type.value} -> {rule.target_agent_types}")
    
    def add_middleware(self, middleware: Callable) -> None:
        """添加中间件"""
        self._middlewares.append(middleware)
    
    async def route(self, message: Message) -> RouteResult:
        """
        路由消息到目标子代理
        
        参数:
            message: 待路由的消息
            
        返回:
            RouteResult: 路由结果
        """
        try:
            # 执行中间件链
            processed_message = message
            for middleware in self._middlewares:
                processed_message = await middleware(processed_message)
                if processed_message is None:
                    return RouteResult(
                        success=False,
                        error="消息被中间件拦截",
                        message_id=message.id
                    )
            
            # 获取路由规则
            rule = self._rules.get(message.type)
            if not rule:
                return RouteResult(
                    success=False,
                    error=f"未找到消息类型 {message.type} 的路由规则",
                    message_id=message.id
                )
            
            # 获取候选代理
            candidates = await self._get_candidate_agents(rule, message)
            if not candidates:
                return RouteResult(
                    success=False,
                    error="没有可用的目标代理",
                    message_id=message.id
                )
            
            # 根据策略选择目标代理
            target = await self._select_target(candidates, rule, message)
            
            # 发送消息
            success = await self._send_to_agent(target, processed_message)
            if not success:
                # 重试逻辑
                for attempt in range(rule.retry_count):
                    logger.warning(f"消息发送失败，重试 {attempt + 1}/{rule.retry_count}")
                    target = await self._select_target(candidates, rule, message)
                    success = await self._send_to_agent(target, processed_message)
                    if success:
                        break
            
            return RouteResult(
                success=success,
                target_agent=target.agent_id if target else None,
                message_id=message.id,
                error=None if success else "所有重试均失败"
            )
            
        except Exception as e:
            logger.error(f"路由异常: {str(e)}")
            return RouteResult(
                success=False,
                error=str(e),
                message_id=message.id
            )
    
    async def _get_candidate_agents(self, rule: RoutingRule, 
                                    message: Message) -> List[AgentInfo]:
        """获取候选代理列表"""
        candidates = []
        for agent_type in rule.target_agent_types:
            if agent_type == "*":
                agents = await self.registry.get_all_agents()
            else:
                agents = await self.registry.get_agents_by_type(agent_type)
            
            for agent in agents:
                if agent.status == AgentStatus.ONLINE:
                    if rule.filter_func:
                        if await rule.filter_func(agent, message):
                            candidates.append(agent)
                    else:
                        candidates.append(agent)
        
        return candidates
    
    async def _select_target(self, candidates: List[AgentInfo], 
                            rule: RoutingRule, 
                            message: Message) -> Optional[AgentInfo]:
        """根据策略选择目标代理"""
        if not candidates:
            return None
        
        if rule.strategy == RoutingStrategy.ROUND_ROBIN:
            return await self._round_robin_select(candidates, rule)
        elif rule.strategy == RoutingStrategy.LEAST_CONNECTIONS:
            return await self._least_connections_select(candidates)
        elif rule.strategy == RoutingStrategy.RANDOM:
            return candidates[hash(str(message.id)) % len(candidates)]
        elif rule.strategy == RoutingStrategy.HASH_BASED:
            return candidates[hash(message.target_id) % len(candidates)]
        elif rule.strategy == RoutingStrategy.BROADCAST:
            # 广播模式下返回第一个，实际会发送给所有
            return candidates[0]
        else:
            return candidates[0]
    
    async def _round_robin_select(self, candidates: List[AgentInfo], 
                                  rule: RoutingRule) -> AgentInfo:
        """轮询选择"""
        key = f"{rule.message_type.value}_{'_'.join(rule.target_agent_types)}"
        async with self._lock:
            counter = self._round_robin_counters.get(key, 0)
            target = candidates[counter % len(candidates)]
            self._round_robin_counters[key] = counter + 1
            return target
    
    async def _least_connections_select(self, candidates: List[AgentInfo]) -> AgentInfo:
        """最少连接选择"""
        # 获取每个代理的当前连接数（简化实现）
        return min(candidates, key=lambda x: x.active_connections)
    
    async def _send_to_agent(self, agent: AgentInfo, message: Message) -> bool:
        """
        发送消息到指定代理
        
        参数:
            agent: 目标代理
            message: 消息内容
            
        返回: 发送成功返回True
        """
        try:
            # 实际实现应使用适当的传输协议（TCP/HTTP/WebSocket）
            logger.debug(f"发送消息 {message.id} 到代理 {agent.agent_id}")
            
            # 模拟发送（实际应替换为真实网络调用）
            await asyncio.sleep(0.001)
            
            # 更新
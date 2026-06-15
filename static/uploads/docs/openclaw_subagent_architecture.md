# openclaw_subagent_architecture

> 任务: 搭建OpenClaw子代理的控制框架 [04291956]
> 附件类型: 技术方案与架构设计
> 生成时间: 2026-05-04 17:21

# 技术方案与架构设计：OpenClaw子代理控制框架

**文档编号**：OC-ARCH-001  
**版本**：1.0  
**状态**：定稿  
**创建日期**：2024-01-15  
**最后更新**：2024-01-15  

---

## 1. 系统概述与设计目标

### 1.1 系统背景

OpenClaw是一个分布式多代理协作平台，本框架旨在为其子代理提供标准化、可扩展的控制能力。子代理（Sub-Agent）是指部署在边缘节点或容器中的轻量级执行单元，负责完成特定领域的任务，如数据处理、模型推理、命令执行等。当前面临的挑战包括：子代理缺乏统一控制平面、状态管理混乱、通信协议不统一、故障恢复能力弱。

### 1.2 设计目标

| 目标类别 | 具体目标 | 可量化指标 |
|---------|---------|-----------|
| **控制力** | 实现全生命周期管理 | 子代理启动、停止、升级时间 < 5秒 |
| **可靠性** | 故障自动检测与恢复 | 故障检测时间 < 3秒，恢复成功率 > 99.5% |
| **扩展性** | 支持水平扩展 | 单控制节点管理子代理数量 ≥ 1000 |
| **安全性** | 端到端加密与权限控制 | 通信加密率 100%，最小权限原则 |
| **标准化** | 统一协议与接口 | API兼容性版本化，向后兼容 ≥ 2个主版本 |

### 1.3 适用范围

本框架适用于OpenClaw生态中所有子代理的创建、注册、配置、调度、监控和销毁等控制场景。不涉及子代理内部业务逻辑的实现细节。

---

## 2. 核心架构拓扑与模块职责划分

### 2.1 物理架构拓扑

```
┌─────────────────────────────────────────────────────────────┐
│                    控制平面 (Control Plane)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ API网关   │  │ 状态服务  │  │ 调度器   │  │ 监控中心 │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │              │              │              │        │
│  ┌────┴──────────────────────────────┴──────────────┐      │
│  │             消息总线 (Message Bus)                │      │
│  └──────────────────────────────────────────────────┘      │
└────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  子代理实例 1   │  │  子代理实例 2   │  │  子代理实例 N   │
│  (边缘节点 A)   │  │  (边缘节点 B)   │  │  (容器集群 C)   │
└────────────────┘  └────────────────┘  └────────────────┘
```

### 2.2 模块职责划分

#### 2.2.1 控制平面模块

| 模块名称 | 核心职责 | 关键技术组件 |
|---------|---------|-------------|
| **API网关** | 统一入口、请求路由、身份认证、限流熔断 | Envoy + JWT认证 + 速率限制器 |
| **状态服务** | 维护子代理注册表、状态持久化、心跳处理 | etcd + 状态机 + 一致性哈希 |
| **调度器** | 任务分配、负载均衡、亲和性调度 | 自定义调度算法 + 资源指标采集 |
| **监控中心** | 指标采集、告警规则、日志聚合 | Prometheus + Grafana + ELK |

#### 2.2.2 子代理侧模块

| 模块名称 | 核心职责 | 实现方式 |
|---------|---------|---------|
| **代理核心** | 生命周期管理、心跳发送、配置同步 | 守护进程 + 事件循环 |
| **任务执行器** | 接收并执行具体任务指令 | 插件化架构 + 沙箱隔离 |
| **资源监控器** | 采集CPU、内存、网络等指标 | 系统调用 + 周期性上报 |
| **安全模块** | 通信加密、证书管理、访问控制 | mTLS + 证书轮换 |

### 2.3 模块间依赖关系

```
API网关 → 状态服务 → 调度器 → 消息总线 → 子代理
   ↓          ↓                    ↓          ↓
监控中心 ← 状态服务 ← 子代理心跳 ← 消息总线 ← 子代理
```

---

## 3. 子代理控制逻辑与状态机设计

### 3.1 状态定义与转换

```
                  ┌─────────────┐
                  │  未注册      │
                  └──────┬──────┘
                         │ 注册请求
                         ▼
                  ┌─────────────┐
                  │  已注册      │
                  └──────┬──────┘
                         │ 启动指令
                         ▼
                  ┌─────────────┐
                  │  运行中      │ ◄──────────────┐
                  └──────┬──────┘                │
                         │ 健康检查失败          │
                         ▼                       │
                  ┌─────────────┐               │
                  │  异常       │ ──────► 恢复  │
                  └──────┬──────┘               │
                         │ 恢复失败              │
                         ▼                       │
                  ┌─────────────┐               │
                  │  故障       │ ──────► 重新注册
                  └──────┬──────┘               │
                         │ 停止指令              │
                         ▼                       │
                  ┌─────────────┐               │
                  │  已停止      │               │
                  └──────┬──────┘               │
                         │ 销毁指令              │
                         ▼                       │
                  ┌─────────────┐               │
                  │  已销毁      │ ──────────────┘
                  └─────────────┘
```

### 3.2 状态转换触发条件

| 当前状态 | 事件 | 下一状态 | 触发条件 |
|---------|------|---------|---------|
| 未注册 | 注册请求 | 已注册 | 子代理发送有效注册数据，控制平面验证通过 |
| 已注册 | 启动指令 | 运行中 | 调度器分配资源，发送启动命令成功 |
| 运行中 | 健康检查失败 | 异常 | 连续3次心跳超时（间隔5秒） |
| 异常 | 恢复成功 | 运行中 | 控制平面发送恢复指令，子代理响应成功 |
| 异常 | 恢复失败 | 故障 | 连续5次恢复尝试失败 |
| 故障 | 重新注册 | 已注册 | 子代理重启后发送新注册请求 |
| 运行中 | 停止指令 | 已停止 | 管理员手动停止或资源释放 |
| 已停止 | 销毁指令 | 已销毁 | 子代理清理所有资源 |

### 3.3 状态机实现代码（Python示例）

```python
import enum
import asyncio
from dataclasses import dataclass
from typing import Dict, Optional, Callable, Awaitable

class AgentState(enum.Enum):
    UNREGISTERED = "unregistered"
    REGISTERED = "registered"
    RUNNING = "running"
    ERROR = "error"
    FAILED = "failed"
    STOPPED = "stopped"
    DESTROYED = "destroyed"

class AgentEvent(enum.Enum):
    REGISTER = "register"
    START = "start"
    HEARTBEAT_OK = "heartbeat_ok"
    HEARTBEAT_FAIL = "heartbeat_fail"
    RECOVER = "recover"
    RECOVER_FAIL = "recover_fail"
    RE_REGISTER = "re_register"
    STOP = "stop"
    DESTROY = "destroy"

@dataclass
class StateTransition:
    current_state: AgentState
    event: AgentEvent
    next_state: AgentState
    action: Optional[Callable[[], Awaitable[None]]] = None

class AgentStateMachine:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.current_state = AgentState.UNREGISTERED
        self.heartbeat_fail_count = 0
        self.recover_attempts = 0
        self.max_heartbeat_fail = 3
        self.max_recover_attempts = 5
        
        self.transitions = {
            (AgentState.UNREGISTERED, AgentEvent.REGISTER): AgentState.REGISTERED,
            (AgentState.REGISTERED, AgentEvent.START): AgentState.RUNNING,
            (AgentState.RUNNING, AgentEvent.HEARTBEAT_OK): AgentState.RUNNING,
            (AgentState.RUNNING, AgentEvent.HEARTBEAT_FAIL): AgentState.ERROR,
            (AgentState.ERROR, AgentEvent.RECOVER): AgentState.RUNNING,
            (AgentState.ERROR, AgentEvent.RECOVER_FAIL): AgentState.FAILED,
            (AgentState.FAILED, AgentEvent.RE_REGISTER): AgentState.REGISTERED,
            (AgentState.RUNNING, AgentEvent.STOP): AgentState.STOPPED,
            (AgentState.ERROR, AgentEvent.STOP): AgentState.STOPPED,
            (AgentState.STOPPED, AgentEvent.DESTROY): AgentState.DESTROYED,
        }
    
    async def handle_event(self, event: AgentEvent, context: Dict = None) -> bool:
        key = (self.current_state, event)
        if key not in self.transitions:
            print(f"[{self.agent_id}] 非法转换: {self.current_state} -> {event}")
            return False
        
        next_state = self.transitions[key]
        print(f"[{self.agent_id}] 状态转换: {self.current_state.value} -> {next_state.value}")
        
        # 执行状态转换动作
        if next_state == AgentState.RUNNING and event == AgentEvent.START:
            await self._on_start(context)
        elif next_state == AgentState.ERROR and event == AgentEvent.HEARTBEAT_FAIL:
            await self._on_heartbeat_fail()
        elif next_state == AgentState.FAILED and event == AgentEvent.RECOVER_FAIL:
            await self._on_recover_fail()
        elif next_state == AgentState.DESTROYED:
            await self._on_destroy()
        
        self.current_state = next_state
        return True
    
    async def _on_start(self, context: Dict):
        print(f"[{self.agent_id}] 启动子代理，上下文: {context}")
        # 实际实现：创建进程、分配端口、加载配置等
    
    async def _on_heartbeat_fail(self):
        self.heartbeat_fail_count += 1
        if self.heartbeat_fail_count >= self.max_heartbeat_fail:
            print(f"[{self.agent_id}] 心跳失败次数达到阈值，标记为异常")
    
    async def _on_recover_fail(self):
        self.recover_attempts += 1
        if self.recover_attempts >= self.max_recover_attempts:
            print(f"[{self.agent_id}] 恢复尝试次数达到上限，标记为故障")
    
    async def _on_destroy(self):
        print(f"[{self.agent_id}] 销毁子代理，清理资源")

# 使用示例
async def main():
    sm = AgentStateMachine("agent-001")
    await sm.handle_event(AgentEvent.REGISTER)
    await sm.handle_event(AgentEvent.START, {"task": "data_processing"})
    for _ in range(4):
        await sm.handle_event(AgentEvent.HEARTBEAT_FAIL)
    await sm.handle_event(AgentEvent.RECOVER_FAIL)
    await sm.handle_event(AgentEvent.RE_REGISTER)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 4. 跨代理通信协议与数据流规范

### 4.1 通信协议栈

| 层级 | 协议 | 用途 | 端口 |
|------|------|------|------|
| 传输层 | TCP/TLS | 可靠传输与加密 | 8443 (控制), 9443 (数据) |
| 应用层 | gRPC | 控制命令与状态同步 | - |
| 应用层 | MQTT | 心跳与轻量级消息 | - |
| 序列化 | Protocol Buffers | 高效数据交换 | - |

### 4.2 消息格式定义（Protobuf）

```protobuf
syntax = "proto3";

package openclaw.agent.v1;

// 控制命令消息
message ControlCommand {
  string command_id = 1;
  string agent_id = 2;
  CommandType type = 3;
  oneof payload {
    StartCommand start = 4;
    StopCommand stop = 5;
    UpdateCommand update = 6;
    ConfigCommand config = 7;
  }
  int64 timestamp = 8;
  int32 ttl_seconds = 9;
}

message StartCommand {
  string task_id = 1;
  map<string, string> environment = 2;
  ResourceLimit resources = 3;
}

message StopCommand {
  bool force = 1;
  int32 grace_period_seconds = 2;
}

message UpdateCommand {
  string new_version = 1;
  string download_url = 2;
  string checksum = 3;
}

message ConfigCommand {
  map<string, string> config_entries = 1;
  bool reload_required = 2;
}

enum CommandType {
  COMMAND_TYPE_UNSPECIFIED = 0;
  COMMAND_TYPE_START = 1;
  COMMAND_TYPE_STOP = 2;
  COMMAND_TYPE_UPDATE = 3;
  COMMAND_TYPE_CONFIG = 4;
}

// 心跳消息
message Heartbeat {
  string agent_id = 1;
  int64 sequence_number = 2;
  int64 timestamp = 3;
  AgentStatus status = 4;
  ResourceUsage resources = 5;
}

message AgentStatus {
  AgentState state = 1;
  string last_error = 2;
  int32 uptime_seconds = 3;
  int32 completed_tasks = 4;
  int32 failed_tasks = 5;
}

message ResourceUsage {
  double cpu_percent = 1;
  int64 memory_bytes = 2;
  int64 disk_bytes = 3;
  int32 network_rx_bytes = 4;
  int32 network_tx_bytes = 5;
}

// 响应消息
message CommandResponse {
  string command_id = 1;
  string agent_id = 2;
  ResponseCode code = 3;
  string message = 4;
  bytes result_data = 5;
}

enum ResponseCode {
  RESPONSE_CODE_OK = 0;
  RESPONSE_CODE_ERROR = 1;
  RESPONSE_CODE_TIMEOUT = 2;
  RESPONSE_CODE_REJECTED = 3;
}
```

### 4.3 数据流时序

```
控制平面                         子代理
    │                              │
    │  1. 注册请求                  │
    │  (agent_id, capabilities)     │
    │──────────────────────────────>│
    │                              │
    │  2. 注册响应                  │
    │  (token, config)              │
    │<──────────────────────────────│
    │                              │
    │  3. 启动命令                  │
    │  (task_id, environment)       │
    │──────────────────────────────>│
    │                              │
    │  4. 启动确认                  │
    │  (status: started)            │
    │<──────────────────────────────│
    │                              │
    │  5. 周期性心跳 (每5秒)        │
    │  (status, resource_usage)     │
    │<──────────────────────────────│
    │                              │
    │  6. 健康检查 (每30秒)         │
    │──────────────────────────────>│
    │                              │
    │  7. 健康检查响应              │
    │<──────────────────────────────│
    │                              │
    │  8. 停止命令                  │
    │──────────────────────────────>│
    │                              │
    │  9. 停止确认                  │
    │<──────────────────────────────│
```

### 4.4 心跳与健康检查实现

```python
import asyncio
import grpc
import time
import uuid
from concurrent import futures

class SubAgentHeartbeatService:
    def __init__(self, agent_id: str, control_plane_host: str, control_plane_port: int):
        self.agent_id = agent_id
        self.control_plane_host = control_plane_host
        self.control_plane_port = control_plane_port
        self.sequence_number = 0
        self.running = False
        
    async def send_heartbeat(self):
        """发送心跳消息"""
        while self.running:
            self.sequence_number += 1
            heartbeat = {
                "agent_id": self.agent_id,
                "sequence_number": self.sequence_number,
                "timestamp": int(time.time()),
                "status": {
                    "state": "running",
                    "last_error": "",
                    "uptime_seconds": self._get_uptime(),
                    "completed_tasks": self._get_completed_tasks(),
                    "failed_tasks": self._get_failed_tasks()
                },
                "resources": {
                    "cpu_percent": self._get_cpu_usage(),
                    "memory_bytes": self._get_memory_usage(),
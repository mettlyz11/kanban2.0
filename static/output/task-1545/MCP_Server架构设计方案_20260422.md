# MCP Server 架构设计方案 v1.0

## 一、背景与目标

### 1.1 现状分析
当前AI助手采用独立skill调用模式，存在以下瓶颈：
- **调用链路不透明**：技能调用无统一追踪，难以定位性能问题
- **Memory架构受限**：文件式Memory.md无法支持大规模语义检索
- **成本不可控**：无精细化token成本核算机制
- **扩展性差**：技能间隔离不足，难以水平扩展

### 1.2 设计目标
- **统一协议**：所有技能遵循MCP (Model Control Protocol) 标准
- **可观测性**：全链路追踪、延迟监控、成本核算
- **高性能**：向量检索响应 < 100ms，技能调用平均延迟 < 500ms
- **可扩展**：支持100+ MCP Server节点水平扩展

## 二、整体架构设计

### 2.1 系统架构图
```
┌─────────────────────────────────────────────────────────────┐
│                    AI Agent Core                            │
├─────────────────────────────────────────────────────────────┤
│  MCP Client SDK  │  Memory Engine  │  Observability Agent   │
└─────────┬─────────────────┬──────────────────┬──────────────┘
          │                 │                  │
          ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    MCP Gateway (负载均衡)                    │
│  协议解析 │ 路由分发 │ 流量控制 │ 熔断降级                     │
└─────────┬─────────────────┬──────────────────┬──────────────┘
          │                 │                  │
          ▼                 ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  MCP Server  │  │  MCP Server  │  │  MCP Server  │
│  (Memory)    │  │  (Skills)    │  │  (Tools)     │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                  │
       ▼                 ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Vector DB    │  │  Skill Pool  │  │  Tool Proxy  │
│ (ChromaDB)   │  │  (Redis)     │  │  (Registry)  │
└──────────────┘  └──────────────┘  └──────────────┘
```

### 2.2 核心组件说明

| 组件 | 职责 | 技术选型 |
|------|------|----------|
| MCP Gateway | 协议解析、路由分发、流量控制 | FastAPI + Nginx |
| MCP Server | 技能执行、工具调用 | Python + gRPC |
| Memory Engine | 向量检索、知识图谱 | ChromaDB + NetworkX |
| Observability | 链路追踪、指标采集 | OpenTelemetry + Prometheus |
| Cost Engine | Token成本核算、预算控制 | 自定义计量模块 |

## 三、MCP 协议规范

### 3.1 核心接口定义

```python
# MCP Server 标准接口
class MCPServer(ABC):
    @abstractmethod
    async def call(self, request: MCPRequest) -> MCPResponse:
        pass
    
    @abstractmethod
    async def health_check(self) -> HealthStatus:
        pass
    
    @abstractmethod
    async def get_capabilities(self) -> List[Capability]:
        pass
```

### 3.2 请求/响应格式

```json
{
  "request_id": "uuid",
  "session_id": "uuid",
  "skill": "memory_search",
  "action": "query",
  "parameters": {
    "query": "MCP架构设计",
    "top_k": 5,
    "threshold": 0.7
  },
  "context": {
    "user_id": "mettlyz",
    "trace_id": "trace-uuid",
    "priority": "normal"
  },
  "timestamp": "2026-04-22T20:00:00Z"
}
```

## 四、可观测性体系设计

### 4.1 三大核心指标

#### 1. 调用链路追踪 (Tracing)
- Trace ID 全链路透传
- 每个技能调用生成 Span
- 记录：入参、出参、耗时、错误堆栈

#### 2. 性能指标 (Metrics)
- **延迟指标**：p50, p95, p99 延迟
- **吞吐指标**：QPS, 并发数
- **错误指标**：错误率, 超时率

#### 3. 成本核算 (Cost)
- Token 消耗量级统计
- 按技能/用户维度计费
- 预算阈值告警

### 4.2 数据存储方案
- **实时指标**：Prometheus (保留7天)
- **链路数据**：Jaeger (保留3天)
- **历史数据**：ClickHouse (保留90天)

## 五、Memory 架构升级

### 5.1 混合存储架构
```
┌─────────────────────────────────────────┐
│              Memory Router              │
└─────────────┬─────────────┬─────────────┘
              │             │
              ▼             ▼
┌───────────────┐ ┌───────────────┐
│  向量检索层   │ │  知识图谱层    │
│  (ChromaDB)   │ │  (NetworkX)    │
└───────┬───────┘ └───────┬───────┘
        │                 │
        ▼                 ▼
┌───────────────┐ ┌───────────────┐
│  语义索引     │ │  实体关系     │
│  100K+ 向量   │ │  50K+ 三元组  │
└───────────────┘ └───────────────┘
```

### 5.2 检索流程
1. **语义召回**：向量检索 Top-K 候选
2. **图谱增强**：知识图谱实体关联扩展
3. **重排序**：Cross-Encoder 精细排序
4. **上下文组装**：格式化返回给 LLM

## 六、部署方案

### 6.1 集群拓扑
```
生产环境 (3节点集群):
- MCP Gateway: 2 实例 (主备)
- Memory Server: 3 实例 (分片)
- Skill Server: 5 实例 (按技能分组)
- Observability: 1 实例 (集中采集)
```

### 6.2 资源配置
| 服务 | CPU | 内存 | 存储 |
|------|-----|------|------|
| MCP Gateway | 2核 | 4GB | 20GB |
| Memory Server | 4核 | 16GB | 100GB SSD |
| Skill Server | 2核 | 8GB | 50GB |
| Observability | 4核 | 16GB | 200GB |

## 七、迁移计划

### 阶段一：基础架构搭建 (Week 1)
- [ ] MCP Gateway 开发部署
- [ ] 可观测性平台搭建
- [ ] Memory 向量库初始化

### 阶段二：核心技能迁移 (Week 2-3)
- [ ] Memory 检索 MCP 化
- [ ] Web Search MCP 化
- [ ] File System MCP 化

### 阶段三：全量切换 (Week 4)
- [ ] 灰度流量切换 (10% → 50% → 100%)
- [ ] 性能基准测试
- [ ] 旧系统下线

---
**文档版本**: v1.0  
**创建日期**: 2026-04-22  
**作者**: Dudu AI Assistant

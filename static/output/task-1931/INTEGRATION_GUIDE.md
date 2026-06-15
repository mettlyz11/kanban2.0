# OpenClaw ACP v2026 集成实施指南

**版本**: 1.0  
**最后更新**: 2026-04-25  
**适用范围**: 系统架构师、DevOps工程师、平台开发人员

---

## 目录

1. [前置准备](#1-前置准备)
2. [环境安装配置](#2-环境安装配置)
3. [沙箱后端配置](#3-沙箱后端配置)
4. [安全策略配置](#4-安全策略配置)
5. [Agent Profile配置](#5-agent-profile配置)
6. [可观测性部署](#6-可观测性部署)
7. [ACP协议适配](#7-acp协议适配)
8. [迁移现有任务](#8-迁移现有任务)
9. [测试验证方法](#9-测试验证方法)
10. [上线与运维](#10-上线与运维)
11. [故障排查指南](#11-故障排查指南)
12. [性能优化建议](#12-性能优化建议)

---

## 1. 前置准备

### 1.1 系统要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 8核 | 16核+ |
| 内存 | 16GB | 32GB+ |
| 磁盘 | 100GB SSD | 500GB NVMe SSD |
| 操作系统 | Ubuntu 22.04 / macOS 13+ | Ubuntu 22.04 LTS |
| Docker | 24.0+ | 25.0+ |
| Python | 3.10+ | 3.11+ |

### 1.2 依赖软件清单

```bash
# 核心依赖
pip install openai-agents[docker]>=1.0.0

# 可选依赖
pip install redis>=5.0          # 消息队列
pip install prometheus-client   # 指标采集
pip install opentelemetry-api   # 分布式追踪
pip install python-dotenv       # 环境变量管理
```

### 1.3 网络要求

| 服务 | 端口 | 用途 | 外部访问 |
|------|------|------|---------|
| OpenAI API | 443 | 模型调用 | 需要 |
| Docker Registry | 443 | 镜像拉取 | 需要 |
| PyPI | 443 | Python包安装 | 需要 |
| Prometheus | 9090 | 指标查询 | 内网 |
| Grafana | 3000 | 监控面板 | 内网 |
| Redis | 6379 | 消息队列 | 内网 |

### 1.4 环境变量

创建 `.env` 文件：

```env
# OpenAI API
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
OPENAI_API_BASE=https://api.openai.com/v1

# 沙箱配置
SANDBOX_BACKEND=docker
SANDBOX_DEFAULT_IMAGE=openclaw/sandbox-python:v2026

# 存储路径
WORKSPACE_ROOT=/var/openclaw/workspace
CHECKPOINT_DIR=/var/openclaw/checkpoints
LOG_DIR=/var/log/openclaw

# 消息队列
REDIS_URL=redis://localhost:6379/0

# 可观测性
PROMETHEUS_PORT=9090
ENABLE_TRACING=true
ENABLE_METRICS=true
```

---

## 2. 环境安装配置

### 2.1 目录结构初始化

```bash
# 创建核心目录结构
sudo mkdir -p /var/openclaw/{workspace,checkpoints,skills,artifacts}
sudo mkdir -p /var/log/openclaw
sudo mkdir -p /etc/openclaw

# 设置权限
sudo chown -R openclaw:openclaw /var/openclaw
sudo chmod 700 /var/openclaw

# 验证
ls -la /var/openclaw/
```

### 2.2 Python虚拟环境配置

```bash
# 创建虚拟环境
python3 -m venv /opt/openclaw/venv
source /opt/openclaw/venv/bin/activate

# 安装核心包
pip install --upgrade pip
pip install 'openai-agents[docker]>=1.0.0'

# 验证安装
python -c "from agents import SandboxAgent; print('SDK OK:', SandboxAgent)"
```

### 2.3 Docker环境配置

```bash
# 验证Docker运行
docker info

# 配置Docker守护进程（可选：优化性能）
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 65536,
      "Soft": 65536
    }
  }
}
EOF

sudo systemctl restart docker

# 拉取基础沙箱镜像
docker pull openclaw/sandbox-python:v2026
docker pull openclaw/sandbox-minimal:v2026
docker pull openclaw/sandbox-data:v2026
```

### 2.4 配置文件部署

```bash
# 部署Harness配置
cp harness_config_example.json /etc/openclaw/harness.json

# 验证配置格式
python -c "import json; json.load(open('/etc/openclaw/harness.json')); print('Config OK')"
```

---

## 3. 沙箱后端配置

### 3.1 Docker沙箱配置

**优点**: 隔离性好、生态成熟、资源控制精确  
**适用场景**: 生产环境、多租户场景

```python
# sandbox_config.py
from agents import DockerSandboxClient

docker_client = DockerSandboxClient(
    # 基础镜像配置
    default_image="openclaw/sandbox-python:v2026",
    
    # 网络配置
    network_mode="none",  # 默认无网络
    allowed_networks=["openclaw-sandbox"],
    
    # 资源限制（每个沙箱）
    default_cpu_limit="2.0",
    default_memory_limit="4g",
    default_pids_limit=100,
    
    # 安全配置
    enable_seccomp=True,
    enable_apparmor=True,
    read_only_rootfs=False,
    
    # 卷挂载
    additional_volumes={
        "/var/openclaw/shared": {
            "bind": "/shared",
            "mode": "ro"
        }
    }
)
```

### 3.2 Unix Local沙箱配置

**优点**: 性能好、无额外依赖、启动快  
**适用场景**: 开发环境、可信任务

```python
from agents import UnixLocalSandboxClient

local_client = UnixLocalSandboxClient(
    # 用户命名空间隔离
    use_user_namespace=True,
    
    # 工作目录
    base_workspace="/tmp/openclaw-sandboxes",
    
    # 资源限制
    max_processes=100,
    max_files=1000,
    
    # 清理配置
    auto_cleanup=True,
    cleanup_timeout=300
)
```

### 3.3 多云沙箱配置（高级）

```python
from agents import MultiSandboxClient

# 配置多个后端，自动故障转移
multi_client = MultiSandboxClient(
    backends=[
        ("docker", docker_client, 10),    # 优先级10
        ("unix_local", local_client, 5),  # 优先级5
    ],
    # 故障转移策略
    failover_enabled=True,
    max_failover_attempts=3
)
```

### 3.4 沙箱健康检查

```bash
# 验证沙箱基本功能
python sandbox_integration_example.py

# 测试沙箱隔离性
docker run --rm --network none openclaw/sandbox-python:v2026 \
  python -c "import requests; print('Network test:', requests.get('https://google.com'))"
# 预期: 网络连接失败（隔离正常）
```

---

## 4. 安全策略配置

### 4.1 能力控制矩阵

| 能力 | 描述 | 风险等级 | 默认启用 |
|------|------|---------|---------|
| Shell | 命令行执行 | 高 | ✓ |
| Filesystem | 文件读写 | 中 | ✓ |
| Memory | 记忆读写 | 低 | ✓ |
| Network | 网络访问 | 高 | ✗ |
| Compaction | 上下文压缩 | 低 | ✗ |
| Skills | 技能加载 | 中 | ✗ |

### 4.2 命令白名单配置

在 `harness.json` 中配置：

```json
{
  "security_policy": {
    "allowed_commands": [
      "ls", "cat", "echo", "pwd", "whoami",
      "python", "python3", "pip",
      "git", "grep", "find", "head", "tail",
      "pytest", "flake8", "black", "mypy"
    ],
    "blocked_commands": [
      "rm -rf /",
      "mkfs",
      "dd if=/dev",
      "nc -l",
      "ssh",
      "scp",
      "curl -X POST",
      "wget --post-data"
    ]
  }
}
```

### 4.3 数据泄露防护（DLP）

```python
# dlp_filter.py
class DataLeakageFilter:
    """检测并阻止敏感数据外泄"""
    
    SENSITIVE_PATTERNS = {
        'api_key': r'sk-[a-zA-Z0-9]{32,}',
        'password': r'password\s*=\s*["\'][^"\']+["\']',
        'private_key': r'-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----',
        'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
        'phone': r'\b1[3-9]\d{9}\b',
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    }
    
    def scan_output(self, content: str) -> dict:
        """扫描输出内容中的敏感数据"""
        findings = {}
        for pattern_name, pattern in self.SENSITIVE_PATTERNS.items():
            import re
            matches = re.findall(pattern, content)
            if matches:
                findings[pattern_name] = len(matches)
        return findings
    
    def filter_output(self, content: str) -> tuple[str, dict]:
        """过滤并替换敏感数据"""
        findings = self.scan_output(content)
        
        if not findings:
            return content, {}
        
        # 执行替换...
        filtered = content
        for pattern_name, pattern in self.SENSITIVE_PATTERNS.items():
            import re
            filtered = re.sub(pattern, '[REDACTED]', filtered)
        
        return filtered, findings
```

### 4.4 安全审计日志

```json
{
  "observability": {
    "logging": {
      "audit_log": {
        "enabled": true,
        "path": "/var/log/openclaw/audit.log",
        "immutable": true,
        "format": "json",
        "events": [
          "sandbox_create",
          "sandbox_destroy",
          "shell_command",
          "file_modification",
          "network_access",
          "checkpoint_create",
          "checkpoint_restore",
          "escalation",
          "guardrail_trigger"
        ]
      }
    }
  }
}
```

---

## 5. Agent Profile配置

### 5.1 基础Agent配置模板

```python
# agent_profiles.py
from agents import SandboxAgent

def create_research_agent() -> SandboxAgent:
    """研究型Agent：用于科研和复杂分析任务"""
    return SandboxAgent(
        name="OpenClaw Research Agent",
        model="gpt-5.4",
        temperature=0.7,
        
        instructions="""
        You are a senior research agent working in a secure sandbox.
        
        Your capabilities:
        - Read and analyze scientific papers
        - Run computational experiments
        - Process and visualize data
        - Write research reports
        
        Best practices:
        1. Always validate data before analysis
        2. Document your methodology clearly
        3. Create intermediate checkpoints
        4. Report uncertainties and limitations
        5. Cite sources appropriately
        """,
        
        capabilities=[
            Shell(timeout=600),
            Filesystem(allow_patch=True),
            Memory(compaction_enabled=True),
            Network(allowlist=["arxiv.org", "github.com", "pypi.org"])
        ],
        
        # 工具配置
        tools=[
            web_search_tool,
            paper_qa_tool,
            data_visualization_tool
        ],
        
        # 交接配置
        handoff_description="Research specialist for scientific analysis",
        can_handoff_to=["code_agent", "data_agent"]
    )

def create_code_agent() -> SandboxAgent:
    """代码Agent：用于代码审查和开发任务"""
    return SandboxAgent(
        name="OpenClaw Code Agent",
        model="gpt-5.4",
        temperature=0.2,
        
        instructions="""
        You are a senior software engineer in a secure sandbox environment.
        
        Security rules:
        - Never hardcode secrets or credentials
        - Validate all inputs before use
        - Write tests for all changes
        - Follow secure coding guidelines
        """,
        
        capabilities=[
            Shell(timeout=300, allowlist=["python", "pip", "git", "pytest"]),
            Filesystem(),
            Memory()
        ]
    )
```

### 5.2 特殊场景Agent配置

#### 长周期任务专用Agent

```python
def create_long_running_agent() -> SandboxAgent:
    return SandboxAgent(
        name="OpenClaw Long-Running Agent",
        model="gpt-5.4",
        
        # 长上下文配置
        max_tokens=128000,
        
        # 记忆配置
        capabilities=[
            Shell(timeout=3600),
            Filesystem(),
            Memory(
                compaction_enabled=True,
                compaction_threshold=80000
            )
        ],
        
        # 检查点配置
        checkpoint_enabled=True,
        checkpoint_interval_steps=10,
        
        # Guardrails
        max_steps=1000,
        max_runtime_hours=72
    )
```

#### 编排器Agent

```python
def create_orchestrator_agent() -> SandboxAgent:
    return SandboxAgent(
        name="OpenClaw Orchestrator",
        model="gpt-5.4",
        
        # 子Agent配置
        subagent_allowed=True,
        max_subagents=10,
        subagent_profiles=["research_agent", "code_agent", "data_agent"],
        
        # 编排模式
        orchestration_pattern="hierarchical",
        fan_out_parallelism=5,
        
        capabilities=[
            Filesystem(),
            Memory(compaction_enabled=True)
        ]
    )
```

---

## 6. 可观测性部署

### 6.1 Prometheus指标配置

```python
# metrics.py
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# 定义指标
SANDBOX_CREATED = Counter('sandbox_created_total', 'Total sandboxes created')
SANDBOX_FAILED = Counter('sandbox_failed_total', 'Total sandbox failures')
TASK_DURATION = Histogram('task_duration_seconds', 'Task execution duration')
ACTIVE_SANDBOXES = Gauge('active_sandboxes', 'Currently active sandboxes')
TOKENS_USED = Counter('tokens_used_total', 'Total tokens used')
STEP_COUNT = Histogram('task_steps', 'Steps per task')

def start_metrics_server(port=9090):
    """启动指标服务"""
    start_http_server(port)
    print(f"Metrics server running on port {port}")
```

### 6.2 Grafana仪表板

导入 `dashboard.json` 到Grafana，包含以下面板：

1. **概览面板**
   - 活跃沙箱数量
   - 任务成功率
   - Token消耗速率
   - 平均任务时长

2. **沙箱资源面板**
   - CPU使用率
   - 内存使用率
   - 磁盘IO
   - 网络流量

3. **安全审计面板**
   - 安全事件计数
   - Guardrail触发统计
   - 命令执行分布
   - 文件修改统计

4. **长周期任务面板**
   - Checkpoint创建频率
   - 恢复成功率
   - Memory Compaction统计
   - 子Agent执行状态

### 6.3 告警规则

```yaml
# prometheus/alerts.yml
groups:
  - name: sandbox_alerts
    rules:
      - alert: HighSandboxFailureRate
        expr: rate(sandbox_failed_total[5m]) / rate(sandbox_created_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Sandbox failure rate above 10%"
      
      - alert: SecurityAnomalyDetected
        expr: increase(security_events_total{level="critical"}[1m]) > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Critical security event detected"
      
      - alert: HighTokenConsumption
        expr: rate(tokens_used_total[1h]) > 1000000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High token consumption rate"
```

---

## 7. ACP协议适配

### 7.1 消息格式扩展

```python
# acp_adapter.py
import json
import uuid
from datetime import datetime
from typing import Dict, Any

class ACPv2SandboxMessage:
    """扩展ACP消息格式，支持沙箱相关字段"""
    
    @staticmethod
    def wrap_task_dispatch(
        original_message: Dict[str, Any],
        sandbox_profile: str,
        capabilities: list,
        manifest_files: Dict[str, bytes] = None
    ) -> Dict[str, Any]:
        """包装任务派发消息，添加沙箱配置"""
        return {
            **original_message,
            "message_id": f"msg-{uuid.uuid4()}",
            "type": "task_dispatch",
            "timestamp": datetime.utcnow().isoformat(),
            "sandbox_config": {
                "profile": sandbox_profile,
                "capabilities": capabilities,
                "manifest": manifest_files or {}
            },
            "lrt_config": {
                "checkpoint_enabled": True,
                "max_duration_hours": 24,
                "enable_compaction": True
            }
        }
    
    @staticmethod
    def wrap_sandbox_event(
        task_id: str,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建沙箱事件消息"""
        return {
            "message_id": f"evt-{uuid.uuid4()}",
            "type": "sandbox_event",
            "task_id": task_id,
            "event_type": event_type,
            "event_data": event_data,
            "timestamp": datetime.utcnow().isoformat()
        }
```

### 7.2 消息处理器实现

```python
class SandboxMessageHandler:
    """处理沙箱相关的ACP消息"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
    
    async def handle_task_dispatch(self, message: Dict[str, Any]):
        """处理任务派发"""
        # 提取沙箱配置
        sandbox_config = message.get('sandbox_config', {})
        lrt_config = message.get('lrt_config', {})
        
        # 创建任务控制器
        task = LongRunningTaskController(
            task_id=message['payload']['task_id'],
            description=message['payload']['instructions'],
            checkpoint_manager=CheckpointManager()
        )
        
        # 启动任务
        result = await task.run(
            max_duration_hours=lrt_config.get('max_duration_hours', 24)
        )
        
        # 返回结果
        return {
            "type": "result_submit",
            "task_id": message['payload']['task_id'],
            "result": result
        }
    
    async def handle_checkpoint_request(self, message: Dict[str, Any]):
        """处理检查点查询请求"""
        task_id = message['payload']['task_id']
        checkpoint = await self.orchestrator.checkpoint_manager.get_latest_checkpoint(task_id)
        
        return {
            "type": "checkpoint_response",
            "task_id": task_id,
            "checkpoint": checkpoint.to_dict() if checkpoint else None
        }
```

### 7.3 ACP协议迁移清单

- [x] 扩展消息类型，添加 `sandbox_event`
- [x] 在 `task_dispatch` 中添加沙箱配置字段
- [x] 在 `status_report` 中添加沙箱资源指标
- [x] 添加 `checkpoint_request` / `checkpoint_response` 消息
- [x] 添加子Agent编排相关消息类型
- [x] 兼容旧版消息格式（向后兼容）

---

## 8. 迁移现有任务

### 8.1 迁移策略

| 迁移阶段 | 任务类型 | 流量比例 | 预计时间 |
|---------|---------|---------|---------|
| Phase 1 | 测试/实验任务 | 0%（影子模式） | 1周 |
| Phase 2 | 低优先级任务 | 10% | 1周 |
| Phase 3 | 普通任务 | 50% | 2周 |
| Phase 4 | 所有任务 | 100% | 1周 |

### 8.2 影子模式验证

```python
# shadow_mode.py
class ShadowModeOrchestrator:
    """同时在新旧架构上运行任务，比较结果"""
    
    def __init__(self, old_orchestrator, new_orchestrator):
        self.old = old_orchestrator
        self.new = new_orchestrator
        self.comparison_results = []
    
    async def run_shadow_task(self, task_spec):
        """在两个架构上并行运行，比较结果"""
        import asyncio
        
        # 同时启动两个任务
        result_old, result_new = await asyncio.gather(
            self.old.run_task(task_spec),
            self.new.run_task(task_spec),
            return_exceptions=True
        )
        
        # 比较结果
        comparison = self._compare_results(result_old, result_new)
        self.comparison_results.append(comparison)
        
        # 始终返回旧架构结果（安全）
        return result_old
    
    def _compare_results(self, old, new):
        """比较两个架构的结果差异"""
        return {
            "task_id": old.get('task_id'),
            "both_success": old.get('success') and new.get('success'),
            "old_success": old.get('success'),
            "new_success": new.get('success'),
            "time_diff": new.get('duration', 0) - old.get('duration', 0),
            "token_diff": new.get('tokens_used', 0) - old.get('tokens_used', 0)
        }
```

### 8.3 回滚计划

**触发回滚条件**：
- 新架构任务成功率 < 95%
- 严重安全事件发生
- 性能下降 > 20%
- 用户投诉 > 5起/天

**回滚步骤**：
1. 将流量切回旧架构（配置开关）
2. 不影响正在运行的任务（双写模式）
3. 排查问题根因
4. 修复后先在测试环境验证
5. 小流量重试

---

## 9. 测试验证方法

### 9.1 功能测试套件

```bash
# 测试沙箱基本功能
pytest tests/sandbox/test_basic.py -v

# 测试内容:
# ✓ 沙箱创建与销毁
# ✓ Shell命令执行
# ✓ 文件读写操作
# ✓ Manifest文件注入
# ✓ 资源限制生效
```

### 9.2 安全渗透测试

```python
# tests/security/test_penetration.py
import pytest

class TestSandboxSecurity:
    """沙箱安全渗透测试"""
    
    def test_network_isolation(self, sandbox):
        """测试网络隔离 - 应该无法访问外部网络"""
        result = sandbox.run_shell("curl -m 5 https://google.com")
        assert result.exit_code != 0, "Network should be blocked"
    
    def test_escape_attempt(self, sandbox):
        """测试沙箱逃逸尝试"""
        escape_commands = [
            "chroot /host",
            "nsenter --target 1 --mount",
            "docker run -v /:/host alpine",
            "mount -o remount,rw /"
        ]
        
        for cmd in escape_commands:
            result = sandbox.run_shell(cmd)
            assert result.exit_code != 0, f"Escape should fail: {cmd}"
    
    def test_sensitive_files(self, sandbox):
        """测试敏感文件访问"""
        sensitive_paths = [
            "/etc/shadow",
            "/etc/passwd",
            "/proc/self/environ",
            "/.dockerenv"
        ]
        
        for path in sensitive_paths:
            result = sandbox.run_shell(f"cat {path}")
            # 根据安全策略，这些可能被允许或阻止
            # 根据实际策略调整断言
```

### 9.3 性能基准测试

```python
# benchmarks/sandbox_benchmark.py
import time
import statistics

async def benchmark_sandbox_startup():
    """测量沙箱启动时间"""
    times = []
    for _ in range(100):
        start = time.time()
        sandbox = await create_sandbox()
        await sandbox.destroy()
        times.append(time.time() - start)
    
    return {
        "mean": statistics.mean(times),
        "p50": statistics.median(times),
        "p95": sorted(times)[int(len(times)*0.95)],
        "p99": sorted(times)[int(len(times)*0.99)]
    }
```

### 9.4 长周期耐久性测试

```bash
# 运行72小时耐久性测试
python long_running_task_example.py --duration 72

# 验证指标:
# ✓ Checkpoint创建频率和成功率
# ✓ Memory Compaction效果
# ✓ 无内存泄漏
# ✓ 无资源耗尽
# ✓ 故障恢复能力
```

---

## 10. 上线与运维

### 10.1 上线检查清单

**上线前检查**：
- [ ] 所有单元测试通过
- [ ] 安全渗透测试通过
- [ ] 性能基准测试达标
- [ ] 可观测性仪表板正常
- [ ] 告警规则配置完成
- [ ] 回滚方案验证过
- [ ] 团队培训完成
- [ ] 文档更新完成

**上线后检查**：
- [ ] 错误率 < 1%
- [ ] 任务成功率 > 99%
- [ ] 沙箱平均启动时间 < 5s
- [ ] 无安全告警
- [ ] 资源使用率正常
- [ ] 用户反馈收集通道畅通

### 10.2 日常运维操作

```bash
# 查看当前运行的沙箱
docker ps --filter name=sandbox

# 查看沙箱日志
docker logs <sandbox_id>

# 手动清理僵尸沙箱
docker ps -q --filter name=sandbox | xargs -r docker rm -f

# 清理旧的checkpoint
find /var/openclaw/checkpoints -type f -mtime +7 -delete

# 日志轮转
logrotate /etc/logrotate.d/openclaw

# 备份配置文件
tar -czf /var/backup/openclaw-config-$(date +%Y%m%d).tar.gz /etc/openclaw/
```

### 10.3 容量规划

| 并发任务数 | CPU需求 | 内存需求 | 磁盘需求 |
|-----------|---------|---------|---------|
| 10 | 4核 | 8GB | 50GB |
| 50 | 16核 | 32GB | 200GB |
| 100 | 32核 | 64GB | 500GB |
| 500 | 128核 | 256GB | 2TB |

扩容触发条件：
- CPU使用率 > 70%（持续5分钟）
- 内存使用率 > 80%（持续5分钟）
- 沙箱启动排队时间 > 30s

---

## 11. 故障排查指南

### 11.1 常见问题排查

**问题1: 沙箱启动失败**

```bash
# 检查Docker是否运行
systemctl status docker

# 检查镜像是否存在
docker images | grep openclaw

# 检查磁盘空间
df -h

# 检查Docker日志
journalctl -u docker -f
```

**问题2: Shell命令超时**

可能原因：
- 命令本身执行时间长
- 沙箱资源不足
- 死锁或无限循环

排查：
```python
# 增加超时时间
Shell(timeout=1200)  # 20分钟

# 检查资源限制
docker stats <sandbox_id>
```

**问题3: Checkpoint恢复失败**

可能原因：
- Checkpoint文件损坏
- 版本不兼容
- 沙箱环境变更

排查：
```bash
# 检查checkpoint文件完整性
ls -lh /var/openclaw/checkpoints/
cat /var/openclaw/checkpoints/<checkpoint_id>.json | python -m json.tool

# 尝试从更早的checkpoint恢复
```

### 11.2 调试工具

```python
# sandbox_debug.py
class SandboxDebugger:
    """沙箱调试工具"""
    
    async def capture_sandbox_state(self, sandbox_id: str):
        """捕获沙箱状态用于调试"""
        return {
            "sandbox_id": sandbox_id,
            "process_list": await self._run_in_sandbox(sandbox_id, "ps aux"),
            "file_list": await self._run_in_sandbox(sandbox_id, "ls -laR /workspace"),
            "resource_usage": await self._get_docker_stats(sandbox_id),
            "logs": await self._get_sandbox_logs(sandbox_id)
        }
    
    async def interactive_shell(self, sandbox_id: str):
        """获取沙箱交互式Shell（仅调试用）"""
        import subprocess
        subprocess.run(["docker", "exec", "-it", sandbox_id, "/bin/bash"])
```

---

## 12. 性能优化建议

### 12.1 沙箱启动优化

**预热沙箱池**：
```python
class SandboxPool:
    """沙箱池 - 预热实例减少启动时间"""
    
    def __init__(self, size: int = 10):
        self.pool = asyncio.Queue(maxsize=size)
        self._start_preload_task()
    
    async def _preload_worker(self):
        while True:
            if self.pool.qsize() < self.pool.maxsize:
                sandbox = await create_sandbox()
                await self.pool.put(sandbox)
            await asyncio.sleep(1)
    
    async def get_sandbox(self):
        return await self.pool.get()
```

**预期优化效果**：沙箱启动时间从 ~3s 降至 <100ms

### 12.2 存储优化

**使用tmpfs**：
```python
# 将workspace挂载到内存
DockerSandboxClient(
    additional_volumes={
        "tmpfs": {
            "target": "/workspace",
            "type": "tmpfs",
            "tmpfs-size": "1G"
        }
    }
)
```

**预期优化效果**：文件IO性能提升5-10倍

### 12.3 网络优化

**本地PyPI镜像**：
```json
{
  "sandbox_profiles": {
    "python": {
      "pre_installed_packages": ["pandas", "numpy"],
      "pip_index_url": "https://pypi-mirror.internal/simple"
    }
  }
}
```

**预期优化效果**：包安装时间减少80%

---

## 附录

### A. 参考配置文件

完整的生产环境配置示例见：
- `harness_config_example.json` - Harness完整配置
- `sandbox_integration_example.py` - 沙箱集成代码
- `long_running_task_example.py` - 长周期任务代码

### B. 联系支持

- 架构问题: architecture@openclaw.ai
- 安全问题: security@openclaw.ai
- 运维问题: ops@openclaw.ai

---

**文档历史**：
- 2026-04-25: v1.0 初始版本

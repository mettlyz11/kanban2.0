# SLURM 作业调度模块使用指南

## 📋 概述

`slurm_scheduler.py` 为 T109 项目提供完整的 SLURM 作业调度功能，支持 Gaussian、ORCA、PSI4 等计算化学软件。

**模块位置**: `~/.openclaw/workspace/kanban-react/backend/slurm_scheduler.py`

**创建时间**: 2026-03-11

---

## 🚀 快速开始

### 1. 基本使用

```python
from slurm_scheduler import SLURMScheduler, SoftwareType

# 创建调度器
scheduler = SLURMScheduler(default_partition="compute")

# 提交作业
result = scheduler.submit_job(
    script_path="my_job.sh",
    job_name="test_job",
    nodes=1,
    cpus_per_task=8,
    memory="16G",
    time_limit="24:00:00"
)

print(f"作业 ID: {result['job_id']}")
```

### 2. 检查作业状态

```python
from slurm_scheduler import check_job_status

status = check_job_status("12345")
print(f"作业状态：{status['status']}")
```

### 3. 取消作业

```python
from slurm_scheduler import cancel_job

result = cancel_job("12345", reason="测试完成")
print(result['message'])
```

---

## 📝 功能详情

### 1. 作业提交 (`submit_job`)

#### 基本参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `script_path` | str | ✅ | SLURM 脚本路径 |
| `job_name` | str | ❌ | 作业名称 |
| `partition` | str | ❌ | 分区 (默认：compute) |
| `nodes` | int | ❌ | 节点数 (默认：1) |
| `ntasks_per_node` | int | ❌ | 每节点任务数 (默认：1) |
| `cpus_per_task` | int | ❌ | 每任务 CPU 数 (默认：1) |
| `memory` | str | ❌ | 内存 (如 "4G", "8192M") |
| `time_limit` | str | ❌ | 时间限制 ("HH:MM:SS") |
| `output_file` | str | ❌ | 标准输出文件 |
| `error_file` | str | ❌ | 错误输出文件 |
| `working_dir` | str | ❌ | 工作目录 |
| `dependencies` | List[str] | ❌ | 依赖作业 ID 列表 |
| `qos` | str | ❌ | 服务质量 |
| `account` | str | ❌ | 账户 |
| `mail_user` | str | ❌ | 邮件通知用户 |
| `mail_type` | List[str] | ❌ | 邮件类型 (如 ["BEGIN", "END", "FAIL"]) |
| `dry_run` | bool | ❌ | 仅生成命令不提交 |

#### 返回值

```python
{
    'success': True,
    'job_id': '12345',
    'message': '作业 12345 提交成功',
    'script_path': '/path/to/script.sh',
    'submit_time': '2026-03-11T23:00:00'
}
```

#### 示例

```python
# 提交高性能计算作业
result = scheduler.submit_job(
    script_path="gaussian_job.sh",
    job_name="h2o_optimization",
    partition="compute",
    nodes=1,
    cpus_per_task=16,
    memory="32G",
    time_limit="48:00:00",
    output_file="h2o.out",
    error_file="h2o.err",
    mail_user="user@example.com",
    mail_type=["BEGIN", "END", "FAIL"]
)
```

---

### 2. 作业状态检查 (`check_job_status`)

#### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `job_id` | str | 作业 ID |

#### 返回值

```python
{
    'success': True,
    'job_id': '12345',
    'status': JobStatus.RUNNING,  # 或 COMPLETED/FAILED/PENDING等
    'details': {
        'job_name': 'test_job',
        'partition': 'compute',
        'time': '1-12:30:45',
        'node': 'node001',
        'cpus': '16/16'
    },
    'message': '作业状态：RUNNING'
}
```

#### 作业状态枚举

```python
class JobStatus(Enum):
    PENDING = "PENDING"      # 等待中
    RUNNING = "RUNNING"      # 运行中
    COMPLETED = "COMPLETED"  # 已完成
    FAILED = "FAILED"        # 失败
    CANCELLED = "CANCELLED"  # 已取消
    TIMEOUT = "TIMEOUT"      # 超时
    NODE_FAIL = "NODE_FAIL"  # 节点故障
    UNKNOWN = "UNKNOWN"      # 未知
```

#### 示例

```python
# 检查单个作业
status = scheduler.check_job_status("12345")
print(f"状态：{status['status'].value}")

# 批量检查
results = scheduler.check_multiple_jobs(["12345", "12346", "12347"])
for job_id, info in results.items():
    print(f"{job_id}: {info['status'].value}")
```

---

### 3. 作业取消 (`cancel_job`)

#### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `job_id` | str | 作业 ID |
| `reason` | str | 取消原因 (可选) |

#### 示例

```python
# 取消单个作业
result = scheduler.cancel_job("12345", reason="计算已完成")

# 批量取消
results = scheduler.cancel_multiple_jobs(["12345", "12346"])

# 按名称取消
result = scheduler.cancel_jobs_by_name("test_job", user="username")
```

---

### 4. SLURM 脚本模板生成

#### 支持的软件类型

```python
class SoftwareType(Enum):
    GAUSSIAN = "gaussian"
    ORCA = "orca"
    PSI4 = "psi4"
    CUSTOM = "custom"
```

#### Gaussian 脚本模板

```python
from slurm_scheduler import generate_gaussian_script

script = generate_gaussian_script(
    input_file="molecule.com",
    job_name="h2o_opt",
    nodes=1,
    cpus_per_task=8,
    memory="16G",
    time_limit="24:00:00"
)

# 保存脚本
with open("h2o_job.sh", "w") as f:
    f.write(script)
```

**生成的脚本**:
```bash
#!/bin/bash
#SBATCH --job-name=h2o_opt
#SBATCH --partition=compute
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=24:00:00
#SBATCH --output=h2o_opt.out
#SBATCH --error=h2o_opt.err

cd $SLURM_SUBMIT_DIR

# Gaussian 模块
module load gaussian  # 根据实际环境调整

# 设置 Gaussian 环境变量
export GAUSSIAN_CPUS=8
export GAUSSIAN_MEM=16384MB

# 运行 Gaussian
g16 < molecule.com
```

#### ORCA 脚本模板

```python
from slurm_scheduler import generate_orca_script

script = generate_orca_script(
    input_file="molecule.inp",
    job_name="orca_test",
    cpus_per_task=4,
    memory="8G"
)
```

**生成的脚本**:
```bash
#!/bin/bash
#SBATCH --job-name=orca_test
#SBATCH --partition=compute
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=24:00:00

cd $SLURM_SUBMIT_DIR

# ORCA 模块
module load orca

# 运行 ORCA
orca molecule.inp --nt 4
```

#### PSI4 脚本模板

```python
from slurm_scheduler import generate_psi4_script

script = generate_psi4_script(
    input_file="molecule.py",
    job_name="psi4_test",
    cpus_per_task=16,
    memory="32G"
)
```

**生成的脚本**:
```bash
#!/bin/bash
#SBATCH --job-name=psi4_test
#SBATCH --partition=compute
#SBATCH --nodes=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=24:00:00

cd $SLURM_SUBMIT_DIR

# PSI4 模块
module load psi4

# 运行 PSI4
psi4 --nthread 16 molecule.py
```

---

### 5. 作业依赖管理

#### 提交依赖作业

```python
# 作业 B 依赖作业 A 成功后执行
result = scheduler.submit_dependent_job(
    script_path="step2.sh",
    dependency_job_ids=["12345"],
    dependency_type="afterok",  # afterok/afternotok/after/afterany
    job_name="step2"
)
```

#### 创建作业链

```python
# 顺序执行多个作业
scripts = [
    {
        'script_path': 'step1_opt.sh',
        'job_name': 'step1_optimization',
        'cpus_per_task': 8,
        'memory': '16G'
    },
    {
        'script_path': 'step2_freq.sh',
        'job_name': 'step2_frequency',
        'cpus_per_task': 8,
        'memory': '16G'
    },
    {
        'script_path': 'step3_analysis.sh',
        'job_name': 'step3_analysis',
        'cpus_per_task': 4,
        'memory': '8G'
    }
]

result = scheduler.create_job_chain(scripts)
print(f"作业链 ID: {result['job_ids']}")
# 输出：['12345', '12346', '12347']
```

---

### 6. 队列管理

#### 获取队列信息

```python
queue_info = scheduler.get_queue_info()

for partition in queue_info['partitions']:
    print(f"分区：{partition['name']}")
    print(f"  节点：{partition['nodes']}")
    print(f"  状态：{partition['state']}")
    print(f"  CPU: {partition['cpus']}")
    print(f"  内存：{partition['memory']}")
```

#### 获取用户作业列表

```python
jobs = scheduler.get_user_jobs(user="username")

for job in jobs:
    print(f"{job['job_id']}: {job['job_name']} - {job['status']}")
```

---

### 7. 错误处理和重试

#### 自动重试提交

```python
# 带重试的作业提交
result = scheduler.submit_job_with_retry(
    script_path="job.sh",
    job_name="retry_test",
    max_retries=3,  # 覆盖默认值
    retry_delay=60  # 60 秒后重试
)

if not result['success']:
    print(f"提交失败：{result['message']}")
    print(f"重试次数：{result['retry_count']}")
```

#### 等待作业完成

```python
# 等待作业完成 (带超时)
result = scheduler.wait_for_job(
    job_id="12345",
    interval=30,   # 每 30 秒检查一次
    timeout=3600   # 1 小时超时
)

if result['status'] == JobStatus.COMPLETED:
    print("作业成功完成!")
else:
    print(f"作业结束，状态：{result['status'].value}")
```

---

## 🔧 高级功能

### 1. 作业统计

```python
stats = scheduler.get_job_statistics(
    user="username",
    start_date="2026-01-01",
    end_date="2026-03-11"
)

print(f"总作业数：{stats['statistics']['total_jobs']}")
print(f"成功率：{stats['statistics']['success_rate']:.2f}%")
print(f"完成：{stats['statistics']['completed']}")
print(f"失败：{stats['statistics']['failed']}")
```

### 2. 自定义参数

```python
# 添加自定义 SLURM 参数
result = scheduler.submit_job(
    script_path="job.sh",
    custom_params={
        '--gres': 'gpu:1',
        '--constraint': 'high_memory',
        '--exclusive': ''
    }
)
```

### 3. Dry Run 模式

```python
# 预览将执行的命令
result = scheduler.submit_job(
    script_path="job.sh",
    dry_run=True
)

print(f"将执行：{result['command']}")
```

---

## 📊 测试

运行测试文件验证功能：

```bash
cd ~/.openclaw/workspace/kanban-react/backend
python test_slurm_scheduler.py
```

测试内容包括：
- ✅ 调度器初始化
- ✅ 脚本模板生成 (Gaussian/ORCA/PSI4)
- ✅ 便捷函数
- ✅ 作业提交 (Dry Run)
- ✅ 状态枚举
- ✅ 作业依赖链
- ✅ 队列信息获取

---

## ⚠️ 注意事项

1. **SLURM 环境要求**: 作业提交、状态检查等功能需要在 SLURM 集群环境中运行
2. **模块加载**: 脚本中的 `module load` 命令需要根据实际环境调整
3. **权限**: 确保用户有提交作业的权限
4. **资源限制**: 遵守集群的资源限制政策

---

## 📞 常见问题

### Q: 如何在非 SLURM 环境测试？
A: 使用 `dry_run=True` 参数预览命令，或运行测试脚本的 Dry Run 测试。

### Q: 如何调整内存单位？
A: 支持 K/M/G/T 单位，如 "4000M"、"4G"、"0.25T"。

### Q: 作业依赖有哪些类型？
A: 
- `afterok`: 依赖作业成功后执行
- `afternotok`: 依赖作业失败后执行
- `after`: 依赖作业完成后执行 (无论成功失败)
- `afterany`: 依赖作业任意状态后执行

### Q: 如何调试提交失败？
A: 检查返回的 `message` 字段，查看 SLURM 错误信息，常见原因包括：
- 脚本路径不存在
- 资源请求超出限制
- 分区名称错误
- 权限不足

---

## 📚 相关文档

- [SLURM 官方文档](https://slurm.schedmd.com/documentation.html)
- [Gaussian 集群使用指南](https://gaussian.com/cluster/)
- [ORCA 并行计算](https://sites.google.com/site/orcainputlibrary/parallel-calculations)
- [PSI4 高性能计算](https://psicode.org/psi4manual/master/parallel.html)

---

**最后更新**: 2026-03-11  
**维护者**: Dudu (AI Assistant)

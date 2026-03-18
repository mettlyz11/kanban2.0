# SLURM 作业调度模块 - 快速参考

## 📦 已创建文件

| 文件 | 大小 | 说明 |
|------|------|------|
| `slurm_scheduler.py` | 49K | 核心模块 |
| `test_slurm_scheduler.py` | 8.2K | 测试文件 |
| `SLURM_SCHEDULER_README.md` | 11K | 详细文档 |
| `test_gaussian_job.sh` | 示例 | 生成的 Gaussian 脚本示例 |

---

## 🚀 快速使用

### 1. 导入模块

```python
from slurm_scheduler import (
    SLURMScheduler,
    SoftwareType,
    submit_job,
    check_job_status,
    cancel_job,
    generate_gaussian_script,
    generate_orca_script,
    generate_psi4_script
)
```

### 2. 提交作业

```python
# 方法 1: 使用便捷函数
result = submit_job(
    script_path="my_job.sh",
    job_name="test",
    cpus_per_task=8,
    memory="16G"
)

# 方法 2: 使用调度器类
scheduler = SLURMScheduler()
result = scheduler.submit_job(
    script_path="my_job.sh",
    job_name="test",
    nodes=1,
    cpus_per_task=8,
    memory="16G",
    time_limit="24:00:00"
)

print(f"作业 ID: {result['job_id']}")
```

### 3. 检查状态

```python
status = check_job_status("12345")
print(f"状态：{status['status'].value}")
# 输出：状态：RUNNING
```

### 4. 取消作业

```python
result = cancel_job("12345")
print(result['message'])
```

### 5. 生成脚本模板

```python
# Gaussian
script = generate_gaussian_script(
    input_file="molecule.com",
    cpus_per_task=8,
    memory="16G"
)

# ORCA
script = generate_orca_script(
    input_file="molecule.inp",
    cpus_per_task=4
)

# PSI4
script = generate_psi4_script(
    input_file="molecule.py",
    cpus_per_task=16
)

# 保存脚本
with open("job.sh", "w") as f:
    f.write(script)
```

---

## ✅ 已实现功能

| 功能 | 状态 | 说明 |
|------|------|------|
| ✅ 创建 slurm_scheduler.py 模块 | 完成 | 49K 完整实现 |
| ✅ 实现 submit_job() | 完成 | 支持所有 SLURM 参数 |
| ✅ 实现 check_job_status() | 完成 | 实时状态 + 历史查询 |
| ✅ 实现 cancel_job() | 完成 | 单个/批量/按名称取消 |
| ✅ 生成 SLURM 脚本模板 | 完成 | Gaussian/ORCA/PSI4/CUSTOM |
| ✅ 作业依赖管理 | 完成 | 依赖提交 + 作业链 |
| ✅ 队列管理 | 完成 | 队列信息 + 用户作业列表 |
| ✅ 错误处理和重试 | 完成 | 自动重试 + 超时处理 |

---

## 🎯 核心 API

### 作业提交

```python
scheduler.submit_job(
    script_path="job.sh",          # 必填：脚本路径
    job_name="my_job",             # 可选：作业名称
    partition="compute",           # 可选：分区
    nodes=1,                       # 可选：节点数
    cpus_per_task=8,               # 可选：CPU 数
    memory="16G",                  # 可选：内存
    time_limit="24:00:00",         # 可选：时间限制
    dependencies=["12345"],        # 可选：依赖作业
    dry_run=False                  # 可选：仅预览
)
```

### 状态检查

```python
scheduler.check_job_status("12345")
# 返回：
# {
#     'success': True,
#     'job_id': '12345',
#     'status': JobStatus.RUNNING,
#     'details': {...},
#     'message': '作业状态：RUNNING'
# }
```

### 作业取消

```python
scheduler.cancel_job("12345", reason="完成")
# 返回：
# {
#     'success': True,
#     'job_id': '12345',
#     'message': '作业 12345 已成功取消'
# }
```

### 脚本生成

```python
scheduler.generate_script_template(
    software=SoftwareType.GAUSSIAN,  # 或 ORCA/PSI4/CUSTOM
    input_file="molecule.com",
    job_name="opt_job",
    cpus_per_task=8,
    memory="16G",
    time_limit="24:00:00"
)
```

---

## 📊 作业状态

| 状态 | 说明 |
|------|------|
| `PENDING` | 等待中 |
| `RUNNING` | 运行中 |
| `COMPLETED` | 已完成 |
| `FAILED` | 失败 |
| `CANCELLED` | 已取消 |
| `TIMEOUT` | 超时 |
| `NODE_FAIL` | 节点故障 |
| `UNKNOWN` | 未知 |

---

## 🔧 高级功能

### 作业依赖链

```python
scripts = [
    {'script_path': 'step1.sh', 'job_name': 'step1'},
    {'script_path': 'step2.sh', 'job_name': 'step2'},
    {'script_path': 'step3.sh', 'job_name': 'step3'}
]

result = scheduler.create_job_chain(scripts)
# 自动创建依赖关系：step1 → step2 → step3
```

### 带重试的提交

```python
result = scheduler.submit_job_with_retry(
    script_path="job.sh",
    max_retries=3,
    retry_delay=60
)
```

### 等待作业完成

```python
result = scheduler.wait_for_job(
    job_id="12345",
    interval=30,      # 每 30 秒检查
    timeout=3600      # 1 小时超时
)
```

### 作业统计

```python
stats = scheduler.get_job_statistics(
    user="username",
    start_date="2026-01-01"
)
# 返回：总作业数、成功率、完成/失败数等
```

---

## 🧪 测试

```bash
cd ~/.openclaw/workspace/kanban-react/backend
python3 test_slurm_scheduler.py
```

**测试结果**: ✅ 所有测试通过

---

## ⚠️ 环境要求

- **必需**: SLURM 集群环境 (用于实际作业提交)
- **可选**: 非 SLURM 环境 (可使用 Dry Run 模式和脚本生成功能)

**SLURM 命令**: `sbatch`, `squeue`, `scancel`, `scontrol`, `sacct`, `sinfo`

---

## 📚 详细文档

查看完整文档：`SLURM_SCHEDULER_README.md`

包含：
- 完整 API 参考
- 所有参数说明
- 详细使用示例
- 常见问题解答
- 故障排除指南

---

## 📞 使用示例

### Gaussian 计算完整流程

```python
from slurm_scheduler import SLURMScheduler, SoftwareType

# 1. 创建调度器
scheduler = SLURMScheduler()

# 2. 生成 Gaussian 脚本
script = scheduler.generate_script_template(
    software=SoftwareType.GAUSSIAN,
    input_file="h2o.com",
    job_name="h2o_opt",
    cpus_per_task=8,
    memory="16G",
    time_limit="24:00:00"
)

# 3. 保存脚本
with open("h2o_job.sh", "w") as f:
    f.write(script)

# 4. 提交作业
result = scheduler.submit_job(
    script_path="h2o_job.sh",
    job_name="h2o_opt",
    cpus_per_task=8,
    memory="16G",
    mail_user="user@example.com",
    mail_type=["END", "FAIL"]
)

if result['success']:
    job_id = result['job_id']
    print(f"作业提交成功：{job_id}")
    
    # 5. 等待完成
    final_status = scheduler.wait_for_job(job_id, timeout=86400)
    
    # 6. 检查结果
    if final_status['status'].value == 'COMPLETED':
        print("计算成功完成！")
    else:
        print(f"计算结束，状态：{final_status['status'].value}")
```

---

**创建时间**: 2026-03-11  
**版本**: 1.0  
**维护者**: Dudu (AI Assistant)

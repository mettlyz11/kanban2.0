# T109 MacMini 任务轮询服务

## 概述

MacMini 任务轮询服务是一个后台守护进程，用于自动处理 T109 系统中的计算任务。

### 核心功能

1. ✅ **数据库轮询** - 自动获取待处理任务
2. ✅ **SLURM 作业提交** - 调用 SLURM 提交计算作业
3. ✅ **状态监控** - 实时监控作业状态
4. ✅ **结果处理** - 读取计算结果并更新数据库
5. ✅ **多任务并行** - 支持并发执行多个任务
6. ✅ **错误恢复** - 自动重试失败任务
7. ✅ **日志记录** - 完整的执行日志
8. ✅ **心跳机制** - 服务健康监控

## 快速开始

### 1. 测试服务

```bash
cd ~/.openclaw/workspace/kanban-react/backend
python3 task_worker.py --test
```

### 2. 启动服务

```bash
# 前台运行（调试用）
python3 task_worker.py --start

# 后台运行（生产环境）
nohup python3 task_worker.py --start > logs/task_worker.out 2>&1 &

# 或使用 systemd（推荐）
sudo systemctl start task-worker
```

### 3. 查看状态

```bash
python3 task_worker.py --status
```

### 4. 单轮执行

```bash
# 只执行一轮，不循环（适合测试）
python3 task_worker.py --once
```

## 配置说明

### 环境变量

```bash
# 数据库路径（可选，默认在 backend/kanban_v5.db）
export TASK_WORKER_DB="/path/to/kanban_v5.db"

# SLURM 配置（可选）
export SLURM_PARTITION="compute"
export SLURM_TIME="24:00:00"
export SLURM_CPUS="4"
export SLURM_MEM="8G"

# 轮询配置
export POLL_INTERVAL="10"  # 秒
export MAX_CONCURRENT="5"  # 最大并行任务数
```

### 配置文件

在 `task_worker.py` 中修改以下常量：

```python
# 轮询配置
POLL_INTERVAL_SECONDS = 10      # 数据库轮询间隔
MAX_CONCURRENT_TASKS = 5        # 最大并行任务数
TASK_TIMEOUT_HOURS = 48         # 任务超时时间
HEARTBEAT_INTERVAL_SECONDS = 30 # 心跳间隔

# SLURM 配置
SLURM_CONFIG = {
    'partition': 'compute',
    'time': '24:00:00',
    'nodes': 1,
    'ntasks': 1,
    'cpus_per_task': 4,
    'mem': '8G',
    'output_dir': './slurm_output',
}
```

## 任务格式

### 数据库任务表结构

任务存储在 `tasks` 表中，关键字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 任务 ID（主键） |
| title | TEXT | 任务标题 |
| description | TEXT | 任务描述 |
| status | TEXT | 状态：todo/in_progress/submitted/running/completed/failed |
| priority | TEXT | 优先级：critical/high/medium/low |
| details | TEXT | JSON 格式的任务详情 |
| depends_on | INTEGER | 依赖的任务 ID |
| result_summary | TEXT | 结果摘要 |
| start_time | TIMESTAMP | 开始时间 |
| end_time | TIMESTAMP | 结束时间 |

### 任务详情格式（details 字段）

```json
{
  "type": "psi4_calculation",
  "config": {
    "method": "B3LYP",
    "basis": "6-31G(d)",
    "scf_type": "DF"
  },
  "geometry": "0 1\nC 0.0 0.0 0.0\nH 0.0 0.0 1.09\nH 1.02 0.0 -0.36\nH -0.51 0.89 -0.36\nH -0.51 -0.89 -0.36",
  "script": "自定义脚本内容（可选）"
}
```

### 支持的任务类型

1. **psi4_calculation** - PSI4 量子化学计算
2. **data_processing** - 数据处理
3. **custom_script** - 自定义脚本

## 工作流程

```
┌─────────────┐
│  待处理任务  │
│  (status=   │
│   todo)     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  轮询获取    │
│  (每 10 秒)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  生成脚本    │
│  (根据类型)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  提交 SLURM  │
│  (sbatch)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  监控状态    │
│  (squeue)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  读取结果    │
│  (输出文件)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  更新数据库  │
│  (status=   │
│   completed)│
└─────────────┘
```

## 日志管理

### 日志位置

```
~/.openclaw/workspace/kanban-react/backend/logs/
├── task_worker_20260311.log  # 按日期分割的日志
├── task_worker_20260312.log
└── ...
```

### 日志级别

- INFO - 正常操作信息
- WARNING - 警告信息
- ERROR - 错误信息
- DEBUG - 调试信息（心跳等）

### 查看实时日志

```bash
tail -f logs/task_worker_$(date +%Y%m%d).log
```

## 错误处理

### 自动重试机制

- 失败任务自动重试，最多 3 次
- 重试间隔：60 秒 × 重试次数（指数退避）
- 超过最大重试次数后标记为 failed

### 超时处理

- 任务超过 48 小时未更新视为卡住
- 自动检查并标记为失败

### 常见错误

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| sbatch: command not found | SLURM 未安装 | 安装 SLURM 或检查 PATH |
| Database is locked | 数据库被占用 | 等待或增加超时时间 |
| Job submission failed | SLURM 配置错误 | 检查分区、资源限制 |

## 系统集成

### 创建 systemd 服务（推荐）

创建 `/etc/systemd/system/task-worker.service`:

```ini
[Unit]
Description=T109 MacMini Task Worker Service
After=network.target

[Service]
Type=simple
User=mettlyz
WorkingDirectory=/Users/mettlyz/.openclaw/workspace/kanban-react/backend
ExecStart=/usr/bin/python3 task_worker.py --start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable task-worker
sudo systemctl start task-worker
sudo systemctl status task-worker
```

### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY backend/ /app/

RUN pip install --no-cache-dir flask flask-cors

CMD ["python3", "task_worker.py", "--start"]
```

## API 接口

### 通过数据库交互

服务直接操作数据库，无需额外 API。

### 创建任务示例

```python
import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect('kanban_v5.db')
c = conn.cursor()

# 创建 PSI4 计算任务
details = {
    "type": "psi4_calculation",
    "config": {
        "method": "B3LYP",
        "basis": "6-31G(d)"
    },
    "geometry": "0 1\nO 0.0 0.0 0.0\nH 0.0 0.757 0.586\nH 0.0 -0.757 0.586"
}

c.execute('''
    INSERT INTO tasks (project_id, title, description, status, priority, details, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
''', (1, '水分子优化', 'B3LYP/6-31G(d) 几何优化', 'todo', 'high', 
      json.dumps(details, ensure_ascii=False), datetime.now().isoformat()))

conn.commit()
conn.close()
```

## 监控和告警

### 检查服务状态

```bash
# 检查进程
ps aux | grep task_worker

# 检查心跳
tail -100 logs/task_worker_*.log | grep "心跳"

# 检查失败任务
sqlite3 kanban_v5.db "SELECT id, title, result_summary FROM tasks WHERE status='failed' ORDER BY updated_at DESC LIMIT 10;"
```

### 集成监控系统

可以集成到现有的监控系统（P049-T041）：

```python
# 在 monitoring_routes.py 中添加
@app.route('/api/monitoring/task-worker/status')
def task_worker_status():
    """获取任务轮询服务状态"""
    try:
        # 检查进程
        result = subprocess.run(['pgrep', '-f', 'task_worker.py'], 
                              capture_output=True, text=True)
        running = bool(result.stdout.strip())
        
        # 统计任务
        db = TaskDatabase()
        stats = {
            'todo': len(db.get_pending_tasks(limit=1000)),
            'running': 0,  # 需要查询数据库
            'failed': 0,
            'completed_today': 0
        }
        
        return jsonify({
            'success': True,
            'running': running,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

## 性能优化

### 调整并行度

根据系统资源调整 `MAX_CONCURRENT_TASKS`:

```python
# Mac Mini (20 核)
MAX_CONCURRENT_TASKS = 15  # 高性能模式
MAX_CONCURRENT_TASKS = 10  # 平衡模式
MAX_CONCURRENT_TASKS = 5   # 保守模式
```

### 优化轮询间隔

```python
# 高负载场景
POLL_INTERVAL_SECONDS = 5   # 快速响应

# 低负载场景
POLL_INTERVAL_SECONDS = 30  # 节省资源
```

## 故障排查

### 1. 服务不启动

```bash
# 检查 Python 版本
python3 --version  # 需要 3.8+

# 检查依赖
python3 -c "import sqlite3, json, logging"

# 手动运行
python3 task_worker.py --start
```

### 2. 任务不执行

```bash
# 检查任务状态
sqlite3 kanban_v5.db "SELECT id, title, status, depends_on FROM tasks WHERE status='todo';"

# 检查依赖
sqlite3 kanban_v5.db "SELECT id, title, status FROM tasks WHERE id IN (SELECT depends_on FROM tasks WHERE status='todo');"
```

### 3. SLURM 作业失败

```bash
# 查看作业状态
squeue -u $USER

# 查看作业输出
cat slurm_output/task_<task_id>_<job_id>.out
cat slurm_output/task_<task_id>_<job_id>.err

# 测试 SLURM
sbatch --test task_worker.py
```

## 最佳实践

1. **任务设计**
   - 保持任务原子性（单一职责）
   - 设置合理的超时时间
   - 提供详细的错误信息

2. **资源管理**
   - 根据系统负载调整并行度
   - 监控内存使用
   - 定期清理旧的输出文件

3. **监控告警**
   - 设置失败任务告警
   - 监控服务心跳
   - 定期检查日志

4. **备份恢复**
   - 定期备份数据库
   - 保存重要的计算结果
   - 记录配置变更

## 开发调试

### 启用调试模式

```python
# 修改日志级别
logging.basicConfig(level=logging.DEBUG)
```

### 模拟 SLURM

在没有 SLURM 的环境中测试：

```python
# 修改 SlurmManager.submit_job
def submit_job(self, task, script_content):
    # 模拟模式
    logger.info(f"[模拟] 提交任务 {task.id}")
    return 99999, ""  # 返回模拟作业 ID
```

### 单元测试

```python
import unittest

class TestTaskWorker(unittest.TestCase):
    def test_database_connection(self):
        db = TaskDatabase()
        tasks = db.get_pending_tasks()
        self.assertIsInstance(tasks, list)
    
    def test_script_generation(self):
        task = Task(id=1, title="Test", ...)
        executor = TaskExecutor(db, slurm)
        script = executor.generate_script(task)
        self.assertIn("echo", script)

if __name__ == '__main__':
    unittest.main()
```

## 版本历史

- **v1.0.0** (2026-03-11) - 初始版本
  - ✅ 基础轮询功能
  - ✅ SLURM 集成
  - ✅ 状态监控
  - ✅ 错误恢复
  - ✅ 日志和心跳

## 相关文件

- `task_worker.py` - 主服务文件
- `logs/` - 日志目录
- `slurm_output/` - SLURM 作业输出
- `kanban_v5.db` - 数据库文件

## 联系方式

如有问题，请查看日志或联系开发团队。

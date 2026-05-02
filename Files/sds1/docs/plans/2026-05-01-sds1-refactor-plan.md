# sds1 重构实施计划

## Phase A: 配置管理

### Task A1: 创建配置加载器
- 文件: `sds1/config_loader.py`
- 功能: 加载 YAML/JSON 配置，提供 `get_config(key)` 接口
- 测试: 验证配置加载和默认值

### Task A2: 创建主配置文件
- 文件: `sds1/config.yaml`
- 内容: 所有路径、阈值、调度间隔、模型配置
- 验证: 配置文件可被正确解析

### Task A3: 替换硬编码路径（分批）
- 批次 1: `sds_main.py`, `modules/subagent_scheduler.py`
- 批次 2: `core/*.py`, `modules/*.py`
- 批次 3: `tools/*.py`, `scripts/*.sh`
- 验证: grep 确认无遗漏

## Phase B: 项目结构标准化

### Task B1: 创建 pyproject.toml
- 定义包名 `sds1`，版本 `4.6.1`
- 指定入口点 `sds1 = sds1.cli:main`

### Task B2: 创建 requirements.txt
- 从代码中提取所有 import
- 包含: pymysql, requests, openai, numpy 等

### Task B3: 重组目录结构
- 创建 `src/sds1/` 包目录
- 移动 `core/`, `modules/`, `tools/` 到 `src/sds1/`
- 更新所有 import 路径

### Task B4: 创建 CLI 入口
- 文件: `src/sds1/cli.py`
- 支持: `sds1 start`, `sds1 stop`, `sds1 status`

## Phase C: 测试体系

### Task C1: 配置 pytest
- `pytest.ini`, `conftest.py`
- 覆盖率目标 60%

### Task C2: 核心模块单元测试
- `test_config_loader.py`
- `test_task_generation_guard.py`
- `test_execution_evaluator.py`

### Task C3: 集成测试
- 完整 SDS 周期模拟
- 使用 mock 数据库连接

## 执行模式
- Subagent-driven: 每个 Task 分配一个子代理
- 两阶段审查: 功能审查 + 代码质量审查

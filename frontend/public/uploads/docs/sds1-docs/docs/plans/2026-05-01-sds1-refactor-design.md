# sds1 重构设计文档

## 目标
将 sds1 从松散脚本集合升级为标准化、可维护、可测试的 Python 包。

## 现状问题
1. 71 个 Python 文件无统一入口
2. 所有路径硬编码（`workspace/sds1/...`）
3. 无依赖管理（requirements.txt）
4. 无配置系统
5. 测试都是任务特定，无单元测试
6. 无持续集成/质量门控

## 设计方案

### A. 配置管理（优先级 1）
- 创建 `sds1/config.yaml` — 集中管理所有路径、阈值、间隔
- 创建 `sds1/config_loader.py` — 统一加载配置
- 逐步替换硬编码路径为配置读取

### B. 项目结构标准化（优先级 2）
```
sds1/
├── pyproject.toml          # Python 包定义
├── requirements.txt        # 依赖
├── README.md              # 项目说明
├── config.yaml            # 主配置
├── src/sds1/              # 源码包
│   ├── __init__.py
│   ├── core/              # 核心模块
│   ├── modules/           # 功能模块
│   ├── tools/             # 工具
│   └── cli.py             # 命令行入口
├── tests/                 # 测试
│   ├── unit/              # 单元测试
│   ├── integration/       # 集成测试
│   └── conftest.py        # pytest 配置
└── scripts/               # 启动脚本
```

### C. 测试体系（优先级 3）
- pytest + pytest-cov + pytest-mock
- 核心模块单元测试（覆盖率目标 60%）
- GitHub Actions / 本地 CI 脚本

## 实施顺序
1. A（配置管理）→ 2. B（结构标准化）→ 3. C（测试体系）

## 风险
- 路径替换可能遗漏 → 用 grep 验证
- 引入新依赖冲突 → 在虚拟环境测试

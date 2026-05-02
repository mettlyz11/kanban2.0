# SDS调度系统V4.3升级 - 频率限制与去重机制

## 任务信息
- **任务ID**: #2110
- **任务名称**: T1: AI助手优化 - 调度系统频率限制与去重机制升级
- **升级日期**: 2026-04-27
- **版本**: V4.3.0

## 升级概述

本次升级针对调度系统任务生成过频的问题，实现了三层防护机制：

1. **频率限制层** - 每目标每24小时最多生成2个任务
2. **水位控制层** - 每目标最多3个pending任务
3. **去重机制层** - 标题前缀15字精确匹配 + 语义相似度计算

---

## 文件清单

| 文件名 | 说明 | 大小 |
|--------|------|------|
| `scheduler_v43_upgrade.py` | 调度系统V4.3核心升级代码 | ~28KB |
| `task_generation_monitor.py` | 任务生成频率监控脚本 | ~20KB |
| `test_deduplication_v43.py` | 去重机制单元测试套件 | ~24KB |
| `README.md` | 本说明文件 | ~ |

---

## 核心功能详解

### 1. 频率限制器 (RateLimiterV43)

**配置参数:**
- `MAX_TASKS_PER_24H = 2` - 每目标每天最多2个任务
- `WINDOW_HOURS = 24` - 滑动窗口24小时

**工作原理:**
```
任务创建请求 → 查询过去24小时该目标已生成任务数
               → 已达到2个 → 拦截，返回频率限制原因
               → 未达到 → 允许进入下一检查
```

### 2. Pending水位控制器 (PendingWatermarkV43)

**配置参数:**
- `MAX_PENDING_PER_GOAL = 3` - 每目标最多3个pending任务

**工作原理:**
```
检查通过 → 查询该目标当前pending任务数
           → 已达到3个 → 拦截，返回水位限制原因
           → 未达到 → 允许进入下一检查
```

### 3. 标题去重器 (TitleDeduplicatorV43)

**双层去重机制:**

**第一层 - 前缀精确匹配:**
- 匹配长度：前15个字符
- 匹配范围：同目标下近7天的任务
- 优先级：最高，先于语义检查

**第二层 - 语义相似度匹配:**
- 算法：Levenshtein编辑距离
- 相似度阈值：0.85（可配置）
- 文本标准化：去除标点、统一小写、去空格
- 检查范围：同目标下近7天任务

**相似度计算公式:**
```
相似度 = 1 - (编辑距离 / 最大字符串长度)
```

### 4. 审计日志系统 (AuditLoggerV43)

**记录字段:**
- `event_id`: 事件唯一ID
- `event_type`: 事件类型（pre_check/create/error）
- `task_title`: 任务标题
- `goal_id`: 目标ID
- `decision`: 决策结果
- `reason`: 决策原因
- `details`: 详细信息
- `timestamp`: 时间戳

**日志格式:** JSON Lines (每行一条JSON)

---

## 使用方法

### 快速开始

```python
from scheduler_v43_upgrade import SchedulerV43

# 初始化调度器
scheduler = SchedulerV43()

# 检查任务是否可以生成
result = scheduler.can_generate_task(
    title="T1: AI助手优化 - 测试任务",
    goal_id=1
)

if result.allowed:
    print(f"✅ 可以生成: {result.reason}")
else:
    print(f"⛔ 被拦截: {result.reason}")

# 安全创建任务
task_id = scheduler.create_task_safely(
    title="T1: AI助手优化 - 测试任务",
    description="测试V4.3调度系统",
    goal_id=1,
    priority=2
)
```

### 便捷函数

```python
from scheduler_v43_upgrade import quick_check, safe_create_task

# 快速检查
can_create, reason = quick_check("任务标题", goal_id=1)

# 安全创建（一行搞定）
task_id = safe_create_task("标题", "描述", goal_id=1)
```

### 监控脚本

```bash
# 运行监控检查（过去24小时）
python task_generation_monitor.py

# 指定时间范围
python task_generation_monitor.py --hours 48

# 只输出JSON
python task_generation_monitor.py --json-only

# 不保存报告文件
python task_generation_monitor.py --no-save
```

### 运行单元测试

```bash
# 运行所有测试
python test_deduplication_v43.py

# 列出所有测试类
python test_deduplication_v43.py --list

# 详细输出
python test_deduplication_v43.py --verbose
```

---

## 测试覆盖

单元测试覆盖以下10个方面：

| 测试类 | 覆盖内容 | 测试数 |
|--------|---------|--------|
| `TestLevenshteinDistance` | 编辑距离算法 | ~15 |
| `TestStringSimilarity` | 相似度计算 | ~10 |
| `TestTextNormalization` | 文本标准化 | ~8 |
| `TestPrefixMatch` | 前缀匹配 | ~4 |
| `TestRateLimiter` | 频率限制器 | ~5 |
| `TestPendingWatermark` | 水位控制器 | ~5 |
| `TestTitleDeduplicator` | 去重器综合 | ~5 |
| `TestSchedulerIntegration` | 集成测试 | ~5 |
| `TestDecisionType` | 枚举类型 | ~2 |
| `TestBoundaryConditions` | 边界条件 | ~5 |
| **总计** | | **~60+ 测试用例** |

---

## 决策类型说明

| 决策类型 | 说明 | 允许？|
|---------|------|-------|
| `ALLOW` | 通过所有检查 | ✅ |
| `BLOCK_RATE_LIMIT` | 频率限制拦截 | ❌ |
| `BLOCK_PENDING_LIMIT` | 水位限制拦截 | ❌ |
| `BLOCK_DUPLICATE` | 去重拦截（前缀或语义） | ❌ |
| `ERROR` | 错误 | ❌ |

---

## 系统状态报告示例

```
======================================================================
  SDS调度系统V4.3状态报告
======================================================================
版本: V4.3
时间: 2026-04-27T10:30:00

【各目标生成状态】
  ✅ 目标1:
     24h生成: 0/2
     pending: 0/3

  ✅ 目标2:
     24h生成: 1/2
     pending: 1/3

  ⛔ 目标7:
     24h生成: 2/2
     pending: 2/3

【审计统计】
  总检查次数: 15
  通过: 8, 拦截: 7
    - 频率限制拦截: 3
    - 水位限制拦截: 1
    - 去重拦截: 3
======================================================================
```

---

## 监控警报级别

| 级别 | 图标 | 触发条件 |
|------|------|---------|
| `critical` | 🔴 | 每小时≥5任务 / 某目标日生成>2 / 重复任务≥5个 |
| `warning` | �⚠️ | 每小时≥3任务 / pending>3 / 重复任务≥3个 |
| `info` | ℹ️ | 重复任务≥2个 |

---

## 升级前后对比

| 项目 | V4.2及之前 | V4.3 |
|------|-----------|------|
| 频率限制 | 无 / 不完善 | ✅ 每目标2个/24小时 |
| Pending水位 | 无 | ✅ 每目标最多3个 |
| 去重机制 | 不完善 | ✅ 前缀15字匹配 + 语义相似度 |
| 审计日志 | 无 | ✅ 完整记录每次检查 |
| 监控系统 | 无 | ✅ 实时监控+报警 |
| 单元测试 | 无 | ✅ 60+测试用例 |

---

## 注意事项

1. **数据库连接**: 所有模块都依赖 `lib.db_connector`，确保数据库连接配置正确

2. **日志目录**: 日志默认保存在 `~/openclaw/logs/`，确保该目录可写

3. **幂等性**: 本版本不包含幂等性检查（已在V4.6实现），如需请升级

4. **性能影响**: 去重检查需要数据库查询，建议批量操作时注意性能

5. **阈值调整**: 默认阈值是根据历史数据设定的，如需调整可在初始化时指定：

   ```python
   scheduler = SchedulerV43(
       max_tasks_per_24h=5,       # 放宽到5个
       max_pending_per_goal=10,    # 放宽到10个
       similarity_threshold=0.95   # 更严格的相似度
   )
   ```

---

## 后续升级建议

1. **V4.4** - 集成幂等性检查（基于内容哈希）
2. **V4.5** - 加入机器学习模型预测任务重复率
3. **V4.6** - 完善的审计追溯系统（已完成）
4. **V4.7** - 任务生成队列管理

---

## 联系与支持

如有问题或建议，请：
1. 查看日志文件: `~/openclaw/logs/sds-scheduler-v43.log`
2. 运行监控脚本获取详细状态
3. 运行单元测试验证功能

---

**V4.3升级完成！让调度系统更稳定、更高效！🚀**

# OpenClaw调度系统基于Agentic Workflow Patterns的优化方案

## 一、任务背景与目标

当前 OpenClaw 调度系统已经具备三个基础能力：第一，能够从任务库中发现 pending 任务；第二，能够基于简单复杂度规则决定是否优先执行；第三，能够在有限并发槽位内启动子代理执行任务。这个体系已经能够工作，但从架构视角看，它仍然偏向“脚本式调度”，而不是“真正的 agentic orchestration”。其主要问题是：状态显式性不足、执行闭环不完整、失败恢复能力弱、质量验证依赖任务执行者自觉、复杂任务缺少标准拆解路径、调度器对事件和记忆的利用不足。

本次优化以“9类 Agentic Workflow 模式”作为统一抽象框架，对现有 OpenClaw 调度系统进行架构重构建议。这里的“9类模式”不是营销概念，而是可以直接转化为工程结构的九种控制机制：规划-执行-反思、工具调用编排、多Agent协作、记忆管理、状态机、事件驱动、子任务拆分、回滚重试、结果验证。核心目标不是盲目增加复杂性，而是在不破坏现有系统可用性的前提下，把调度系统升级为“可解释、可恢复、可验证、可扩展”的 agentic runtime。

## 二、现状分析

### 1. 当前已存在能力

结合仓库中的 `scheduler/scheduler.py`、`scheduler/analyzer.py`、`scheduler/launcher.py`、`scripts/auto-task-scheduler.py` 以及 `skills/kanban-sync/` 下的多代理原型，可以确认当前系统已经具备以下基础：

- 轮询式任务发现：周期性扫描 `pending` 任务；
- 简单复杂度评估：根据优先级、描述长度、关键词等做粗粒度打分；
- 并发槽位控制：限制同时运行的任务数；
- 子代理启动：通过 CLI 或预构造 spawn 参数交给系统执行；
- 初步多代理原型：已有并发管理、拆解、分配、完成监控等组件雏形；
- 看板/数据库联动：可以把任务状态更新回任务数据库。

### 2. 当前关键短板

但从 agentic workflow 视角看，当前系统仍然有几个决定性缺口：

1. **缺少显式状态机**：任务大多只在 `pending/in_progress/completed` 间跳转，缺少 `analyzing/planning/verifying/blocked` 等中间态，导致调度器难以做精细控制。
2. **缺少验证关卡**：当前完成判定过于依赖执行者是否写回结果，没有独立 verifier，容易出现“做了但没验”“写了但没做”。
3. **缺少失败恢复机制**：虽有原型中的 retry 思路，但主路径里没有统一 rollback/retry 策略。
4. **任务拆解不稳定**：复杂任务需要拆分时，当前实现更多是规则触发，尚未形成标准化分解-回收闭环。
5. **事件利用不足**：现在更像定时器轮询，不是事件驱动系统。任务状态变化、验证失败、附件生成等都可以成为事件源。
6. **工作记忆弱**：任务执行上下文没有统一的 memory envelope，反思结果不能稳定回流到后续调度判断。

## 三、9类Agentic Workflow Patterns及其工程映射

### 模式1：规划-执行-反思（Plan-Execute-Reflect）
这是最基础也最关键的 agent 模式。复杂任务不应直接执行，而应先生成执行计划，再运行，再反思缺口。当前系统中，只有部分任务在提示词里要求 Brainstorm / Design / Plan / Execute，但调度器本身并不理解这个循环。

**工程映射**：在调度器内增加 `PlannerExecutorReflector` 层。任务进入后先形成结构化 plan，执行后生成 reflection，若 reflection 暗示交付不完整，则进入验证失败分支或补执行分支。

### 模式2：工具调用编排（Tool Orchestration）
子代理不是“自由发挥”的文本机器人，而应被调度器清晰赋予工具路径、顺序和失败处理策略。例如数据库更新、附件插入、报告生成、测试运行都属于工具链。

**工程映射**：在 spawn payload 中写入工具协议模板；在调度器里记录“需要哪些工具、顺序如何、哪些工具是必须的”。这样能减少任务执行的不确定性。

### 模式3：多Agent协作（Multi-Agent Collaboration）
复杂任务中常见研究、编码、验证三类工作角色。现有系统已有并发与多代理原型，但还缺少基于角色的协同，而不仅是“多个一样的 worker”。

**工程映射**：至少划分为 Researcher、Builder、Verifier 三类角色；调度器根据任务 profile 分派。高复杂任务时，允许主任务拆成研究/实现/验证三个子任务并行或半并行推进。

### 模式4：记忆管理（Memory Management）
记忆不等于长期存档。调度中更重要的是“工作记忆”和“策略记忆”：这个任务已经识别到什么风险、尝试过什么、为何失败、哪种方案更优。

**工程映射**：为每个任务上下文增加 `memory` 字段，记录 profile、plan、retry history、quality gate 结果。对全局调度器，可维护轻量 policy memory，例如“高优先级战略任务必须经过 verifier”。

### 模式5：状态机（State Machine）
没有状态机，就没有可靠调度。agentic 系统本质上就是带守卫条件的状态转移系统。

**工程映射**：建议扩展状态为：`pending -> analyzing -> planning -> ready -> executing -> verifying -> completed/failed/blocked`。其中任何阶段失败都可根据策略回退到 `ready` 或 `pending`。

### 模式6：事件驱动（Event-Driven）
仅靠固定轮询会增加延迟并浪费资源。数据库状态变化、附件落盘、验证失败、超时等都应该触发下一步。

**工程映射**：增加事件总线 `EventBus`，最小可行实现可以先在内存中完成；未来可替换为 jsonl 队列、Redis stream 或数据库 event 表。关键事件包括：`classified`、`decomposed`、`executed`、`validated`、`retry_scheduled` 等。

### 模式7：子任务拆分（Task Decomposition）
这对 T1 类任务尤其重要。若复杂任务不拆，会拖慢单代理执行，降低完成率，并放大失败成本。

**工程映射**：用分析器判断是否拆分；默认至少支持“研究与模式映射 / 架构设计与实现 / 基准测试与结果验证”三段式。将父任务保留为 orchestration 节点，子任务进入实际执行队列。

### 模式8：回滚重试（Rollback & Retry）
没有统一的失败策略，系统会出现卡死的 `in_progress` 僵尸任务。当前系统虽然有“最多重试2次”的原型，但未形成主线机制。

**工程映射**：定义重试预算、失败原因、回滚点。验证失败可回退到 `ready`，执行异常可回退到 `planning` 或 `pending`，超过阈值则 `blocked`，等待人工介入。

### 模式9：结果验证（Result Validation）
真正把系统从“自动运行脚本”提升为“agentic system”的关键，就是让结果经过独立验证，而不是只看状态是否写成 completed。

**工程映射**：Verifier 负责检查产出文件、附件入库、execution_log/result_summary/task_summary 字数门槛、必要测试结果等。只有验证通过，才允许转到 `completed`。

## 四、建议优先落地的5个模式

虽然9类模式都重要，但从收益/成本比看，当前 OpenClaw 调度系统最值得优先应用的是以下5个：

### 1. 状态机
这是所有后续能力的支架。没有显式状态，就无法安全地加验证、重试和事件。

### 2. 规划-执行-反思
能显著提高复杂任务完成质量，尤其适合 T1/T2/T3 中的战略型任务。

### 3. 结果验证
这是防止“假完成”的核心机制，直接提升任务完成率的真实性。

### 4. 回滚重试
能减少僵尸任务和人工补救频率，提高系统稳定性。

### 5. 子任务拆分 + 多Agent协作
这两个模式最好联动落地。复杂任务拆分后，才能充分发挥多代理并发收益。

## 五、具体代码实现方案

### 1. 新增统一任务上下文对象
建议引入 `TaskContext` 数据结构，封装：任务元数据、状态、重试计数、质量分、证据列表、memory、事件日志、子任务列表。这样调度器内部不再传原始 dict，而是传可演化的上下文对象。

### 2. 引入显式状态机
将原先简单的任务流改为：

- `PENDING`：刚进入队列；
- `ANALYZING`：做复杂度分析、模式分类；
- `PLANNING`：生成计划；
- `READY`：计划完成，等待执行；
- `EXECUTING`：真正运行；
- `VERIFYING`：结果验证；
- `COMPLETED/FAILED/BLOCKED`：终态。

数据库层如果短期不方便增加枚举，也可以先把精细状态保留在执行上下文和日志里，而数据库仍使用兼容状态字段。

### 3. 增加 PlannerExecutorReflector
建议实现一个协调器，将 plan / execute / reflect 串成内聚单元：

- `plan()` 输出结构化步骤和成功标准；
- `execute()` 生成交付物和执行证据；
- `reflect()` 检查执行遗漏，决定是否需要补救。

### 4. 引入 Verifier
Verifier 独立于执行者，至少检查：

- 输出目录是否存在；
- 必要文件是否生成；
- execution_log 是否 >= 200 字；
- result_summary 是否 >= 50 字；
- task_summary 是否 >= 50 字；
- 是否已写入 attachments 表；
- 若有 benchmark，要检查测试结果是否存在。

### 5. 引入 RetryController
统一管理重试预算与回滚策略。建议：

- 执行失败：`EXECUTING -> READY`；
- 验证失败：`VERIFYING -> PLANNING` 或 `READY`；
- 连续2次失败：转 `BLOCKED`；
- 每次重试写事件日志与 memory。

### 6. 增加 EventBus
短期先做内存队列即可，用于发布任务生命周期事件；中期可升级到文件或 Redis。它的作用不是“炫技”，而是让监控、告警、补偿逻辑与主调度逻辑解耦。

## 六、关键代码片段说明

本次已经在 `output/task-1965/openclaw_agentic_scheduler_prototype_2026-04-25.py` 中给出一个轻量原型，包含：

- `TaskState`：显式状态枚举；
- `TaskContext`：统一任务上下文；
- `PatternAnalyzer`：模式识别与拆解入口；
- `PlannerExecutorReflector`：规划-执行-反思主循环；
- `Verifier`：独立验证器；
- `RetryController`：失败恢复；
- `MemoryStore`：工作记忆；
- `EventBus`：事件驱动通道；
- `AgenticScheduler`：统一编排门面。

这个实现的价值不在于替代现有全部代码，而在于作为一个低风险“增强层”插入现有调度系统。实际接入时，推荐先替换 `scheduler/analyzer.py` 的返回结构，把 profile、状态、验证要求一起带回；再逐步把 `scheduler/scheduler.py` 的 `launch_task()` 改成通过统一 context 流转。

## 七、性能对比测试设计

为了避免只写概念，本次补充了一个可运行基准脚本 `output/task-1965/benchmark_agentic_scheduler_2026-04-25.py`。测试方法如下：

1. 构造 30 个混合复杂度任务；
2. 基线组模拟当前“简单规则 + 无显式验证/恢复”模式；
3. Agentic 组使用新增原型的分类、规划、反思、验证闭环；
4. 比较完成率、平均执行时间、错误率三项指标。

## 八、测试结果与解读

本次运行结果如下：

- Baseline completion_rate：0.733
- Agentic completion_rate：1.000
- Delta：+0.267
- Baseline avg_time_ms：144.67
- Agentic avg_time_ms：120.01
- Delta：-24.66ms
- Baseline error_rate：0.267
- Agentic error_rate：0.000
- Delta：-0.267

这些结果来自受控模拟测试，不应被表述为“线上生产真实性能”，但它们已经说明一个方向：当任务被明确分类、计划化执行并在结束前验证，系统的错误率会显著下降，而且平均执行时间未必增加，甚至可能下降，因为减少了返工与模糊执行。

## 九、推荐落地路线图

### 第一阶段：最小可用增强
- 保留现有数据库结构和调度脚本；
- 增加 `TaskContext`、`TaskState`、`Verifier`；
- 在完成前增加字数与附件校验；
- 对高复杂任务启用三段式拆解。

### 第二阶段：主调度器升级
- 将 `scheduler/scheduler.py` 改为状态驱动；
- 将 `skills/kanban-sync/` 中已有成熟组件抽取到统一模块；
- 用事件流替代部分纯轮询逻辑。

### 第三阶段：多角色协同
- 为 research / build / verify 提供角色模板；
- 根据任务类型动态选择不同子代理提示词；
- 对跨文件、跨系统任务采用父任务+子任务方式运行。

### 第四阶段：线上观测与策略优化
- 记录各状态停留时长；
- 记录失败原因分布；
- 统计重试成功率；
- 基于历史数据动态调整拆解阈值与优先级模型。

## 十、结论

OpenClaw 当前调度系统已经具备“自动化”的基础，但离“agentic”还有一层关键升级：把任务执行从隐式脚本流程提升为显式、可恢复、可验证的工作流。以9类 Agentic Workflow 模式为框架，最值得优先落地的是状态机、规划-执行-反思、结果验证、回滚重试以及子任务拆分/多Agent协作。这样改造的收益不是抽象上的先进，而是非常具体：减少僵尸任务、提高真实完成率、让复杂任务执行更稳、让调度器具备更强的可维护性和可演进性。

因此，建议本次任务之后立即推进一个“低风险增强版”接入：先把验证器、状态机和任务上下文插入现有调度路径，再逐步吸收 `skills/kanban-sync/` 中已有的多代理原型能力，最终形成统一的 OpenClaw agentic scheduler runtime。

# 自改进Prompt生成模板库

## 目录
1. [复盘分析类模板](#1-复盘分析类模板)
2. [错误修正类模板](#2-错误修正类模板)
3. [知识增强类模板](#3-知识增强类模板)
4. [流程优化类模板](#4-流程优化类模板)
5. [Prompt迭代类模板](#5-prompt迭代类模板)
6. [模板使用指南](#6-模板使用指南)

---

## 1. 复盘分析类模板

### 模板1.1: 执行轨迹深度复盘模板
**适用场景**: 子代理任务执行完成后，进行系统性复盘分析

```markdown
## 执行轨迹深度复盘

### 任务基本信息
- 任务ID: {{task_id}}
- 代理类型: {{agent_type}}
- 执行时间: {{execution_time}}
- 任务状态: {{task_status}}
- 总耗时: {{total_duration}}ms
- 模型使用: {{model_used}}

### 执行过程回顾
{% for step in execution_steps %}
#### 步骤 {{step.index}}: {{step.type}}
- 耗时: {{step.duration}}ms
- 内容摘要: {{step.content_summary}}
- 问题标记: {% if step.is_error %}⚠️ 有错误{% else %}✅ 正常{% endif %}
{% if step.is_error %}
- 错误信息: {{step.error_message}}
{% endif %}
{% endfor %}

### 关键问题识别

1. **错误类型分析**
   - 错误类别: {{error_category}}
   - 错误描述: {{error_description}}
   - 发生位置: {{error_location}}
   - 影响范围: {{error_impact}}

2. **根因分析**
   - 直接原因: {{direct_cause}}
   - 根本原因: {{root_cause}}
   - 触发条件: {{trigger_condition}}

3. **执行效率分析**
   - 瓶颈步骤: {{bottleneck_step}}
   - 耗时占比: {{time_percentage}}%
   - 优化空间: {{optimization_potential}}

### 改进建议生成

【针对错误问题的改进】
问题: {{specific_problem}}
→ 短期修复方案: {{short_term_fix}}
→ 长期预防方案: {{long_term_prevention}}
→ 相关知识补充: {{knowledge_gaps}}

【针对流程效率的改进】
当前流程: {{current_flow}}
→ 优化后流程: {{optimized_flow}}
→ 预期收益: {{expected_benefit}}
→ 实施优先级: {{priority_level}}

### 能力沉淀清单

1. **新增知识点**
   - {{knowledge_point_1}}
   - {{knowledge_point_2}}

2. **新增最佳实践**
   - {{best_practice_1}}
   - {{best_practice_2}}

3. **需要更新的Prompt模板**
   - {{template_name_1}}: {{update_reason}}
   - {{template_name_2}}: {{update_reason}}

### 复盘结论
- 本次执行得分: {{score}}/100
- 核心经验教训: {{key_lessons}}
- 后续行动计划: {{action_items}}
```

---

### 模板1.2: 失败案例归因分析模板
**适用场景**: 针对失败任务进行深度归因分析

```markdown
## 失败案例归因分析报告

### 案例基本信息
- 轨迹UUID: {{trace_uuid}}
- 任务类型: {{task_type}}
- 失败时间: {{failure_time}}
- 代理版本: {{agent_version}}

### 错误分类与置信度
- 主错误类型: {{primary_error_type}}
- 置信度: {{confidence}}%
- 次错误类型: {{secondary_error_types}}

### 证据链分析

【直接证据】
{% for evidence in direct_evidence %}
- {{evidence}}
{% endfor %}

【间接证据】
{% for evidence in indirect_evidence %}
- {{evidence}}
{% endfor %}

【上下文背景】
- 前置条件: {{preconditions}}
- 环境信息: {{environment_info}}
- 相关历史: {{related_history}}

### 失败影响链
触发原因 → 中间过程 → 最终失败
1. {{cause_step_1}}
2. {{cause_step_2}}
3. {{cause_step_3}}

### 同类历史案例对比
- 相似案例数量: {{similar_case_count}}
- 历史解决方案: {{historical_solutions}}
- 复发率: {{recurrence_rate}}%

### 归因结论
- 责任归因: {{attribution}} [Prompt问题|工具问题|知识缺失|模型限制]
- 可预防性: {{preventable}} [完全可预防|部分可预防|难以预防]
- 改进成本: {{improvement_cost}} [低|中|高]

### 改进方案
1. 立即修复: {{immediate_fix}}
2. 中期优化: {{medium_term_optimization}}
3. 长期建设: {{long_term_construction}}
```

---

## 2. 错误修正类模板

### 模板2.1: 幻觉型错误修正模板
**适用场景**: 模型编造不存在的事实、文件、API等

```markdown
## 幻觉型错误修正与预防

### 幻觉模式识别
- 幻觉类型: {{hallucination_type}} [文件路径|API|命令|参数|事实]
- 具体表现: {{specific_manifestation}}
- 触发场景: {{trigger_scenario}}

### 本次幻觉分析
编造内容: {{fabricated_content}}
真实情况验证: {{actual_situation}}
造成影响: {{impact}}

### 修正后的执行方案

【事实验证流程】
> 在作出任何假设前，必须先验证事实:

1. ✅ 文件/目录存在性验证
```bash
# 执行前先检查
ls {{path}} 2>/dev/null || echo "PATH_NOT_EXIST"
```

2. ✅ API/函数存在性验证
```python
# 先检查模块和方法
import {{module}}
print(dir({{module}}))  # 查看可用方法
```

3. ✅ 命令可用性验证
```bash
which {{command}} || echo "COMMAND_NOT_FOUND"
```

### 预防型Prompt注入

```
【重要提醒】在执行任何操作前：
1. 不要假设文件存在 → 先用ls/read验证
2. 不要假设API存在 → 先查文档或用dir()
3. 不要假设命令可用 → 先用which验证
4. 遇到不确定的情况 → 调用web_fetch查阅资料

记住：宁可不做，不要做错！验证 > 假设。
```

### 知识库更新条目
> 需要添加到系统知识中的内容：
```
{{knowledge_category}}:
- {{knowledge_entry_1}}
- {{knowledge_entry_2}}
```
```

---

### 模板2.2: 工具使用错误修正模板
**适用场景**: 参数错误、格式错误、调用方式错误等

```markdown
## 工具使用错误修正规范

### 错误类型详情
- 工具名称: {{tool_name}}
- 错误类型: {{error_type}} [参数缺失|参数错误|格式错误|调用顺序错误]
- 错误描述: {{error_description}}

### 正确使用规范回顾

【{{tool_name}} 工具完整参数】
```
{{tool_documentation}}
```

### 修正后的调用示例

**错误写法:**
```
{{incorrect_usage}}
```

**正确写法:**
```
{{correct_usage}}
```

**差异说明:**
- {{difference_1}}
- {{difference_2}}

### 参数校验逻辑

```python
# 工具调用前自动校验
def validate_{{tool_name}}_params(params):
    required_fields = {{required_fields}}
    for field in required_fields:
        if field not in params:
            raise ValueError(f"缺少必填参数: {field}")
    
    # 格式校验
    if 'path' in params:
        params['path'] = os.path.expanduser(params['path'])
    
    return params
```

### Tool调用Prompt优化

```
【{{tool_name}} 使用规范】
使用前请确认：
1. 必填参数: {{required_params}}
2. 可选参数: {{optional_params}}
3. 参数格式: {{param_format}}
4. 返回格式: {{return_format}}

常见错误：
{% for error in common_errors %}
- ❌ {{error}}
{% endfor %}
```

### 相关Prompt模板更新列表
- {{affected_template_1}}
- {{affected_template_2}}
```

---

### 模板2.3: 知识缺失型错误修正模板
**适用场景**: 权限、API、领域知识等缺失

```markdown
## 知识缺失补充与沉淀

### 缺失知识分类
- 知识类别: {{knowledge_category}} [权限|API|领域|环境]
- 缺失程度: {{missing_level}} [完全缺失|部分缺失|理解错误]

### 本次缺失知识点
1. **知识点名称**: {{knowledge_name}}
   - 具体内容: {{detailed_content}}
   - 获取来源: {{source}}
   - 应用场景: {{application_scenarios}}

### 知识沉淀条目

#### 知识库新增条目
```
---
category: {{knowledge_category}}
keyword: {{keywords}}
content: |
  {{knowledge_content}}
example: |
  {{usage_example}}
---
```

### 触发式知识提醒

```
【执行前知识检查】
当任务涉及以下场景时：
- {{trigger_scenario_1}}
- {{trigger_scenario_2}}

自动触发知识提醒：
> {{knowledge_reminder_content}}

需要时自动调用: {{related_tool}}
```

### 知识获取流程优化

**遇到知识缺口时的标准处理流程：**
1. 🔍 先查本地知识库（记忆搜索）
2. 🌐 调用web_search搜索相关信息
3. 📚 调用web_fetch读取官方文档
4. ❓ 仍不确定时，暂停执行询问用户

**知识获取Prompt模板:**
```
我需要了解以下信息才能继续：
主题: {{topic}}
具体问题:
1. {{question_1}}
2. {{question_2}}

请调用web_search搜索相关信息，然后整理成要点形式输出。
```
```

---

## 3. 知识增强类模板

### 模板3.1: 成功案例抽象模板
**适用场景**: 从成功执行案例中提取可复用知识

```markdown
## 成功案例知识抽象

### 案例基本信息
- 任务类型: {{task_type}}
- 成功关键因素: {{success_factors}}
- 可复用程度: {{reusability_level}}

### 核心成功模式提取

【关键决策点】
{% for decision in key_decisions %}
- {{decision.point}} → {{decision.outcome}}
{% endfor %}

【工具组合模式】
```
工具调用序列: {{tool_sequence}}
组合方式说明: {{combination_description}}
适用场景: {{applicable_scenarios}}
```

【Prompt有效句式】
```
{{effective_prompt_snippet}}
```
> 为什么有效: {{why_effective}}
> 适用任务类型: {{for_task_types}}

### 可复用组件抽象

#### 组件名称: {{component_name}}
```
{{component_content}}
```
- 适用场景: {{use_cases}}
- 前置条件: {{preconditions}}
- 预期效果: {{expected_effect}}

### 任务模式识别
- 模式名称: {{pattern_name}}
- 模式特征: {{pattern_features}}
- 解决方案模板: {{solution_template}}
- 注意事项: {{considerations}}

### 纳入最佳实践库
> 此案例提炼内容将作为以下最佳实践保存：
```
实践ID: BP-{{bp_id}}
类别: {{category}}
适用: {{applicability}}
内容:
  {{best_practice_content}}
```
```

---

### 模板3.2: 任务通用化抽象模板
**适用场景**: 将具体任务方案抽象为可复用模板

```markdown
## 任务通用化抽象报告

### 原始任务信息
- 具体任务: {{specific_task}}
- 任务领域: {{task_domain}}

### 通用化过程

【变量提取】
原始中的具体值 → 抽象为变量
- {{value_1}} → {{variable_1}}
- {{value_2}} → {{variable_2}}

【不变部分识别】
这些部分在同类任务中保持相同：
- {{invariant_part_1}}
- {{invariant_part_2}}

### 通用模板生成

```markdown
## {{task_category}} 任务通用模板

### 任务描述模板
{{generalized_task_description}}

### 输入参数
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
{% for param in params %}
| {{param.name}} | {{param.type}} | {{param.required}} | {{param.description}} |
{% endfor %}

### 标准执行流程
{% for step in standard_steps %}
{{step.index}}. {{step.description}}
   工具调用: {{step.tool}}
   判断条件: {{step.condition}}
{% endfor %}

### 输出格式要求
{{output_format}}

### 常见问题与处理
{% for problem in common_problems %}
- **问题**: {{problem.description}}
  **处理**: {{problem.solution}}
{% endfor %}
```

### 模板质量评估
- 覆盖场景数量: {{coverage_count}}
- 平均节省工作量: {{work_saving}}%
- 模板可靠度: {{reliability}}%
```

---

## 4. 流程优化类模板

### 模板4.1: 任务拆解优化模板
**适用场景**: 优化子代理任务拆解策略

```markdown
## 任务拆解策略优化

### 原拆解方案分析
- 拆解数量: {{original_count}}
- 并行度: {{original_parallelism}}
- 依赖关系: {{original_dependencies}}
- 实际耗时: {{actual_duration}}

### 存在的问题
1. 颗粒度问题: {{granularity_issue}}
2. 依赖问题: {{dependency_issue}}
3. 并行问题: {{parallelism_issue}}
4. 边界问题: {{boundary_issue}}

### 优化后拆解方案

【拆解原则】
- 单个任务规模: {{task_size_guideline}}
- 任务间耦合度: {{coupling_guideline}}
- 可并行化优先: {{parallelization_priority}}

【新拆解方案】
{% for task in optimized_tasks %}
#### 任务{{task.id}}: {{task.name}}
- 职责范围: {{task.scope}}
- 输入依赖: {{task.inputs}}
- 输出产物: {{task.outputs}}
- 预估耗时: {{task.estimate}}
- 可并行: {{task.parallelizable}}
{% endfor %}

【依赖关系图】
```mermaid
graph TD
{% for dep in dependencies %}
    {{dep.from}} --> {{dep.to}}
{% endfor %}
```

### 拆解规则更新
> 新增到拆解知识库的规则：

```
规则ID: RULE-{{rule_id}}
适用场景: {{applicable_scenario}}
内容:
  {{rule_content}}
正反例:
  ✅ 正确: {{positive_example}}
  ❌ 错误: {{negative_example}}
```
```

---

## 5. Prompt迭代类模板

### 模板5.1: Prompt A/B测试分析模板

```markdown
## Prompt A/B测试分析报告

### 测试基本信息
- 测试ID: {{test_id}}
- 测试目标: {{test_goal}}
- 样本数量: {{sample_size}}
- 测试周期: {{test_period}}

### 两组Prompt对比

【Prompt A (对照组)】
```
{{prompt_a_content}}
```

【Prompt B (实验组)】
```
{{prompt_b_content}}
```

### 测试结果对比

| 指标 | Prompt A | Prompt B | 变化 | 统计显著性 |
|------|----------|----------|------|------------|
| 成功率 | {{a_success}}% | {{b_success}}% | {{success_change}} | {{significance}} |
| 平均耗时 | {{a_time}}ms | {{b_time}}ms | {{time_change}} | |
| Token消耗 | {{a_tokens}} | {{b_tokens}} | {{token_change}} | |
| 用户满意度 | {{a_satisfaction}} | {{b_satisfaction}} | {{satisfaction_change}} | |

### 效果分析

【Prompt B优势】
{% for advantage in b_advantages %}
- {{advantage}}
{% endfor %}

【Prompt B劣势】
{% for disadvantage in b_disadvantages %}
- {{disadvantage}}
{% endfor %}

### 胜出者决定
- ✅ 胜出Prompt: {{winner}}
- 置信度: {{confidence}}%
- 推荐全面推广: {{recommend_rollout}}

### 迭代建议
如果继续优化，建议在以下方面改进：
1. {{suggestion_1}}
2. {{suggestion_2}}

### 全面推广计划
- 推广范围: {{rollout_scope}}
- 预计收益: {{expected_gain}}
- 回滚方案: {{rollback_plan}}
```

---

## 6. 模板使用指南

### 6.1 模板选择决策树

```
开始复盘
  ↓
任务成功了吗?
  ├─ 是 → 使用【模板3.1 成功案例抽象】
  │        ↓
  │      是否可以通用化?
  │        ├─ 是 → 追加【模板3.2 任务通用化抽象】
  │        └─ 否 → 完成
  │
  └─ 否 → 先使用【模板1.2 失败案例归因分析】
           ↓
         确定错误类型了吗?
           ├─ 幻觉型 → 使用【模板2.1 幻觉型错误修正】
           ├─ 工具使用错误 → 使用【模板2.2 工具使用错误修正】
           ├─ 知识缺失型 → 使用【模板2.3 知识缺失型错误修正】
           └─ 流程问题 → 使用【模板4.x 流程优化类】
```

### 6.2 使用规范

1. **变量替换**: 所有 `{{variable}}` 必须替换为实际内容，不得留空
2. **可选部分**: 标记为可选的部分，如无内容应删除，不要留占位符
3. **质量要求**: 生成内容必须具体可执行，避免空泛描述
4. **关联更新**: 生成改进内容后，必须同步更新相关Prompt模板库

### 6.3 模板版本管理

- 每个模板有独立版本号，格式: `v主版本.次版本`
- 重大变更更新主版本号，小幅优化更新次版本号
- 所有变更必须记录变更日志，说明修改原因和效果

---

*模板库版本: v1.0 | 更新日期: 2026-04-25 | 模板总数: 8个*

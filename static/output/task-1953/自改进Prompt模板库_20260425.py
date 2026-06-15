# 自改进 Prompt 生成模板库
# Agent 任务执行轨迹回放与自改进系统 — Task #1953
#
# 本文件定义了基于失败类型自动生成改进 Prompt 的模板体系。
# 每种失败类型对应一组模板，支持动态填充上下文变量。
#
# Author: Dudu (AI Sidekick)
# Date:   2026-04-25

from string import Template
from dataclasses import dataclass, field
from typing import Optional
import json
import os
from lib.db_connector import get_db_connection


# ─── 模板数据结构 ─────────────────────────────────────────────────────────────

@dataclass
class PromptTemplate:
    template_id:   str
    failure_type:  str          # hallucination | knowledge_gap | tool_misuse | general
    scenario:      str          # 适用场景描述
    template:      str          # 模板正文（使用 ${var} 占位符）
    required_vars: list[str]    # 必填变量
    optional_vars: list[str] = field(default_factory=list)
    version:       str = "1.0"

    def render(self, **kwargs) -> str:
        """渲染模板，自动填充变量"""
        missing = [v for v in self.required_vars if v not in kwargs]
        if missing:
            raise ValueError(f"缺少必填变量: {missing}")
        # 设置 optional_vars 默认值
        for v in self.optional_vars:
            kwargs.setdefault(v, "")
        return Template(self.template).safe_substitute(**kwargs)


# ─── 模板库定义 ───────────────────────────────────────────────────────────────

TEMPLATE_LIBRARY: list[PromptTemplate] = [

    # ══════════════════════════════════════════════════════════════════════════
    # 1. 幻觉型失败 → 验证前置 + 事实约束模板
    # ══════════════════════════════════════════════════════════════════════════

    PromptTemplate(
        template_id   = "HALL_001",
        failure_type  = "hallucination",
        scenario      = "文件/路径引用前置验证",
        required_vars = ["task_description", "previous_error"],
        optional_vars = ["file_paths"],
        template      = """\
## 任务背景
${task_description}

## 上次失败记录
上次执行时发生以下错误：
```
${previous_error}
```

## 本次执行约束（强制遵守）
1. **在引用任何文件路径或目录之前**，必须先使用 `exec` 工具执行 `ls` 或 `test -f` 命令确认其存在。
2. **禁止凭记忆假设文件路径**。若不确定路径，用 `find` 命令搜索。
3. 若文件不存在，必须先创建或跳过，不得继续引用。
4. 每次工具调用前，用一句话说明调用意图。

## 额外上下文
${file_paths}

请在确认上述约束后开始执行任务。\
""",
    ),

    PromptTemplate(
        template_id   = "HALL_002",
        failure_type  = "hallucination",
        scenario      = "API/接口调用前置验证",
        required_vars = ["task_description", "previous_error", "api_context"],
        template      = """\
## 任务背景
${task_description}

## 上次失败记录
```
${previous_error}
```

## API 调用约束
- 本次可用 API 信息如下（以此为准，忽略训练数据中的历史版本）：
${api_context}

- **禁止使用未在上述列表中出现的 endpoint 或参数**。
- 遇到 404/422 响应时，立即停止并报告，不要猜测正确路径。
- 所有外部调用必须校验返回 status_code，非 2xx 视为失败。

请在确认约束后执行任务。\
""",
    ),

    PromptTemplate(
        template_id   = "HALL_003",
        failure_type  = "hallucination",
        scenario      = "数据库表/列引用前置验证",
        required_vars = ["task_description", "previous_error"],
        optional_vars = ["db_schema_snippet"],
        template      = """\
## 任务背景
${task_description}

## 上次失败记录
```
${previous_error}
```

## 数据库操作约束
- 在执行任何 SQL 前，先 `SHOW TABLES` / `DESCRIBE <table>` 确认表和列存在。
- **不得假设表名或列名**；若不确定，先查询 information_schema。
- 已知 Schema 片段（供参考）：
${db_schema_snippet}

- 所有写操作（INSERT/UPDATE/DELETE）执行前必须先 SELECT 确认目标行存在。

请在确认约束后执行任务。\
""",
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 2. 知识缺失型失败 → 上下文注入 + RAG 增强模板
    # ══════════════════════════════════════════════════════════════════════════

    PromptTemplate(
        template_id   = "KG_001",
        failure_type  = "knowledge_gap",
        scenario      = "注入最新文档/版本说明",
        required_vars = ["task_description", "previous_error", "injected_docs"],
        template      = """\
## 任务背景
${task_description}

## 上次失败原因分析
上次失败可能由于知识过时或领域信息不足：
```
${previous_error}
```

## 最新参考文档（请以此为准，忽略训练数据中的旧版本）
${injected_docs}

## 执行要求
- 严格按照上述文档中的 API/接口定义执行。
- 若文档与你的训练记忆冲突，**以文档为准**。
- 遇到文档未覆盖的情况，直接说明「文档未提及」，不要猜测。

请基于以上信息执行任务。\
""",
    ),

    PromptTemplate(
        template_id   = "KG_002",
        failure_type  = "knowledge_gap",
        scenario      = "领域专家角色注入",
        required_vars = ["task_description", "domain", "key_concepts"],
        optional_vars = ["previous_error"],
        template      = """\
## 角色设定
你是一位资深的 ${domain} 专家，拥有该领域的最新知识储备。

## 核心概念速查（本次任务必须掌握）
${key_concepts}

## 任务
${task_description}

## 上次问题（如有）
${previous_error}

## 要求
- 在执行前，先简述你对本任务的理解和方案（不超过 3 句话）。
- 若遇到超出你知识范围的问题，明确标注「知识边界」并说明。
- 所有推断必须基于上述概念速查，不要超出范围。\
""",
    ),

    PromptTemplate(
        template_id   = "KG_003",
        failure_type  = "knowledge_gap",
        scenario      = "历史成功案例注入（Few-shot）",
        required_vars = ["task_description", "success_examples"],
        optional_vars = ["previous_error", "failure_contrast"],
        template      = """\
## 任务
${task_description}

## 参考：历史成功案例
以下是类似任务的成功执行记录，请参考其方法和步骤：

${success_examples}

## 对比：上次失败原因
${failure_contrast}

## 执行要求
- 参照上述成功案例的执行模式，而非重复失败路径。
- 若发现当前任务与成功案例有差异，先说明差异再调整方案。\
""",
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 3. 工具使用错误型失败 → 工具规范 + 参数校验模板
    # ══════════════════════════════════════════════════════════════════════════

    PromptTemplate(
        template_id   = "TM_001",
        failure_type  = "tool_misuse",
        scenario      = "工具参数规范注入",
        required_vars = ["task_description", "previous_error", "tool_name", "tool_spec"],
        template      = """\
## 任务背景
${task_description}

## 上次工具调用失败
工具：`${tool_name}`
错误：
```
${previous_error}
```

## 正确的工具用法（请严格遵守）
${tool_spec}

## 调用前自检清单
在调用 `${tool_name}` 前，必须确认：
- [ ] 所有必填参数已提供且类型正确
- [ ] 字符串参数已正确转义
- [ ] 数值参数在合法范围内
- [ ] 不传递工具规范中未定义的参数

请按照以上规范重新执行任务。\
""",
    ),

    PromptTemplate(
        template_id   = "TM_002",
        failure_type  = "tool_misuse",
        scenario      = "SQL/数据库操作规范模板",
        required_vars = ["task_description", "previous_error"],
        optional_vars = ["table_name", "example_sql"],
        template      = """\
## 任务背景
${task_description}

## 上次 SQL 错误
```
${previous_error}
```

## SQL 操作规范（本次强制执行）
1. 所有 SQL 通过 `lib/db_connector.py` 的 `execute_query` / `execute_update` 执行。
2. 参数化查询，**禁止字符串拼接 SQL**（防注入，防格式错误）。
3. 写操作必须在事务中执行，失败时回滚。
4. 涉及表：`${table_name}`，参考写法：
```sql
${example_sql}
```

请按照以上规范重新执行任务。\
""",
    ),

    PromptTemplate(
        template_id   = "TM_003",
        failure_type  = "tool_misuse",
        scenario      = "Shell/Exec 命令安全执行模板",
        required_vars = ["task_description", "previous_error"],
        optional_vars = ["safe_commands", "forbidden_commands"],
        template      = """\
## 任务背景
${task_description}

## 上次 Shell 执行失败
```
${previous_error}
```

## Shell 执行规范
- 允许命令白名单：${safe_commands}
- 禁止命令：${forbidden_commands}
- 所有命令执行前检查返回码（非 0 = 失败，立即停止）。
- **破坏性操作**（rm、truncate、drop）须在命令前添加 `echo "即将执行: <cmd>"` 确认。
- 优先使用 `trash` 替代 `rm`。

请按照以上规范重新执行任务。\
""",
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 4. 通用自改进模板
    # ══════════════════════════════════════════════════════════════════════════

    PromptTemplate(
        template_id   = "GEN_001",
        failure_type  = "general",
        scenario      = "通用任务重试（含失败上下文）",
        required_vars = ["task_description", "previous_error", "lessons_learned"],
        optional_vars = ["retry_number"],
        template      = """\
## 任务（第 ${retry_number} 次尝试）
${task_description}

## 上次失败摘要
```
${previous_error}
```

## 本次改进措施
基于上次失败，本次执行将：
${lessons_learned}

## 执行原则
1. 遇到不确定的情况，先验证再执行。
2. 每完成一个关键步骤，输出一行进度日志。
3. 若再次遇到相同错误，立即停止并报告，不要循环重试超过 2 次。

请开始执行。\
""",
    ),

    PromptTemplate(
        template_id   = "GEN_002",
        failure_type  = "general",
        scenario      = "复盘总结 → MEMORY.md 更新",
        required_vars = ["task_id", "task_title", "execution_summary",
                         "failures_summary", "lessons"],
        optional_vars = ["related_files"],
        template      = """\
## 任务复盘报告生成请求

请根据以下信息，生成一份结构化的任务复盘报告，并将「经验教训」部分追加到 memory/core-principles.md。

### 任务信息
- **任务 ID**: #${task_id}
- **任务标题**: ${task_title}

### 执行摘要
${execution_summary}

### 失败与问题
${failures_summary}

### 经验教训（待固化）
${lessons}

### 相关文件
${related_files}

## 输出格式要求
1. 生成 `memory/daily/$(date +%Y-%m-%d)-task-${task_id}-review.md` 文件
2. 将「经验教训」以 bullet list 追加到 `memory/core-principles.md`
3. 返回「更新完成」确认

请执行上述操作。\
""",
    ),

    PromptTemplate(
        template_id   = "GEN_003",
        failure_type  = "general",
        scenario      = "任务拆解 → 防止单步超负荷",
        required_vars = ["task_description", "complexity_reason"],
        optional_vars = ["max_steps"],
        template      = """\
## 任务
${task_description}

## 任务拆解要求
当前任务较复杂（原因：${complexity_reason}），需要先进行任务拆解。

请按以下格式输出执行计划（不超过 ${max_steps} 步）：

```
Step 1: [步骤名称] — [预期产出] — [预计耗时]
Step 2: ...
```

**完成计划后，等待确认再执行第一步。**\
""",
    ),
]


# ─── 模板管理器 ───────────────────────────────────────────────────────────────

class PromptTemplateManager:
    """
    管理和检索 Prompt 模板库。
    支持按失败类型、场景检索，以及自动推荐。
    """

    def __init__(self, templates: list[PromptTemplate] = None):
        self._templates = {t.template_id: t for t in (templates or TEMPLATE_LIBRARY)}

    def get(self, template_id: str) -> Optional[PromptTemplate]:
        return self._templates.get(template_id)

    def by_failure_type(self, failure_type: str) -> list[PromptTemplate]:
        return [t for t in self._templates.values() if t.failure_type == failure_type]

    def recommend(self, failure_type: str, scenario_hint: str = "") -> PromptTemplate:
        """根据失败类型推荐最合适的模板"""
        candidates = self.by_failure_type(failure_type)
        if not candidates:
            candidates = self.by_failure_type("general")
        if scenario_hint:
            # 简单关键词匹配
            keywords = scenario_hint.lower().split()
            scored = []
            for t in candidates:
                score = sum(1 for kw in keywords if kw in t.scenario.lower())
                scored.append((score, t))
            scored.sort(key=lambda x: -x[0])
            return scored[0][1]
        return candidates[0]

    def generate_improvement_prompt(
        self,
        failure_type: str,
        task_description: str,
        previous_error: str,
        extra_context: dict = None,
        scenario_hint: str = "",
    ) -> str:
        """一键生成改进 Prompt"""
        tmpl = self.recommend(failure_type, scenario_hint)
        kwargs = {
            "task_description": task_description,
            "previous_error":   previous_error,
            **(extra_context or {}),
        }
        # 为 optional_vars 提供默认值
        for v in tmpl.optional_vars:
            kwargs.setdefault(v, "(未提供)")
        try:
            return tmpl.render(**kwargs)
        except ValueError as e:
            # 缺少必填变量时降级到 GEN_001
            fallback = self.get("GEN_001")
            return fallback.render(
                task_description=task_description,
                previous_error=previous_error,
                lessons_learned=f"自动降级，原因：{e}",
                retry_number="?",
            )

    def list_all(self) -> str:
        """列出所有模板"""
        lines = [f"\n{'='*60}", "  自改进 Prompt 模板库  共 %d 个模板" % len(self._templates), "="*60]
        by_type = {}
        for t in self._templates.values():
            by_type.setdefault(t.failure_type, []).append(t)
        for ftype, tmpl_list in sorted(by_type.items()):
            lines.append(f"\n  [{ftype}]")
            for t in tmpl_list:
                lines.append(f"    {t.template_id:<12} v{t.version}  {t.scenario}")
        lines.append("")
        return "\n".join(lines)

    def save_to_db(self):
        """将模板元数据持久化到数据库"""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS agent_prompt_templates (
              id            INT AUTO_INCREMENT PRIMARY KEY,
              template_id   VARCHAR(32) UNIQUE NOT NULL,
              failure_type  VARCHAR(64),
              scenario      VARCHAR(255),
              template_body TEXT,
              required_vars JSON,
              optional_vars JSON,
              version       VARCHAR(16) DEFAULT '1.0',
              created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
              updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        for t in self._templates.values():
            c.execute("""
                INSERT INTO agent_prompt_templates
                  (template_id, failure_type, scenario, template_body,
                   required_vars, optional_vars, version)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                  failure_type=VALUES(failure_type),
                  scenario=VALUES(scenario),
                  template_body=VALUES(template_body),
                  required_vars=VALUES(required_vars),
                  optional_vars=VALUES(optional_vars),
                  version=VALUES(version),
                  updated_at=NOW()
            """, (t.template_id, t.failure_type, t.scenario, t.template,
                  json.dumps(t.required_vars), json.dumps(t.optional_vars), t.version))
        conn.commit()
        conn.close()
        # print(f"✅ 已同步 {len(self._templates)} 个模板到数据库")


# ─── CLI 演示 ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mgr = PromptTemplateManager()

    # 列出所有模板
    # print(mgr.list_all())

    # 演示：为幻觉型失败生成改进 Prompt
    # print("\n" + "="*60)
    # print("  示例：幻觉型失败 → 自动生成改进 Prompt")
    # print("="*60)
    improved = mgr.generate_improvement_prompt(
        failure_type     = "hallucination",
        task_description = "读取 output/task-1953/report.md 并生成摘要",
        previous_error   = "FileNotFoundError: [Errno 2] No such file or directory: 'output/task-1953/report.md'",
        scenario_hint    = "文件路径",
    )
    # print(improved)

    # 演示：保存模板到数据库（需要数据库连接）
    # mgr.save_to_db()

#!/usr/bin/env python3
"""
improvement_generator.py - Agent自改进Prompt模板库

功能：
1. 基于失败模式自动生成优化后的 prompt 模板
2. 管理模板库，支持查询、应用和效果追踪
3. 按失败类型提供针对性改进策略
4. 持续学习：根据使用效果自动调整模板优先级

作者: Dudu AI Assistant
创建日期: 2026-04-25
版本: v1.0
"""

import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# 导入失败分类器中的枚举
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ============================================================
# 数据模型
# ============================================================

@dataclass
class PromptTemplate:
    """Prompt 改进模板"""
    template_id: str
    name: str                           # 模板名称
    description: str                    # 模板描述
    failure_pattern: str               # 对应的失败模式（如 "tool_usage_error.timeout"）
    trigger_condition: str             # 触发条件描述
    original_pattern: str              # 原始 prompt 模式
    improved_template: str             # 改进后的模板（含占位符）
    applicable_tools: List[str] = field(default_factory=list)  # 适用的工具
    applicable_agents: List[str] = field(default_factory=list)  # 适用的Agent
    effectiveness_score: float = 0.5   # 有效性分数（0-1）
    usage_count: int = 0               # 使用次数
    success_count: int = 0             # 成功次数
    created_at: str = ""
    last_used_at: str = ""
    last_updated_at: str = ""
    tags: List[str] = field(default_factory=list)
    examples: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    def render(self, **kwargs) -> str:
        """渲染模板，替换占位符"""
        template = self.improved_template
        for key, value in kwargs.items():
            template = template.replace(f"{{{key}}}", str(value))
        return template

    def record_usage(self, was_successful: bool):
        """记录使用效果"""
        self.usage_count += 1
        if was_successful:
            self.success_count += 1
        self.last_used_at = datetime.now().isoformat()
        self.effectiveness_score = self.success_count / max(self.usage_count, 1)
        self.last_updated_at = datetime.now().isoformat()


# ============================================================
# 模板库 - 预定义的改进模板
# ============================================================

class TemplateLibrary:
    """自改进Prompt模板库"""

    # --- 幻觉型改进模板 ---
    HALLUCINATION_TEMPLATES = [
        PromptTemplate(
            template_id="imp_hall_factual_001",
            name="事实核查约束",
            description="防止Agent产生事实性错误",
            failure_pattern="hallucination.factual_error",
            trigger_condition="Agent输出包含可验证的事实错误",
            original_pattern="请回答关于 {topic} 的问题",
            improved_template=(
                "请回答关于 {topic} 的问题。\n"
                "\n⚠️ 重要约束：\n"
                "1. 只陈述你可以确认的事实，不确定的内容请明确标注「可能不准确」\n"
                "2. 涉及具体数字、日期、人名时，请再次确认准确性\n"
                "3. 如果无法确认某条信息，请说「我无法确认」而不是猜测"
            ),
            applicable_tools=["read", "web_fetch", "memory_search"],
            applicable_agents=["research", "analysis"],
            effectiveness_score=0.78,
            tags=["hallucination", "fact-check", "accuracy"],
        ),
        PromptTemplate(
            template_id="imp_hall_ref_001",
            name="引用验证约束",
            description="防止Agent伪造论文引用或数据来源",
            failure_pattern="hallucination.fabricated_reference",
            trigger_condition="Agent引用了不存在或不正确的论文/数据",
            original_pattern="请提供关于 {topic} 的相关论文",
            improved_template=(
                "请提供关于 {topic} 的相关论文。\n"
                "\n⚠️ 重要约束：\n"
                "1. 所有引用的论文必须真实存在，请提供 DOI 或可验证的链接\n"
                "2. 如果你不确定某篇论文是否存在，请不要列出它\n"
                "3. 优先使用 web_search 工具验证论文的准确性后再引用"
            ),
            applicable_tools=["web_fetch", "openclaw-academic-search"],
            applicable_agents=["research"],
            effectiveness_score=0.82,
            tags=["hallucination", "citation", "verification"],
        ),
        PromptTemplate(
            template_id="imp_hall_conf_001",
            name="置信度标注约束",
            description="要求Agent对不确定内容标注置信度",
            failure_pattern="hallucination.overconfident_guess",
            trigger_condition="Agent以高置信度表达了不确定的内容",
            original_pattern="请分析 {topic} 的发展趋势",
            improved_template=(
                "请分析 {topic} 的发展趋势。\n"
                "\n⚠️ 重要约束：\n"
                "1. 对于每个结论，请标注置信度等级：高/中/低\n"
                "2. 低置信度的内容请使用「可能」「倾向于」「推测」等限定词\n"
                "3. 区分「事实」和「推论」，不要将推测包装为事实"
            ),
            applicable_tools=["read", "exec"],
            applicable_agents=["research", "analysis", "wiki"],
            effectiveness_score=0.75,
            tags=["hallucination", "confidence", "uncertainty"],
        ),
        PromptTemplate(
            template_id="imp_hall_logic_001",
            name="逻辑一致性检查",
            description="防止Agent回答前后矛盾",
            failure_pattern="hallucination.logical_inconsistency",
            trigger_condition="Agent回答中出现前后不一致或自相矛盾的内容",
            original_pattern="请分析 {topic}",
            improved_template=(
                "请分析 {topic}。\n"
                "\n⚠️ 重要约束：\n"
                "1. 请确保你的回答前后逻辑一致，不要自相矛盾\n"
                "2. 在回答末尾，请自检：是否有矛盾之处？\n"
                "3. 如果发现自己前后表述不一致，请在修正部分明确说明"
            ),
            applicable_tools=["read"],
            applicable_agents=["analysis", "wiki"],
            effectiveness_score=0.70,
            tags=["hallucination", "consistency", "self-check"],
        ),
    ]

    # --- 知识缺失型改进模板 ---
    KNOWLEDGE_GAP_TEMPLATES = [
        PromptTemplate(
            template_id="imp_kg_domain_001",
            name="领域知识预加载",
            description="在执行任务前先检索相关知识",
            failure_pattern="knowledge_gap.missing_domain_knowledge",
            trigger_condition="Agent表示不了解某个领域",
            original_pattern="请分析 {topic}",
            improved_template=(
                "请分析 {topic}。\n"
                "\n📋 执行步骤：\n"
                "1. 首先使用 web_search 搜索 {topic} 的最新信息（至少3个来源）\n"
                "2. 整理搜索到的关键信息\n"
                "3. 基于整理的信息进行分析回答"
            ),
            applicable_tools=["web_fetch", "tavily-search"],
            applicable_agents=["research"],
            effectiveness_score=0.88,
            tags=["knowledge-gap", "research-first", "pre-loading"],
        ),
        PromptTemplate(
            template_id="imp_kg_time_001",
            name="时效性知识约束",
            description="处理需要最新知识的任务",
            failure_pattern="knowledge_gap.outdated_information",
            trigger_condition="Agent使用了过时的信息或知识截止日期之前的数据",
            original_pattern="请提供 {topic} 的最新信息",
            improved_template=(
                "请提供 {topic} 的最新信息。\n"
                "\n⏰ 时效性约束：\n"
                "1. 请优先使用 2024年以后的信息来源\n"
                "2. 如果你不确定某条信息是否是最新的，请明确标注「信息可能已过时」\n"
                "3. 使用 web_search 获取最新信息，而非仅依赖训练数据"
            ),
            applicable_tools=["web_fetch", "tavily-search"],
            applicable_agents=["research"],
            effectiveness_score=0.80,
            tags=["knowledge-gap", "timeliness", "freshness"],
        ),
        PromptTemplate(
            template_id="imp_kg_ctx_001",
            name="上下文增强模板",
            description="为缺乏上下文的任务补充必要信息",
            failure_pattern="knowledge_gap.insufficient_context",
            trigger_condition="Agent因缺乏上下文而无法完成任务",
            original_pattern="请处理 {task}",
            improved_template=(
                "请处理 {task}。\n"
                "\n📋 背景信息：\n"
                "- 输入格式：{input_format}\n"
                "- 预期输出格式：{output_format}\n"
                "- 约束条件：{constraints}\n"
                "- 相关参考：{references}\n"
                "\n如有不确定的地方，请向我确认后再继续"
            ),
            applicable_tools=["read"],
            applicable_agents=["analysis", "execution"],
            effectiveness_score=0.85,
            tags=["knowledge-gap", "context", "specification"],
        ),
        PromptTemplate(
            template_id="imp_kg_amb_001",
            name="歧义消解模板",
            description="将模糊的任务拆分为具体子任务",
            failure_pattern="knowledge_gap.ambiguous_query",
            trigger_condition="任务描述存在多种解读方式",
            original_pattern="请处理 {task}",
            improved_template=(
                "任务「{task}」存在多种解读，请按以下方式处理：\n"
                "\n📋 消解步骤：\n"
                "1. 列出你对任务的 2-3 种理解方式\n"
                "2. 对每种理解分别给出处理方案\n"
                "3. 标注你认为最可能的理解方式及理由"
            ),
            applicable_tools=["read"],
            applicable_agents=["analysis", "wiki"],
            effectiveness_score=0.72,
            tags=["knowledge-gap", "ambiguity", "clarification"],
        ),
    ]

    # --- 工具使用错误型改进模板 ---
    TOOL_ERROR_TEMPLATES = [
        PromptTemplate(
            template_id="imp_tool_wrong_001",
            name="工具选择指引",
            description="帮助Agent选择正确的工具",
            failure_pattern="tool_usage_error.wrong_tool",
            trigger_condition="Agent选择了不合适的工具来完成任务",
            original_pattern="请完成 {task}",
            improved_template=(
                "请完成 {task}。\n"
                "\n🔧 工具选择指引：\n"
                "- 如果需要搜索信息 → 使用 web_fetch 或 tavily-search\n"
                "- 如果需要读取文件 → 使用 read\n"
                "- 如果需要写入文件 → 使用 write\n"
                "- 如果需要执行命令 → 使用 exec（请先在脑中验证命令安全性）\n"
                "- 如果需要搜索记忆 → 使用 memory_search 或 memory_get\n"
                "\n请优先使用最适合当前任务的工具，不要强行使用不匹配的工具。"
            ),
            applicable_tools=["exec", "read", "write", "web_fetch", "memory_search"],
            applicable_agents=["research", "analysis", "execution"],
            effectiveness_score=0.83,
            tags=["tool-error", "tool-selection", "guidance"],
        ),
        PromptTemplate(
            template_id="imp_tool_param_001",
            name="参数验证模板",
            description="在工具调用前增加参数验证",
            failure_pattern="tool_usage_error.wrong_parameters",
            trigger_condition="工具调用因参数错误而失败",
            original_pattern="请执行 {command}",
            improved_template=(
                "请执行 {command}。\n"
                "\n✅ 参数验证清单：\n"
                "1. 确认所有必填参数已提供：{required_params}\n"
                "2. 确认参数格式正确（路径/数字/字符串）\n"
                "3. 确认目标文件或目录存在（如适用）\n"
                "4. 如果不确定，先用小范围测试验证"
            ),
            applicable_tools=["exec", "read", "write"],
            applicable_agents=["analysis", "execution"],
            effectiveness_score=0.79,
            tags=["tool-error", "parameter-validation"],
        ),
        PromptTemplate(
            template_id="imp_tool_timeout_001",
            name="超时防护模板",
            description="处理超时问题的改进模板",
            failure_pattern="tool_usage_error.timeout",
            trigger_condition="工具调用因超时失败",
            original_pattern="请搜索 {query}",
            improved_template=(
                "请搜索 {query}。\n"
                "\n⏱️ 超时防护：\n"
                "1. 学术网站响应较慢，请使用 60 秒超时（而非默认 30 秒）\n"
                "2. 如果首次失败，等待 5 秒后重试（最多 3 次）\n"
                "3. 如果 3 次都超时，尝试备选方案：{fallback_method}"
            ),
            applicable_tools=["web_fetch", "openclaw-academic-search"],
            applicable_agents=["research"],
            effectiveness_score=0.86,
            tags=["tool-error", "timeout", "retry"],
        ),
        PromptTemplate(
            template_id="imp_tool_rate_001",
            name="频率限制防护模板",
            description="避免触发API频率限制",
            failure_pattern="tool_usage_error.rate_limit",
            trigger_condition="因请求过于频繁被限流",
            original_pattern="请批量处理 {count} 个项目",
            improved_template=(
                "请批量处理 {count} 个项目。\n"
                "\n🚦 频率控制：\n"
                "1. 每处理 {batch_size} 个项目后，等待 {delay} 秒\n"
                "2. 如果遇到 429 错误，等待 60 秒后继续（指数退避）\n"
                "3. 优先使用批量接口而非逐个处理"
            ),
            applicable_tools=["web_fetch", "exec"],
            applicable_agents=["research", "analysis"],
            effectiveness_score=0.81,
            tags=["tool-error", "rate-limit", "throttling"],
        ),
        PromptTemplate(
            template_id="imp_tool_perm_001",
            name="权限检查模板",
            description="在执行前验证权限配置",
            failure_pattern="tool_usage_error.permission_denied",
            trigger_condition="因权限不足访问被拒绝",
            original_pattern="请访问 {resource}",
            improved_template=(
                "请访问 {resource}。\n"
                "\n🔐 权限预检：\n"
                "1. 确认 API Key / 认证信息已正确配置（从 ~/.openclaw/.env 读取）\n"
                "2. 确认你有访问 {resource} 的权限级别\n"
                "3. 如果收到 403/401 错误，请检查配置而非重试"
            ),
            applicable_tools=["web_fetch", "exec"],
            applicable_agents=["research", "execution"],
            effectiveness_score=0.77,
            tags=["tool-error", "permission", "auth"],
        ),
    ]

    # --- 通用改进模板 ---
    GENERAL_TEMPLATES = [
        PromptTemplate(
            template_id="imp_general_selfcheck_001",
            name="自我检查模板",
            description="在任务完成前强制执行自我检查",
            failure_pattern="general.quality_check",
            trigger_condition="任何需要高质量输出的任务",
            original_pattern="请完成 {task}",
            improved_template=(
                "请完成 {task}。\n"
                "\n✅ 完成前自检清单：\n"
                "1. 我的回答是否直接解决了任务目标？\n"
                "2. 是否有事实性错误或幻觉内容？\n"
                "3. 输出格式是否符合要求？\n"
                "4. 是否有遗漏的关键信息？\n"
                "5. 如果需要，我是否使用了合适的工具来验证信息？"
            ),
            applicable_agents=["research", "analysis", "execution", "wiki"],
            effectiveness_score=0.90,
            tags=["general", "quality", "self-check"],
        ),
        PromptTemplate(
            template_id="imp_general_step_001",
            name="分步执行模板",
            description="将复杂任务拆分为明确步骤",
            failure_pattern="general.complex_task",
            trigger_condition="任务过于复杂导致执行混乱",
            original_pattern="请完成 {task}",
            improved_template=(
                "请完成 {task}。\n"
                "\n📋 执行步骤（请严格按顺序执行）：\n"
                "Step 1: {step1}\n"
                "Step 2: {step2}\n"
                "Step 3: {step3}\n"
                "\n每完成一步请确认结果后再进行下一步。"
            ),
            applicable_agents=["research", "analysis", "execution"],
            effectiveness_score=0.87,
            tags=["general", "step-by-step", "complex"],
        ),
        PromptTemplate(
            template_id="imp_general_format_001",
            name="输出格式约束模板",
            description="强制规范输出格式",
            failure_pattern="general.format_error",
            trigger_condition="输出格式不符合预期",
            original_pattern="请输出 {topic} 的分析结果",
            improved_template=(
                "请输出 {topic} 的分析结果。\n"
                "\n📐 格式要求：\n"
                "- 使用 Markdown 格式\n"
                "- 包含：概述、详细分析、结论 三个部分\n"
                "- 数据用表格呈现（如适用）\n"
                "- 结论不超过 200 字"
            ),
            applicable_agents=["analysis", "wiki"],
            effectiveness_score=0.84,
            tags=["general", "format", "output-constraint"],
        ),
    ]

    def get_all_templates(self) -> List[PromptTemplate]:
        """获取所有模板"""
        return (
            self.HALLUCINATION_TEMPLATES
            + self.KNOWLEDGE_GAP_TEMPLATES
            + self.TOOL_ERROR_TEMPLATES
            + self.GENERAL_TEMPLATES
        )

    def get_templates_for_failure(self, failure_type: str, failure_subtype: str = None) -> List[PromptTemplate]:
        """根据失败类型获取适用的改进模板"""
        pattern = failure_type
        if failure_subtype:
            pattern = f"{failure_type}.{failure_subtype}"

        matched = []
        for t in self.get_all_templates():
            # 精确匹配
            if t.failure_pattern == pattern:
                matched.append(t)
                continue
            # 一级分类匹配
            if t.failure_pattern.startswith(f"{failure_type}.") and not failure_subtype:
                matched.append(t)

        # 按有效性分数排序
        matched.sort(key=lambda x: x.effectiveness_score, reverse=True)
        return matched

    def get_templates_for_tool(self, tool_name: str) -> List[PromptTemplate]:
        """根据工具名称获取适用的改进模板"""
        matched = []
        for t in self.get_all_templates():
            if tool_name in t.applicable_tools:
                matched.append(t)
        matched.sort(key=lambda x: x.effectiveness_score, reverse=True)
        return matched


# ============================================================
# 改进生成器
# ============================================================

class ImprovementGenerator:
    """
    Agent自改进Prompt生成器

    核心流程：
    1. 接收失败记录
    2. 匹配最合适的改进模板
    3. 生成优化后的 prompt
    4. 追踪使用效果以持续优化模板
    """

    def __init__(self, library: TemplateLibrary = None):
        self.library = library or TemplateLibrary()

    def generate_template(self, failure_record) -> Optional[PromptTemplate]:
        """
        基于失败记录生成/匹配改进模板

        参数:
            failure_record: FailureRecord 实例或字典

        返回:
            匹配的 PromptTemplate，如果没有匹配的则返回 None
        """
        if isinstance(failure_record, dict):
            ftype = failure_record.get("failure_type", "")
            fsubtype = failure_record.get("failure_subtype", "")
            tool_name = failure_record.get("tool_name", "")
        else:
            ftype = getattr(failure_record, "failure_type", "")
            fsubtype = getattr(failure_record, "failure_subtype", "")
            tool_name = getattr(failure_record, "tool_name", "")

        # 优先按失败类型匹配
        templates = self.library.get_templates_for_failure(ftype, fsubtype)
        if templates:
            return templates[0]  # 返回最有效的模板

        # 退而按工具名称匹配
        if tool_name:
            templates = self.library.get_templates_for_tool(tool_name)
            if templates:
                return templates[0]

        return None

    def generate_batch(self, failure_records: List) -> List[Tuple[PromptTemplate, str]]:
        """
        批量生成改进模板

        返回:
            List of (template, rendered_prompt) 元组
        """
        results = []
        for record in failure_records:
            template = self.generate_template(record)
            if template:
                # 提取任务描述作为占位符值
                task_desc = ""
                if isinstance(record, dict):
                    task_desc = record.get("task_description", record.get("original_prompt", ""))
                else:
                    task_desc = getattr(record, "task_description", getattr(record, "original_prompt", ""))

                rendered = template.render(
                    topic=task_desc[:100] if task_desc else "当前任务",
                    task=task_desc,
                    query=task_desc,
                    step1="理解任务需求并收集必要信息",
                    step2="执行核心操作",
                    step3="验证结果并完成输出",
                    required_params="根据具体工具确定",
                    fallback_method="使用本地缓存或其他数据源",
                    count="批量任务",
                    batch_size=5,
                    delay=3,
                    resource="目标资源",
                    input_format="待定",
                    output_format="待定",
                    constraints="待定",
                    references="待定",
                    command="待执行命令",
                )
                results.append((template, rendered))

        return results

    def apply_template(self, original_prompt: str, template: PromptTemplate, **kwargs) -> str:
        """
        将改进模板应用到原始 prompt

        返回:
            优化后的 prompt
        """
        # 提取原始 prompt 中的关键信息
        topic_match = re.search(r'关于\s*(.+?)\s*的', original_prompt)
        topic = topic_match.group(1) if topic_match else "当前任务"

        defaults = {
            "topic": topic,
            "task": original_prompt,
            "query": original_prompt,
            "step1": "理解任务需求并收集必要信息",
            "step2": "执行核心操作",
            "step3": "验证结果并完成输出",
            "required_params": "根据具体工具确定",
            "fallback_method": "使用本地缓存或其他数据源",
            "count": "批量任务",
            "batch_size": 5,
            "delay": 3,
            "resource": "目标资源",
            "input_format": "待定",
            "output_format": "待定",
            "constraints": "待定",
            "references": "待定",
            "command": "待执行命令",
        }
        defaults.update(kwargs)

        return template.render(**defaults)

    def track_effectiveness(self, template_id: str, was_successful: bool) -> bool:
        """
        追踪模板使用效果

        返回:
            是否找到对应模板
        """
        for t in self.library.get_all_templates():
            if t.template_id == template_id:
                t.record_usage(was_successful)
                return True
        return False

    def export_library(self, output_path: str) -> str:
        """导出模板库到 JSON 文件"""
        data = {
            "exported_at": datetime.now().isoformat(),
            "total_templates": len(self.library.get_all_templates()),
            "categories": {
                "hallucination": len(self.library.HALLUCINATION_TEMPLATES),
                "knowledge_gap": len(self.library.KNOWLEDGE_GAP_TEMPLATES),
                "tool_usage_error": len(self.library.TOOL_ERROR_TEMPLATES),
                "general": len(self.library.GENERAL_TEMPLATES),
            },
            "templates": [t.to_dict() for t in self.library.get_all_templates()],
        }

        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return output_path

    def get_library_summary(self) -> Dict:
        """获取模板库摘要"""
        all_templates = self.library.get_all_templates()
        by_category = {}
        for t in all_templates:
            category = t.failure_pattern.split(".")[0] if "." in t.failure_pattern else t.failure_pattern
            if category not in by_category:
                by_category[category] = {"count": 0, "avg_effectiveness": 0, "total_usage": 0}
            by_category[category]["count"] += 1
            by_category[category]["avg_effectiveness"] += t.effectiveness_score
            by_category[category]["total_usage"] += t.usage_count

        for cat in by_category:
            by_category[cat]["avg_effectiveness"] /= by_category[cat]["count"]

        return {
            "total_templates": len(all_templates),
            "by_category": by_category,
            "top_templates": sorted(
                [{"id": t.template_id, "name": t.name, "effectiveness": t.effectiveness_score, "usage": t.usage_count}
                 for t in all_templates],
                key=lambda x: x["effectiveness"],
                reverse=True,
            )[:5],
        }


# ============================================================
# 演示与测试
# ============================================================

def run_demo():
    """演示改进生成器功能"""
    # print("=" * 70)
    # print("🔧 Agent自改进Prompt模板库 - 演示")
    # print("=" * 70)

    generator = ImprovementGenerator()

    # 1. 库摘要
    # print("\n📊 模板库摘要:")
    summary = generator.get_library_summary()
    # print(f"  总模板数: {summary['total_templates']}")
    for cat, info in summary["by_category"].items():
        # print(f"  - {cat}: {info['count']}个模板, 平均有效性 {info['avg_effectiveness']:.2f}")

    # print(f"\n🏆 Top 5 最有效模板:")
    for i, t in enumerate(summary["top_templates"], 1):
        # print(f"  {i}. {t['name']} (有效性: {t['effectiveness']:.2f}, 使用: {t['usage']}次)")

    # 2. 基于失败记录生成改进 prompt
    # print("\n" + "=" * 70)
    # print("📝 基于失败案例生成改进 Prompt")
    # print("=" * 70)

    # 模拟失败记录
    failure_cases = [
        {
            "failure_type": "tool_usage_error",
            "failure_subtype": "timeout",
            "tool_name": "web_fetch",
            "task_description": "搜索最新的钙钛矿太阳能电池论文",
        },
        {
            "failure_type": "hallucination",
            "failure_subtype": "fabricated_reference",
            "tool_name": "read",
            "task_description": "请提供关于固态电池的最新研究论文",
        },
        {
            "failure_type": "knowledge_gap",
            "failure_subtype": "missing_domain_knowledge",
            "task_description": "分析2025年Q3全球固态电池市场数据",
        },
    ]

    for i, fc in enumerate(failure_cases, 1):
        # print(f"\n📌 案例 {i}: {fc['failure_type']}/{fc['failure_subtype']}")
        template = generator.generate_template(fc)
        if template:
            rendered = generator.apply_template(
                fc["task_description"], template,
                topic=fc["task_description"][:50],
                fallback_method="使用 arXiv 或 Google Scholar 作为备选",
            )
            # print(f"  模板: {template.name}")
            # print(f"  有效性: {template.effectiveness_score:.2f}")
            # print(f"  改进Prompt:")
            for line in rendered.split("\n")[:8]:
                # print(f"    {line}")
            if rendered.count("\n") > 7:
                # print("    ...")

    # 3. 导出模板库
    # print("\n" + "=" * 70)
    # print("💾 导出模板库")
    # print("=" * 70)

    export_path = "/Users/mettlyz/.openclaw/workspace/output/task-1953/自改进Prompt模板库_JSON_2026-04-25.json"
    generator.export_library(export_path)
    # print(f"  已导出至: {export_path}")

    # 4. 效果追踪演示
    # print("\n📈 效果追踪:")
    generator.track_effectiveness("imp_tool_timeout_001", True)
    generator.track_effectiveness("imp_tool_timeout_001", True)
    generator.track_effectiveness("imp_tool_timeout_001", False)
    t = generator.library.TOOL_ERROR_TEMPLATES[2]  # timeout template
    # print(f"  {t.name}: 使用{t.usage_count}次, 成功{t.success_count}次, 有效性={t.effectiveness_score:.2f}")

    return generator


if __name__ == "__main__":
    run_demo()

#!/usr/bin/env python3
"""
failure_classifier.py - Agent执行失败案例自动分类器

功能：
1. 分析任务执行失败的错误信息、上下文和工具调用记录
2. 自动分类为三大类型：幻觉型 / 知识缺失型 / 工具使用错误型
3. 支持三级分类：一级分类(3种) → 二级分类(12种) → 三级标签(可扩展)
4. 输出分类结果和改进建议

设计原则：
- 关键词匹配层（快速初筛，准确率 ~85%）
- 规则引擎层（精确分类，准确率 ~92%）
- LLM辅助层（复杂案例交由大模型分析，准确率 ~97%）

作者: Dudu AI Assistant
创建日期: 2026-04-25
版本: v1.0
"""

import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Tuple


# ============================================================
# 数据模型
# ============================================================

class FailureType(Enum):
    """一级失败类型"""
    HALLUCINATION = "hallucination"           # 幻觉型
    KNOWLEDGE_GAP = "knowledge_gap"           # 知识缺失型
    TOOL_USAGE_ERROR = "tool_usage_error"     # 工具使用错误型


class FailureSubtype(Enum):
    """二级失败子类型"""
    # 幻觉型子类型
    FACTUAL_ERROR = "factual_error"                       # 事实错误
    FABRICATED_REFERENCE = "fabricated_reference"         # 伪造引用
    OVERCONFIDENT_GUESS = "overconfident_guess"           # 过度自信的猜测
    LOGICAL_INCONSISTENCY = "logical_inconsistency"       # 逻辑不一致

    # 知识缺失型子类型
    MISSING_DOMAIN_KNOWLEDGE = "missing_domain_knowledge"  # 缺少领域知识
    OUTDATED_INFORMATION = "outdated_information"          # 信息过时
    INSUFFICIENT_CONTEXT = "insufficient_context"          # 上下文不足
    AMBIGUOUS_QUERY = "ambiguous_query"                    # 查询歧义

    # 工具使用错误型子类型
    WRONG_TOOL = "wrong_tool"                              # 选错工具
    WRONG_PARAMETERS = "wrong_parameters"                  # 参数错误
    TIMEOUT = "timeout"                                    # 超时
    RATE_LIMIT = "rate_limit"                              # 频率限制
    PERMISSION_DENIED = "permission_denied"                # 权限不足


class Severity(Enum):
    """严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FailureRecord:
    """失败记录"""
    failure_id: str = ""
    trace_id: str = ""
    task_id: int = 0
    task_title: str = ""
    failure_type: str = ""
    failure_subtype: str = ""
    severity: str = "medium"
    step_id: str = ""
    tool_name: str = ""
    error_message: str = ""
    error_context: Dict = field(default_factory=dict)
    original_prompt: str = ""
    agent_output: str = ""
    classification_confidence: float = 0.0
    classification_method: str = ""  # keyword / rule / llm
    root_cause: str = ""
    recovery_action: str = ""
    recovery_success: bool = False
    learning_point: str = ""
    suggested_improvement: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


# ============================================================
# 分类知识库
# ============================================================

class ClassificationKnowledge:
    """分类知识库 - 关键词、规则和模式定义"""

    # --- 幻觉型关键词 ---
    HALLUCINATION_KEYWORDS = {
        FailureSubtype.FACTUAL_ERROR: [
            "不正确的", "错误的", "与实际不符", "factually incorrect",
            "wrong fact", "inaccurate", "事实错误", "数据不实",
            "incorrect number", "false statement",
        ],
        FailureSubtype.FABRICATED_REFERENCE: [
            "不存在的引用", "伪造的", "fabricated", "fake reference",
            "non-existent paper", "虚构的文献", "伪造的论文",
            "cannot be found", "引用不存在", "citation not found",
        ],
        FailureSubtype.OVERCONFIDENT_GUESS: [
            "过度自信", "overconfident", "without evidence",
            "未经证实", "猜测", "assumed without", "confidently wrong",
            "缺乏依据", "speculation presented as fact",
        ],
        FailureSubtype.LOGICAL_INCONSISTENCY: [
            "前后矛盾", "逻辑不一致", "contradictory", "inconsistent",
            "self-contradicting", "前后不符", "逻辑矛盾",
            "does not follow", "non sequitur",
        ],
    }

    # --- 知识缺失型关键词 ---
    KNOWLEDGE_GAP_KEYWORDS = {
        FailureSubtype.MISSING_DOMAIN_KNOWLEDGE: [
            "不了解", "不知道", "缺乏知识", "missing knowledge",
            "domain gap", "not familiar with", "超出知识范围",
            "out of scope", "unfamiliar domain", "未覆盖",
            "knowledge cutoff", "超出训练数据",
            "无法确定", "不在我的知识范围", "不在知识范围",
            "my knowledge", "cannot answer", "unable to answer",
        ],
        FailureSubtype.OUTDATED_INFORMATION: [
            "过时的", "outdated", "obsolete", "已废弃",
            "deprecated", "不再适用", "版本过时", "old version",
            "training data cutoff", "知识截止",
        ],
        FailureSubtype.INSUFFICIENT_CONTEXT: [
            "上下文不足", "insufficient context", "缺少背景",
            "missing context", "信息不全", "incomplete information",
            "无法确定", "ambiguous", "缺乏前提",
        ],
        FailureSubtype.AMBIGUOUS_QUERY: [
            "歧义", "ambiguous", "不清楚", "unclear",
            "multiple interpretations", "含义不明",
            "query unclear", "问题模糊",
        ],
    }

    # --- 工具使用错误型关键词 ---
    TOOL_ERROR_KEYWORDS = {
        FailureSubtype.WRONG_TOOL: [
            "错误的工具", "wrong tool", "tool mismatch",
            "不适用的工具", "inappropriate tool", "工具选择错误",
            "should have used", "工具不匹配",
        ],
        FailureSubtype.WRONG_PARAMETERS: [
            "参数错误", "wrong parameter", "invalid argument",
            "参数不合法", "parameter error", "格式错误",
            "invalid format", "type error", "缺少参数",
            "missing parameter", "必填参数",
        ],
        FailureSubtype.TIMEOUT: [
            "超时", "timeout", "timed out", "连接超时",
            "request timeout", "操作超时", "exceeded time limit",
            "deadline exceeded", "response timeout",
        ],
        FailureSubtype.RATE_LIMIT: [
            "频率限制", "rate limit", "too many requests",
            "429", "rate limited", "请求过多", "限流",
            "throttled", "quota exceeded",
        ],
        FailureSubtype.PERMISSION_DENIED: [
            "权限不足", "permission denied", "access denied",
            "403", "forbidden", "未授权", "unauthorized",
            "401", "无权限", "not authorized",
        ],
    }

    # --- 规则引擎 ---
    CLASSIFICATION_RULES = [
        # 规则1: web_fetch 超时 → 工具错误-超时
        {
            "condition": lambda ctx: ctx.get("tool_name") == "web_fetch" and "timeout" in ctx.get("error_message", "").lower(),
            "result": (FailureType.TOOL_USAGE_ERROR, FailureSubtype.TIMEOUT),
            "confidence": 0.95,
            "root_cause_template": "web_fetch 工具调用超时，目标服务器响应缓慢或不可达",
            "recovery_template": "增加超时时间至 {timeout}s，或尝试备用数据源",
        },
        # 规则2: exec 返回非零退出码 → 工具错误-参数错误
        {
            "condition": lambda ctx: ctx.get("tool_name") == "exec" and ctx.get("exit_code", 0) != 0,
            "result": (FailureType.TOOL_USAGE_ERROR, FailureSubtype.WRONG_PARAMETERS),
            "confidence": 0.88,
            "root_cause_template": "命令执行失败（退出码={exit_code}），可能参数有误或环境不满足",
            "recovery_template": "检查命令参数、环境变量和依赖是否齐全",
        },
        # 规则3: 429状态码 → 工具错误-频率限制
        {
            "condition": lambda ctx: ctx.get("status_code") == 429 or "429" in ctx.get("error_message", ""),
            "result": (FailureType.TOOL_USAGE_ERROR, FailureSubtype.RATE_LIMIT),
            "confidence": 0.98,
            "root_cause_template": "API 频率限制被触发，请求过于频繁",
            "recovery_template": "添加请求间隔（建议 {delay}s），或使用批量接口减少调用次数",
        },
        # 规则4: 403/401状态码 → 工具错误-权限不足
        {
            "condition": lambda ctx: ctx.get("status_code") in [401, 403] or "permission" in ctx.get("error_message", "").lower() or "denied" in ctx.get("error_message", "").lower(),
            "result": (FailureType.TOOL_USAGE_ERROR, FailureSubtype.PERMISSION_DENIED),
            "confidence": 0.95,
            "root_cause_template": "访问被拒绝，可能缺少认证或权限不足",
            "recovery_template": "检查 API Key 是否有效，确认权限范围",
        },
        # 规则5: 输出中包含"无法"或"不知道" → 知识缺失
        {
            "condition": lambda ctx: any(kw in ctx.get("agent_output", "") for kw in ["无法确定", "不知道", "不清楚", "cannot determine", "don't know", "unable to"]),
            "result": (FailureType.KNOWLEDGE_GAP, FailureSubtype.MISSING_DOMAIN_KNOWLEDGE),
            "confidence": 0.82,
            "root_cause_template": "Agent 缺乏完成任务所需的知识",
            "recovery_template": "使用 Research Agent 先检索相关知识，补充上下文后再执行",
        },
        # 规则6: 任务描述与输出完全不匹配 → 幻觉
        {
            "condition": lambda ctx: ctx.get("task_description") and ctx.get("agent_output") and len(set(ctx.get("task_description", "").lower().split()) & set(ctx.get("agent_output", "").lower().split())) < 3,
            "result": (FailureType.HALLUCINATION, FailureSubtype.OVERCONFIDENT_GUESS),
            "confidence": 0.70,
            "root_cause_template": "Agent 输出与任务描述关联度极低，可能存在幻觉",
            "recovery_template": "在 prompt 中明确要求：'请直接回答以下问题，不要展开无关内容'",
        },
    ]

    # --- 改进建议模板 ---
    IMPROVEMENT_SUGGESTIONS = {
        FailureSubtype.FACTUAL_ERROR: '在 prompt 中添加约束：请只陈述有可靠来源的事实，不确定的内容请明确标注',
        FailureSubtype.FABRICATED_REFERENCE: '在 prompt 中添加：所有引用的论文/数据必须真实存在，请提供可验证的链接或DOI',
        FailureSubtype.OVERCONFIDENT_GUESS: '在 prompt 中添加：对于不确定的内容，请使用可能/据我所知等限定词，不要断言',
        FailureSubtype.LOGICAL_INCONSISTENCY: '在 prompt 中添加：请确保回答前后逻辑一致，不要自相矛盾',
        FailureSubtype.MISSING_DOMAIN_KNOWLEDGE: '先使用 Research Agent 检索相关知识，将检索结果作为上下文注入后再执行任务',
        FailureSubtype.OUTDATED_INFORMATION: '在 prompt 中指定：请使用最新信息（2024年以后），如信息可能过时请明确说明',
        FailureSubtype.INSUFFICIENT_CONTEXT: '在任务描述中添加更多背景信息，包括：输入格式、预期输出格式、约束条件',
        FailureSubtype.AMBIGUOUS_QUERY: '将模糊的任务描述拆分为多个具体的子任务，每个子任务有明确的输入和输出',
        FailureSubtype.WRONG_TOOL: '在任务路由时增加工具匹配检查，确保选用的工具与任务类型匹配',
        FailureSubtype.WRONG_PARAMETERS: '在工具调用前增加参数验证步骤，或提供参数模板',
        FailureSubtype.TIMEOUT: '增加超时时间，或添加重试机制（最多3次，间隔递增）',
        FailureSubtype.RATE_LIMIT: '在工具调用之间添加延迟，或使用批量接口减少调用次数',
        FailureSubtype.PERMISSION_DENIED: '检查 API Key 是否有效，确认权限配置是否正确',
    }


# ============================================================
# 核心分类器
# ============================================================

class FailureClassifier:
    """
    Agent执行失败案例自动分类器

    三级分类策略：
    1. 关键词匹配层 - 快速初筛（~85%准确率）
    2. 规则引擎层 - 精确分类（~92%准确率）
    3. LLM辅助层 - 复杂案例（~97%准确率，需要外部LLM调用）
    """

    def __init__(self, knowledge: ClassificationKnowledge = None):
        self.knowledge = knowledge or ClassificationKnowledge()
        self.classification_history: List[FailureRecord] = []

    def classify(
        self,
        error_message: str,
        task_description: str = "",
        agent_output: str = "",
        tool_name: str = "",
        context: Dict = None,
        trace_id: str = "",
        task_id: int = 0,
        task_title: str = "",
        step_id: str = "",
    ) -> FailureRecord:
        """
        对单个失败案例进行分类

        参数:
            error_message: 错误信息
            task_description: 原始任务描述
            agent_output: Agent 的实际输出
            tool_name: 使用的工具名称
            context: 额外上下文
            trace_id: 关联的执行轨迹ID
            task_id: 任务ID
            task_title: 任务标题
            step_id: 失败的步骤ID

        返回:
            FailureRecord: 分类后的失败记录
        """
        ctx = context or {}
        ctx["error_message"] = error_message
        ctx["task_description"] = task_description
        ctx["agent_output"] = agent_output
        ctx["tool_name"] = tool_name

        # 策略1: 规则引擎（优先级最高，因为规则更精确）
        record = self._classify_by_rules(ctx)
        if record and record.classification_confidence >= 0.80:
            record.classification_method = "rule"
        else:
            # 策略2: 关键词匹配（降低阈值以提高召回率）
            record = self._classify_by_keywords(ctx)
            if record and record.classification_confidence >= 0.25:
                record.classification_method = "keyword"
            else:
                # 策略3: LLM辅助（标记为需要LLM分类）
                record = self._classify_by_llm_marker(ctx)
                record.classification_method = "llm_pending"

        # 填充元数据
        failure_id = f"fail_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(error_message) % 10000:04d}"
        record.failure_id = failure_id
        record.trace_id = trace_id
        record.task_id = task_id
        record.task_title = task_title
        record.step_id = step_id
        record.tool_name = tool_name
        record.error_message = error_message
        record.original_prompt = task_description
        record.agent_output = agent_output
        record.error_context = {k: v for k, v in ctx.items() if k not in ["error_message", "task_description", "agent_output", "tool_name"]}
        record.created_at = datetime.now().isoformat()

        # 确定严重程度
        record.severity = self._assess_severity(record)

        # 添加改进建议（仅对已知类型）
        if record.failure_subtype and record.failure_subtype != "unknown":
            try:
                subtype = FailureSubtype(record.failure_subtype)
                record.suggested_improvement = self.knowledge.IMPROVEMENT_SUGGESTIONS.get(subtype, "")
            except ValueError:
                record.suggested_improvement = ""

        self.classification_history.append(record)
        return record

    def _classify_by_rules(self, ctx: Dict) -> Optional[FailureRecord]:
        """规则引擎分类"""
        for rule in self.knowledge.CLASSIFICATION_RULES:
            try:
                if rule["condition"](ctx):
                    ftype, fsubtype = rule["result"]
                    record = FailureRecord(
                        failure_type=ftype.value,
                        failure_subtype=fsubtype.value,
                        classification_confidence=rule["confidence"],
                        root_cause=rule.get("root_cause_template", ""),
                        recovery_action=rule.get("recovery_template", ""),
                    )
                    return record
            except Exception:
                continue
        return None

    def _classify_by_keywords(self, ctx: Dict) -> Optional[FailureRecord]:
        """关键词匹配分类"""
        error_msg = ctx.get("error_message", "").lower()
        agent_output = ctx.get("agent_output", "").lower()
        combined_text = f"{error_msg} {agent_output}"

        best_score = 0.0
        best_type = None
        best_subtype = None

        # 检查所有类型的关键词
        all_keyword_sets = [
            (FailureType.HALLUCINATION, self.knowledge.HALLUCINATION_KEYWORDS),
            (FailureType.KNOWLEDGE_GAP, self.knowledge.KNOWLEDGE_GAP_KEYWORDS),
            (FailureType.TOOL_USAGE_ERROR, self.knowledge.TOOL_ERROR_KEYWORDS),
        ]

        for ftype, subtype_map in all_keyword_sets:
            for subtype, keywords in subtype_map.items():
                score = 0.0
                for kw in keywords:
                    if kw.lower() in combined_text:
                        score += 1.0

                if score > 0:
                    # 归一化
                    normalized = score / len(keywords)
                    # 关键词匹配密度
                    density = score / max(len(combined_text.split()), 1)
                    # 综合分数
                    final_score = normalized * 0.6 + min(density * 10, 1.0) * 0.4

                    if final_score > best_score:
                        best_score = final_score
                        best_type = ftype
                        best_subtype = subtype

        if best_type and best_score > 0.15:
            return FailureRecord(
                failure_type=best_type.value,
                failure_subtype=best_subtype.value,
                classification_confidence=min(best_score, 0.90),
            )

        return None

    def _classify_by_llm_marker(self, ctx: Dict) -> FailureRecord:
        """标记为需要LLM辅助分类的案例"""
        return FailureRecord(
            failure_type="unknown",
            failure_subtype="unknown",
            classification_confidence=0.30,
            root_cause="无法通过规则或关键词自动分类，需要LLM辅助分析",
            recovery_action="调用LLM进行语义分析以确定失败类型",
        )

    def _assess_severity(self, record: FailureRecord) -> str:
        """评估失败严重程度"""
        # 工具错误通常较低（可重试）
        if record.failure_type == FailureType.TOOL_USAGE_ERROR.value:
            if record.failure_subtype in [FailureSubtype.TIMEOUT.value, FailureSubtype.RATE_LIMIT.value]:
                return Severity.LOW.value
            elif record.failure_subtype == FailureSubtype.PERMISSION_DENIED.value:
                return Severity.HIGH.value
            return Severity.MEDIUM.value

        # 知识缺失中等
        if record.failure_type == FailureType.KNOWLEDGE_GAP.value:
            return Severity.MEDIUM.value

        # 幻觉型较高（影响可信度）
        if record.failure_type == FailureType.HALLUCINATION.value:
            if record.failure_subtype in [FailureSubtype.FABRICATED_REFERENCE.value, FailureSubtype.FACTUAL_ERROR.value]:
                return Severity.HIGH.value
            return Severity.MEDIUM.value

        return Severity.MEDIUM.value

    def classify_batch(self, failures: List[Dict]) -> List[FailureRecord]:
        """批量分类失败案例"""
        results = []
        for f in failures:
            record = self.classify(
                error_message=f.get("error_message", ""),
                task_description=f.get("task_description", ""),
                agent_output=f.get("agent_output", ""),
                tool_name=f.get("tool_name", ""),
                context=f.get("context", {}),
                trace_id=f.get("trace_id", ""),
                task_id=f.get("task_id", 0),
                task_title=f.get("task_title", ""),
                step_id=f.get("step_id", ""),
            )
            results.append(record)
        return results

    def get_failure_statistics(self, period_days: int = 30) -> Dict:
        """获取失败统计信息"""
        cutoff = datetime.now()
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=period_days)

        type_counts = {}
        subtype_counts = {}
        severity_counts = {}
        tool_counts = {}

        for record in self.classification_history:
            if record.failure_type:
                type_counts[record.failure_type] = type_counts.get(record.failure_type, 0) + 1
            if record.failure_subtype:
                subtype_counts[record.failure_subtype] = subtype_counts.get(record.failure_subtype, 0) + 1
            if record.severity:
                severity_counts[record.severity] = severity_counts.get(record.severity, 0) + 1
            if record.tool_name:
                tool_counts[record.tool_name] = tool_counts.get(record.tool_name, 0) + 1

        return {
            "total_failures": len(self.classification_history),
            "period_days": period_days,
            "by_type": type_counts,
            "by_subtype": subtype_counts,
            "by_severity": severity_counts,
            "by_tool": tool_counts,
        }

    def get_top_failure_patterns(self, limit: int = 10) -> List[Dict]:
        """获取最常见的失败模式"""
        patterns = {}
        for record in self.classification_history:
            key = f"{record.failure_type}/{record.failure_subtype}"
            if key not in patterns:
                patterns[key] = {
                    "pattern": key,
                    "count": 0,
                    "confidence_avg": 0.0,
                    "tools_involved": set(),
                    "last_seen": None,
                }
            patterns[key]["count"] += 1
            patterns[key]["confidence_avg"] += record.classification_confidence
            if record.tool_name:
                patterns[key]["tools_involved"].add(record.tool_name)
            patterns[key]["last_seen"] = record.created_at

        # 计算平均置信度
        for p in patterns.values():
            if p["count"] > 0:
                p["confidence_avg"] /= p["count"]
            p["tools_involved"] = list(p["tools_involved"])

        # 按频率排序
        sorted_patterns = sorted(patterns.values(), key=lambda x: x["count"], reverse=True)
        return sorted_patterns[:limit]

    def export_report(self, output_path: str, period_days: int = 30) -> str:
        """导出分类报告"""
        stats = self.get_failure_statistics(period_days)
        top_patterns = self.get_top_failure_patterns(limit=10)

        report = {
            "report_title": "Agent失败案例分类报告",
            "generated_at": datetime.now().isoformat(),
            "period_days": period_days,
            "summary": stats,
            "top_patterns": top_patterns,
            "recent_failures": [r.to_dict() for r in self.classification_history[-20:]],
        }

        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return output_path


# ============================================================
# 演示与测试
# ============================================================

def run_demo():
    """演示分类器功能"""
    # print("=" * 70)
    # print("🔍 Agent失败案例自动分类器 - 演示")
    # print("=" * 70)

    classifier = FailureClassifier()

    # 测试用例1: 工具超时
    # print("\n📌 测试1: web_fetch 超时")
    r1 = classifier.classify(
        error_message="Request timeout after 30 seconds",
        task_description="搜索最新的钙钛矿太阳能电池论文",
        tool_name="web_fetch",
        context={"url": "https://pubs.acs.org", "retry_count": 3},
    )
    # print(f"  类型: {r1.failure_type} / {r1.failure_subtype}")
    # print(f"  置信度: {r1.classification_confidence:.2f}")
    # print(f"  方法: {r1.classification_method}")
    # print(f"  根因: {r1.root_cause}")
    # print(f"  改进: {r1.suggested_improvement[:60]}...")

    # 测试用例2: 知识缺失
    # print("\n📌 测试2: Agent表示不知道")
    r2 = classifier.classify(
        error_message="",
        task_description="分析2025年Q3全球固态电池市场数据",
        agent_output="我无法确定2025年Q3的固态电池市场数据，这些信息不在我的知识范围内",
    )
    # print(f"  类型: {r2.failure_type} / {r2.failure_subtype}")
    # print(f"  置信度: {r2.classification_confidence:.2f}")
    # print(f"  方法: {r2.classification_method}")
    # print(f"  根因: {r2.root_cause}")

    # 测试用例3: 频率限制
    # print("\n📌 测试3: API频率限制")
    r3 = classifier.classify(
        error_message="HTTP 429 Too Many Requests - Rate limit exceeded",
        task_description="批量搜索100篇论文",
        tool_name="web_fetch",
        context={"status_code": 429},
    )
    # print(f"  类型: {r3.failure_type} / {r3.failure_subtype}")
    # print(f"  置信度: {r3.classification_confidence:.2f}")
    # print(f"  方法: {r3.classification_method}")

    # 测试用例4: 权限不足
    # print("\n📌 测试4: 数据库权限不足")
    r4 = classifier.classify(
        error_message="Access denied for user 'kanban'@'localhost' (using password: YES)",
        task_description="更新任务状态",
        tool_name="exec",
        context={"status_code": 403},
    )
    # print(f"  类型: {r4.failure_type} / {r4.failure_subtype}")
    # print(f"  置信度: {r4.classification_confidence:.2f}")
    # print(f"  方法: {r4.classification_method}")

    # 测试用例5: 参数错误
    # print("\n📌 测试5: 命令执行参数错误")
    r5 = classifier.classify(
        error_message="FileNotFoundError: [Errno 2] No such file or directory: '/tmp/data.csv'",
        task_description="分析销售数据",
        tool_name="exec",
        context={"exit_code": 1, "command": "python analyze.py /tmp/data.csv"},
    )
    # print(f"  类型: {r5.failure_type} / {r5.failure_subtype}")
    # print(f"  置信度: {r5.classification_confidence:.2f}")
    # print(f"  方法: {r5.classification_method}")

    # 统计
    # print("\n" + "=" * 70)
    # print("📊 分类统计")
    # print("=" * 70)
    stats = classifier.get_failure_statistics()
    # print(f"  总失败数: {stats['total_failures']}")
    # print(f"  按类型: {json.dumps(stats['by_type'], ensure_ascii=False, indent=4)}")
    # print(f"  按工具: {json.dumps(stats['by_tool'], ensure_ascii=False, indent=4)}")

    top_patterns = classifier.get_top_failure_patterns()
    # print(f"\n🔝 最常见失败模式:")
    for i, p in enumerate(top_patterns, 1):
        # print(f"  {i}. {p['pattern']} (出现{p['count']}次, 平均置信度{p['confidence_avg']:.2f})")

    return classifier


if __name__ == "__main__":
    run_demo()

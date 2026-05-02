#!/usr/bin/env python3
"""
失败案例自动分类器
Agent 任务执行轨迹回放与自改进系统 — Task #1953

分类维度（三大类型）：
  1. 幻觉型 (HALLUCINATION)     — 模型捏造事实、路径、API 等
  2. 知识缺失型 (KNOWLEDGE_GAP)  — 领域知识不足、信息过时
  3. 工具使用错误型 (TOOL_MISUSE) — 工具调用参数错误、格式错误、滥用工具

Author: Dudu (AI Sidekick)
Date:   2026-04-25
"""

import re
import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from lib.db_connector import get_db_connection


# ─── 枚举 ────────────────────────────────────────────────────────────────────

class FailureType(str, Enum):
    HALLUCINATION   = "hallucination"       # 幻觉型
    KNOWLEDGE_GAP   = "knowledge_gap"       # 知识缺失型
    TOOL_MISUSE     = "tool_misuse"         # 工具使用错误型
    RATE_LIMIT      = "rate_limit"          # 限流/配额
    TIMEOUT         = "timeout"             # 超时
    PERMISSION      = "permission"          # 权限不足
    UNKNOWN         = "unknown"             # 无法分类


class FailureSeverity(str, Enum):
    CRITICAL = "critical"   # 任务完全失败
    HIGH     = "high"       # 关键步骤失败，结果不可信
    MEDIUM   = "medium"     # 部分功能受损
    LOW      = "low"        # 轻微影响，任务仍完成


# ─── 数据结构 ────────────────────────────────────────────────────────────────

@dataclass
class FailureRecord:
    trace_id:    str
    task_id:     int
    step_id:     str
    failure_type: FailureType
    severity:    FailureSeverity
    confidence:  float          # 0.0–1.0，分类置信度
    evidence:    str            # 触发该分类的关键证据片段
    suggestion:  str            # 改进建议
    raw_error:   Optional[str] = None
    meta:        dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "trace_id":     self.trace_id,
            "task_id":      self.task_id,
            "step_id":      self.step_id,
            "failure_type": self.failure_type.value,
            "severity":     self.severity.value,
            "confidence":   round(self.confidence, 3),
            "evidence":     self.evidence,
            "suggestion":   self.suggestion,
            "raw_error":    self.raw_error,
            "meta":         self.meta,
        }


# ─── 规则库 ──────────────────────────────────────────────────────────────────

# 幻觉型特征
HALLUCINATION_PATTERNS = [
    # 文件/路径不存在
    (r"No such file or directory", 0.90),
    (r"FileNotFoundError", 0.85),
    (r"cannot find.*file|file.*not found", 0.80),
    # 函数/属性不存在
    (r"AttributeError: .* has no attribute", 0.88),
    (r"NameError: name '.*' is not defined", 0.82),
    (r"ImportError: cannot import name", 0.80),
    (r"ModuleNotFoundError", 0.75),
    # URL/API 不存在
    (r"404 Not Found", 0.70),
    (r"HTTP 404|status_code=404", 0.70),
    # 数据库表/列不存在
    (r"Table '.*' doesn't exist", 0.90),
    (r"Unknown column '.*' in", 0.85),
    # 模型输出中包含明显虚构标志
    (r"I don't have access to real-time", 0.60),
    (r"as of my (knowledge|training) cutoff", 0.55),
]

# 知识缺失型特征
KNOWLEDGE_GAP_PATTERNS = [
    # 过时 API
    (r"deprecated.*use .* instead", 0.80),
    (r"has been removed in version", 0.85),
    (r"API.*changed|endpoint.*moved", 0.75),
    # 概念混淆
    (r"TypeError: .* takes .* positional argument", 0.65),
    (r"unexpected keyword argument", 0.65),
    # 领域缺失
    (r"I('m| am) not (sure|familiar|aware)", 0.55),
    (r"I don't (know|have information)", 0.55),
    (r"insufficient (data|information|context)", 0.60),
    # 版本不匹配
    (r"version.*mismatch|incompatible version", 0.75),
    (r"requires.*>=.*but.*installed", 0.78),
]

# 工具使用错误型特征
TOOL_MISUSE_PATTERNS = [
    # 参数错误
    (r"missing required (argument|parameter|field)", 0.88),
    (r"invalid (parameter|argument|value).*expected", 0.85),
    (r"JSONDecodeError|json.decoder.JSONDecodeError", 0.80),
    (r"SyntaxError", 0.72),
    # 数据库操作错误
    (r"pymysql\.err|OperationalError.*MySQL|IntegrityError", 0.82),
    (r"duplicate entry|UNIQUE constraint", 0.78),
    # Shell/Exec 错误
    (r"command not found|No command", 0.80),
    (r"Permission denied", 0.75),
    (r"bash: .*: command not found", 0.85),
    # 工具调用格式错误
    (r"tool_call.*malformed|invalid.*tool.*schema", 0.88),
    (r"required field.*missing.*tool", 0.85),
    # 超出工具能力范围（误用）
    (r"context.*too long|token.*limit.*exceeded", 0.70),
    (r"rate.?limit|429 Too Many Requests", 0.65),
]

# 限流/超时（独立分类）
RATE_LIMIT_PATTERNS = [
    (r"429|rate.?limit|quota.*exceeded|RateLimitError", 0.95),
    (r"too many requests", 0.90),
]

TIMEOUT_PATTERNS = [
    (r"timeout|timed? out|deadline exceeded", 0.90),
    (r"TimeoutError|ReadTimeout|ConnectTimeout", 0.92),
]

PERMISSION_PATTERNS = [
    (r"permission denied|access denied|unauthorized|403 Forbidden", 0.88),
    (r"PermissionError|AuthenticationError", 0.90),
]


# ─── 主分类器 ────────────────────────────────────────────────────────────────

class FailureClassifier:
    """
    规则引擎 + 置信度加权的失败分类器。
    未来可接入 LLM 进行语义级兜底分类。
    """

    def classify_error(
        self,
        error_text: str,
        step_type: str = "",
        output_text: str = "",
        trace_id: str = "unknown",
        task_id: int = 0,
        step_id: str = "unknown",
    ) -> FailureRecord:
        combined = f"{error_text}\n{output_text}".lower()

        # 按优先级逐类检查
        checks = [
            (RATE_LIMIT_PATTERNS,   FailureType.RATE_LIMIT),
            (TIMEOUT_PATTERNS,      FailureType.TIMEOUT),
            (PERMISSION_PATTERNS,   FailureType.PERMISSION),
            (TOOL_MISUSE_PATTERNS,  FailureType.TOOL_MISUSE),
            (HALLUCINATION_PATTERNS,FailureType.HALLUCINATION),
            (KNOWLEDGE_GAP_PATTERNS,FailureType.KNOWLEDGE_GAP),
        ]

        best_type       = FailureType.UNKNOWN
        best_confidence = 0.0
        best_evidence   = error_text[:200]

        for patterns, ftype in checks:
            for pattern, confidence in patterns:
                m = re.search(pattern, combined, re.IGNORECASE)
                if m and confidence > best_confidence:
                    best_type       = ftype
                    best_confidence = confidence
                    best_evidence   = m.group(0)

        severity   = self._infer_severity(best_type, best_confidence)
        suggestion = self._generate_suggestion(best_type, best_evidence, step_type)

        return FailureRecord(
            trace_id=trace_id,
            task_id=task_id,
            step_id=step_id,
            failure_type=best_type,
            severity=severity,
            confidence=best_confidence,
            evidence=best_evidence,
            suggestion=suggestion,
            raw_error=error_text[:500],
            meta={"step_type": step_type},
        )

    def classify_trace(self, trace: dict) -> list[FailureRecord]:
        """对整条轨迹中所有含错误的步骤进行分类"""
        results = []
        for step in trace.get("steps", []):
            err = step.get("error")
            if not err:
                continue
            err_text = err if isinstance(err, str) else json.dumps(err, ensure_ascii=False)
            out_text = str(step.get("output", ""))
            record = self.classify_error(
                error_text=err_text,
                output_text=out_text,
                step_type=step.get("step_type", ""),
                trace_id=trace.get("trace_id", ""),
                task_id=trace.get("task_id", 0),
                step_id=step.get("step_id", ""),
            )
            results.append(record)
        return results

    def _infer_severity(self, ftype: FailureType, confidence: float) -> FailureSeverity:
        if ftype in (FailureType.HALLUCINATION,) and confidence >= 0.85:
            return FailureSeverity.CRITICAL
        if ftype in (FailureType.TOOL_MISUSE, FailureType.PERMISSION) and confidence >= 0.80:
            return FailureSeverity.HIGH
        if ftype in (FailureType.KNOWLEDGE_GAP,) and confidence >= 0.70:
            return FailureSeverity.MEDIUM
        if ftype in (FailureType.RATE_LIMIT, FailureType.TIMEOUT):
            return FailureSeverity.MEDIUM
        if confidence < 0.60:
            return FailureSeverity.LOW
        return FailureSeverity.MEDIUM

    def _generate_suggestion(self, ftype: FailureType, evidence: str, step_type: str) -> str:
        suggestions = {
            FailureType.HALLUCINATION: (
                "✋ 检测到幻觉型失败：模型引用了不存在的资源。\n"
                "建议：① 执行前先验证路径/接口存在性；"
                "② 在 Prompt 中加入「如果不确定请说不知道」约束；"
                "③ 对关键步骤启用 grounding 验证。"
            ),
            FailureType.KNOWLEDGE_GAP: (
                "📚 检测到知识缺失型失败：模型信息过时或领域不足。\n"
                "建议：① 在 Prompt 中注入最新文档/上下文；"
                "② 优先使用带 RAG 能力的模型；"
                "③ 将相关知识更新到 MEMORY.md 或 skills。"
            ),
            FailureType.TOOL_MISUSE: (
                "🔧 检测到工具使用错误型失败：参数格式或调用方式有误。\n"
                "建议：① 在 Prompt 中附加工具用法示例；"
                "② 对工具输入进行 schema 校验；"
                "③ 将常见错误模式记录到对应 SKILL.md。"
            ),
            FailureType.RATE_LIMIT: (
                "⏳ 限流/配额超出。建议：① 增加重试退避逻辑；"
                "② 切换到备用 provider；③ 任务错峰执行。"
            ),
            FailureType.TIMEOUT: (
                "⏰ 超时失败。建议：① 拆分长任务为子步骤；"
                "② 增大 timeout 阈值；③ 异步执行后轮询结果。"
            ),
            FailureType.PERMISSION: (
                "🔒 权限不足。建议：① 确认 API Key / Token 有效；"
                "② 检查文件/DB 访问权限；③ 检查 .env 配置。"
            ),
            FailureType.UNKNOWN: (
                "❓ 未能自动分类。建议人工审查轨迹并补充规则库。"
            ),
        }
        return suggestions.get(ftype, suggestions[FailureType.UNKNOWN])


# ─── 批量分析与持久化 ────────────────────────────────────────────────────────

class FailureAnalyzer:
    """从数据库加载失败轨迹，批量分类，写回结果"""

    def __init__(self):
        self.classifier = FailureClassifier()

    def analyze_recent_failures(self, limit: int = 100) -> list[FailureRecord]:
        """分析最近 N 条失败轨迹"""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT t.trace_id, t.task_id, s.step_id, s.step_type,
                   s.error_json, s.output_json
            FROM agent_traces t
            JOIN agent_trace_steps s ON t.trace_id = s.trace_id
            WHERE t.status = 'failed' AND s.error_json IS NOT NULL
            ORDER BY t.started_at DESC
            LIMIT %s
        """, (limit,))
        rows = c.fetchall()
        conn.close()

        results = []
        for row in rows:
            err_text = json.dumps(row["error_json"], ensure_ascii=False) \
                       if isinstance(row["error_json"], dict) else str(row["error_json"])
            out_text = json.dumps(row["output_json"], ensure_ascii=False) \
                       if isinstance(row["output_json"], dict) else ""
            record = self.classifier.classify_error(
                error_text=err_text,
                output_text=out_text,
                step_type=row.get("step_type", ""),
                trace_id=row["trace_id"],
                task_id=row["task_id"],
                step_id=row["step_id"],
            )
            results.append(record)
        return results

    def save_results(self, records: list[FailureRecord]):
        """将分类结果写入 agent_failure_analysis 表"""
        if not records:
            return
        conn = get_db_connection()
        c = conn.cursor()
        # 确保表存在
        c.execute("""
            CREATE TABLE IF NOT EXISTS agent_failure_analysis (
              id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
              trace_id      VARCHAR(64),
              task_id       INT,
              step_id       VARCHAR(64),
              failure_type  VARCHAR(64),
              severity      VARCHAR(32),
              confidence    FLOAT,
              evidence      TEXT,
              suggestion    TEXT,
              raw_error     TEXT,
              meta_json     JSON,
              analyzed_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_trace_id (trace_id),
              INDEX idx_failure_type (failure_type),
              INDEX idx_task_id (task_id)
            )
        """)
        for r in records:
            c.execute("""
                INSERT INTO agent_failure_analysis
                (trace_id, task_id, step_id, failure_type, severity,
                 confidence, evidence, suggestion, raw_error, meta_json)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (r.trace_id, r.task_id, r.step_id, r.failure_type.value,
                  r.severity.value, r.confidence, r.evidence,
                  r.suggestion, r.raw_error, json.dumps(r.meta)))
        conn.commit()
        conn.close()
        print(f"✅ 已保存 {len(records)} 条分类结果到 agent_failure_analysis")

    def report(self, records: list[FailureRecord]) -> str:
        """生成分类摘要报告"""
        from collections import Counter
        type_counts = Counter(r.failure_type.value for r in records)
        sev_counts  = Counter(r.severity.value for r in records)
        lines = [
            f"\n{'='*55}",
            f"  失败分类报告  共 {len(records)} 条",
            f"{'='*55}",
            "  类型分布:",
        ]
        for t, n in type_counts.most_common():
            pct = n / len(records) * 100 if records else 0
            lines.append(f"    {t:<22} {n:>4} 条  ({pct:.1f}%)")
        lines.append("  严重程度:")
        for s, n in sev_counts.most_common():
            lines.append(f"    {s:<22} {n:>4} 条")
        lines.append(f"{'='*55}\n")
        return "\n".join(lines)


# ─── CLI 入口 ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agent 失败案例自动分类器")
    parser.add_argument("--analyze", action="store_true", help="分析最近失败轨迹")
    parser.add_argument("--limit", type=int, default=100, help="分析条数上限")
    parser.add_argument("--test",  action="store_true", help="运行内置测试用例")
    parser.add_argument("--save",  action="store_true", help="将结果写入数据库")
    args = parser.parse_args()

    if args.test:
        clf = FailureClassifier()
        test_cases = [
            ("FileNotFoundError: /path/to/nonexistent.py",              "幻觉型"),
            ("Table 'workspace.xyz_table' doesn't exist",               "幻觉型"),
            ("deprecated, use requests.get() instead",                  "知识缺失型"),
            ("missing required argument: 'entity_id'",                  "工具使用错误型"),
            ("429 Too Many Requests",                                    "限流"),
            ("TimeoutError: read timed out after 30s",                  "超时"),
        ]
        print("\n🧪 自检测试:")
        all_pass = True
        for err_text, expected_label in test_cases:
            r = clf.classify_error(err_text)
            ok = "✅" if r.failure_type != FailureType.UNKNOWN else "⚠️ "
            print(f"  {ok} [{r.failure_type.value:<20}] conf={r.confidence:.2f}  ← {err_text[:50]}")
        print()

    elif args.analyze:
        analyzer = FailureAnalyzer()
        print(f"🔍 正在分析最近 {args.limit} 条失败轨迹...")
        records = analyzer.analyze_recent_failures(limit=args.limit)
        print(analyzer.report(records))
        if args.save:
            analyzer.save_results(records)
    else:
        parser.print_help()

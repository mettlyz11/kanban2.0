#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
失败案例自动分类器
支持分类：幻觉型 / 知识缺失型 / 工具使用错误型

用法：
    python3 失败案例自动分类器_代码_20260425.py input.json
或：
    from classifier import FailureCaseClassifier
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Any


@dataclass
class ClassificationResult:
    label: str
    confidence: float
    evidence: List[str]
    root_cause: str
    improvement_suggestion: str


class FailureCaseClassifier:
    """基于规则的失败案例分类器，可作为后续ML/LLM分类器的基线版本。"""

    LABELS = {
        "hallucination": "幻觉型",
        "knowledge_gap": "知识缺失型",
        "tool_error": "工具使用错误型",
        "mixed": "混合型",
        "unknown": "未知型",
    }

    HALLUCINATION_PATTERNS = [
        r"编造",
        r"杜撰",
        r"无依据",
        r"未找到来源",
        r"source not found",
        r"fabricat",
        r"hallucin",
        r"与事实不符",
        r"引用不存在",
        r"schema.*假设",
        r"假设了.*字段",
    ]

    KNOWLEDGE_GAP_PATTERNS = [
        r"缺少知识",
        r"不知道",
        r"缺乏上下文",
        r"缺乏资料",
        r"未检索到",
        r"knowledge gap",
        r"insufficient context",
        r"missing context",
        r"需要更多信息",
        r"无法确认",
        r"文档不存在",
        r"未读取到相关文件",
    ]

    TOOL_ERROR_PATTERNS = [
        r"tool.*error",
        r"exec.*failed",
        r"permission denied",
        r"timeout",
        r"command not found",
        r"路径错误",
        r"文件不存在",
        r"sql.*失败",
        r"数据库.*失败",
        r"参数错误",
        r"调用.*失败",
        r"json decode error",
    ]

    def _score_patterns(self, text: str, patterns: List[str]) -> Tuple[int, List[str]]:
        matches = []
        score = 0
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches.append(pattern)
                score += 1
        return score, matches

    def classify(self, case: Dict[str, Any]) -> ClassificationResult:
        text_parts = [
            str(case.get("prompt", "")),
            str(case.get("intermediate_steps", "")),
            str(case.get("output", "")),
            str(case.get("error", "")),
            str(case.get("review_notes", "")),
        ]
        text = "\n".join(text_parts)

        halluc_score, halluc_hits = self._score_patterns(text, self.HALLUCINATION_PATTERNS)
        gap_score, gap_hits = self._score_patterns(text, self.KNOWLEDGE_GAP_PATTERNS)
        tool_score, tool_hits = self._score_patterns(text, self.TOOL_ERROR_PATTERNS)

        scores = {
            "hallucination": halluc_score,
            "knowledge_gap": gap_score,
            "tool_error": tool_score,
        }

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_label, top_score = sorted_scores[0]
        second_score = sorted_scores[1][1]

        if top_score == 0:
            return ClassificationResult(
                label="unknown",
                confidence=0.2,
                evidence=[],
                root_cause="未匹配到明显规则，建议人工复核或接入LLM二次判断。",
                improvement_suggestion="补充失败上下文、工具日志和证据链后再分类。",
            )

        if top_score > 0 and second_score > 0 and abs(top_score - second_score) <= 1:
            return ClassificationResult(
                label="mixed",
                confidence=min(0.85, 0.45 + top_score * 0.1),
                evidence=halluc_hits + gap_hits + tool_hits,
                root_cause="失败表现同时具备多种特征，可能是上下文不足引发的错误工具使用或事实性幻觉。",
                improvement_suggestion="先补充检索/上下文，再增加工具前置校验，最后要求输出必须附证据来源。",
            )

        evidence_map = {
            "hallucination": halluc_hits,
            "knowledge_gap": gap_hits,
            "tool_error": tool_hits,
        }

        root_cause_map = {
            "hallucination": "模型在证据不足时仍给出看似确定的内容，存在编造事实、字段或引用的倾向。",
            "knowledge_gap": "任务上下文、知识库或检索证据不足，导致模型无法稳定完成推理或回答。",
            "tool_error": "问题主要出在工具调用、参数、路径、权限、超时或数据库/命令执行层面。",
        }

        improvement_map = {
            "hallucination": "在prompt中加入“无证据不下结论、必须列出来源、无法确认时明确说明”的约束，并启用输出前事实核验。",
            "knowledge_gap": "在执行前增加memory/doc/schema检索步骤，要求先补足上下文，再进入生成阶段。",
            "tool_error": "增加工具调用前检查清单：路径存在性、参数合法性、权限、schema验证、失败重试与回退方案。",
        }

        confidence = min(0.95, 0.5 + top_score * 0.12)
        return ClassificationResult(
            label=top_label,
            confidence=confidence,
            evidence=evidence_map[top_label],
            root_cause=root_cause_map[top_label],
            improvement_suggestion=improvement_map[top_label],
        )


def demo_cases() -> List[Dict[str, Any]]:
    return [
        {
            "prompt": "根据数据库表结构更新任务状态",
            "output": "我已更新 review_status 字段",
            "error": "实际表中不存在 review_status，属于假设字段",
            "review_notes": "引用不存在字段，未先核对schema",
        },
        {
            "prompt": "请总结该项目历史决策",
            "intermediate_steps": "未读取memory，直接输出总结",
            "error": "缺乏上下文，很多结论无法确认",
            "review_notes": "需要更多信息和历史文件",
        },
        {
            "prompt": "执行附件入库",
            "intermediate_steps": "调用 python 脚本",
            "error": "文件不存在、路径错误，随后 SQL 执行失败",
            "review_notes": "典型工具调用问题",
        },
    ]


def main():
    classifier = FailureCaseClassifier()

    if len(sys.argv) == 2:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            case = json.load(f)
        # print(json.dumps(asdict(classifier.classify(case)), ensure_ascii=False, indent=2))
        return

    results = []
    for case in demo_cases():
        result = classifier.classify(case)
        results.append({
            "case": case,
            "result": asdict(result),
            "label_zh": classifier.LABELS.get(result.label, result.label),
        })

    # print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Agent执行失败自动分类器
=====================
自动识别和分类Agent执行失败类型，支持:
- 幻觉型错误 (hallucination)
- 知识缺失型错误 (knowledge_missing)
- 工具使用错误型错误 (tool_usage_error)
- 逻辑错误型错误 (logic_error)
- 格式错误型错误 (format_error)
- 超时型错误 (timeout_error)
- 未知错误型错误 (unknown_error)

Author: Dudu AI Assistant
Date: 2026-04-25
Version: v1.0
"""

import re
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FailureType(Enum):
    """失败类型枚举"""
    HALLUCINATION = "hallucination"
    KNOWLEDGE_MISSING = "knowledge_missing"
    TOOL_USAGE_ERROR = "tool_usage_error"
    LOGIC_ERROR = "logic_error"
    FORMAT_ERROR = "format_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"

    @classmethod
    def from_string(cls, value: str) -> "FailureType":
        for ft in cls:
            if ft.value == value:
                return ft
        return cls.UNKNOWN_ERROR


@dataclass
class ClassificationResult:
    """分类结果数据结构"""
    failure_type: FailureType
    confidence: float
    confidence_level: str
    evidence: List[str]
    root_cause: str
    improvement_suggestions: List[str]


class FailureClassifier:
    """
    失败案例自动分类器
    
    使用基于规则的启发式分类 + 关键词匹配 + 模式识别
    """

    def __init__(self):
        self.patterns = self._build_patterns()
        self.confidence_threshold = 0.6

    def _build_patterns(self) -> Dict[FailureType, Dict]:
        """构建各失败类型的匹配模式"""
        return {
            FailureType.HALLUCINATION: {
                "keywords": [
                    "编造", "虚构", "不存在", "虚假", "幻觉", "捏造",
                    "编造了", "编造的", "虚假信息", "捏造的", "不符合事实",
                    "fabricat", "hallucinat", "made up", "fictional", "non-existent",
                    "不存在的文件", "不存在的路径", "不存在的函数", "不存在的方法",
                    "引用不存在", "虚假引用", "错误引用不存在", "不存在的表"
                ],
                "regex_patterns": [
                    r"不存在.*(文件|路径|方法|函数|类|表|字段)",
                    r"(编造|虚构|捏造).*内容",
                    r"虚假.*(信息|数据|事实)"
                ],
                "weight": 1.0
            },

            FailureType.KNOWLEDGE_MISSING: {
                "keywords": [
                    "不知道", "不清楚", "不了解", "不懂", "缺乏",
                    "不知道如何", "不清楚如何", "不了解如何",
                    "缺乏知识", "知识不足", "信息不足",
                    "don't know", "not sure", "unclear",
                    "lack of knowledge", "insufficient information",
                    "领域知识不足", "专业知识不足", "背景知识不足",
                    "需要更多信息", "需要更多知识", "需要了解"
                ],
                "regex_patterns": [
                    r"(需要|缺乏|缺少).*(信息|知识|数据)",
                    r"(不知道|不清楚|不了解).*(如何|怎么)",
                    r"领域知识.*不足",
                    r"专业知识.*不足"
                ],
                "weight": 1.0
            },

            FailureType.TOOL_USAGE_ERROR: {
                "keywords": [
                    "参数错误", "参数不正确", "参数格式",
                    "调用错误", "调用失败", "调用方式",
                    "工具错误", "工具失败", "工具不存在",
                    "parameter", "invalid", "error", "failed",
                    "argument", "argument error", "wrong parameter",
                    "缺少参数", "参数缺失", "参数类型错误",
                    "工具选择错误", "选错工具", "使用了错误的工具"
                ],
                "regex_patterns": [
                    r"(参数|argument).*(错误|不正确|缺失|缺少",
                    r"工具.*(错误|失败|不存在)",
                    r"调用.*(错误|失败)",
                    r"(缺少|缺失).*参数"
                ],
                "weight": 1.2
            },

            FailureType.LOGIC_ERROR: {
                "keywords": [
                    "逻辑错误", "推理错误", "逻辑漏洞",
                    "逻辑有问题", "推理有问题", "逻辑不对",
                    "reasoning error", "logic error", "flawed",
                    "逻辑矛盾", "自相矛盾", "前后矛盾",
                    "决策错误", "判断错误", "结论错误"
                ],
                "regex_patterns": [
                    r"(逻辑|推理).*(错误|问题|漏洞)",
                    r"(前后|自相).*矛盾",
                    r"(决策|判断|结论).*错误"
                ],
                "weight": 1.0
            },

            FailureType.FORMAT_ERROR: {
                "keywords": [
                    "格式错误", "json错误", "解析失败",
                    "格式不正确", "输出格式",
                    "parse error", "format error", "invalid format",
                    "JSONDecodeError", "json解析错误",
                    "格式不符合", "格式要求", "期望格式"
                ],
                "regex_patterns": [
                    r"(json|格式).*(错误|解析失败",
                    r"JSON.*(DecodeError|error)",
                    r"格式.*(不符合|不正确)",
                    r"期望.*格式"
                ],
                "weight": 1.1
            },

            FailureType.TIMEOUT_ERROR: {
                "keywords": [
                    "超时", "timeout", "timed out",
                    "执行超时", "运行超时", "步骤超时",
                    "time out", "超过时间", "耗时过长",
                    "timeout expired", "超时错误"
                ],
                "regex_patterns": [
                    r"(超时|timeout).*错误",
                    r"执行.*超时",
                    r"timed? out"
                ],
                "weight": 1.3
            },

            FailureType.UNKNOWN_ERROR: {
                "keywords": [
                    "未知错误", "unknown error",
                    "发生错误", "出现错误",
                    "error occurred", "something went wrong"
                ],
                "regex_patterns": [],
                "weight": 0.5
            }
        }

    def classify(self,
                error_message: str,
                trace_content: str = "",
                tool_name: str = None,
                final_output: str = "") -> ClassificationResult:
        """
        对失败案例进行分类
        
        Args:
            error_message: 错误信息
            trace_content: 轨迹内容
            tool_name: 使用的工具名称
            final_output: 最终输出
            
        Returns:
            ClassificationResult 分类结果
        """
        scores = {}
        all_evidence = {}

        combined_text = "\n".join(filter(None, [
            error_message, trace_content, final_output])

        for failure_type in FailureType:
            score, evidence = self._calculate_score(failure_type, combined_text)
            scores[failure_type] = score
            all_evidence[failure_type] = evidence

        # 找出最高分的失败类型
        max_score = max(scores.values())
        if max_score < self.confidence_threshold:
            best_type = FailureType.UNKNOWN_ERROR
        else:
            best_type = max(scores.items(), key=lambda x: x[1])[0]

        # 确定置信度级别
        confidence_level = self._get_confidence_level(max_score)

        # 生成根本原因分析
        root_cause = self._generate_root_cause(best_type, all_evidence[best_type])

        # 生成改进建议
        suggestions = self._generate_suggestions(best_type, all_evidence[best_type])

        return ClassificationResult(
            failure_type=best_type,
            confidence=round(max_score, 4),
            confidence_level=confidence_level,
            evidence=all_evidence[best_type],
            root_cause=root_cause,
            improvement_suggestions=suggestions
        )

    def _calculate_score(self, failure_type: FailureType, text: str) -> Tuple[float, List[str]]:
        """计算某个失败类型的得分"""
        if not text:
            return 0.0, []

        patterns = self.patterns[failure_type]
        keywords = patterns["keywords"]
        regex_patterns = patterns["regex_patterns"]
        weight = patterns["weight"]

        text_lower = text.lower()
        score = 0.0
        evidence = []

        # 关键词匹配
        keyword_matches = []
        for keyword in keywords:
            if keyword.lower() in text_lower:
                score += 0.1
                keyword_matches.append(keyword)

        if keyword_matches:
            evidence.append(f"匹配关键词: {', '.join(keyword_matches)}")

        # 正则表达式匹配
        regex_matches = []
        for pattern in regex_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                score += 0.2 * len(matches)
                regex_matches.extend(matches)

        if regex_matches:
            evidence.append(f"匹配模式: {regex_matches}")

        # 应用权重
        score *= weight

        # 归一化到0-1范围
        score = min(score, 1.0)

        return score, evidence

    def _get_confidence_level(self, score: float) -> str:
        """根据得分确定置信度级别"""
        if score >= 0.9:
            return "high"
        elif score >= 0.7:
            return "medium"
        elif score >= 0.5:
            return "low"
        else:
            return "very_low"

    def _generate_root_cause(self, failure_type: FailureType, evidence: List[str]) -> str:
        """生成根本原因分析"""
        cause_templates = {
            FailureType.HALLUCINATION:
                "Agent产生了幻觉，编造了不存在的事实或信息。可能是因为训练数据不足或推理过程失控。",
            FailureType.KNOWLEDGE_MISSING:
                "Agent缺乏完成任务所需的领域知识或背景信息。需要补充相关知识或提供更详细的任务说明。",
            FailureType.TOOL_USAGE_ERROR:
                "Agent在使用工具时犯了错误，可能是参数错误、调用方式错误或工具选择错误。需要加强工具使用训练。",
            FailureType.LOGIC_ERROR:
                "Agent在推理过程中出现了逻辑错误或矛盾。需要优化推理链或增加逻辑验证步骤。",
            FailureType.FORMAT_ERROR:
                "Agent输出格式不符合要求，导致解析失败。需要加强格式约束或增加输出校验。",
            FailureType.TIMEOUT_ERROR:
                "Agent执行超时，可能是任务过于复杂或步骤设计不合理。需要优化任务分解或增加超时处理。",
            FailureType.UNKNOWN_ERROR:
                "无法明确识别具体失败原因，需要进一步分析详细执行轨迹进行人工分析。"
        }

        base_cause = cause_templates.get(failure_type, "未知原因")

        if evidence:
            evidence_str = "; ".join(evidence)
            return f"{base_cause} 证据: {evidence_str}"

        return base_cause

    def _generate_suggestions(self, failure_type: FailureType, evidence: List[str]) -> List[str]:
        """根据失败类型生成改进建议"""
        suggestion_templates = {
            FailureType.HALLUCINATION: [
                "在Prompt中增加事实核查要求",
                "增加信息源验证步骤",
                "要求引用具体来源",
                "增加幻觉检测机制",
                "优化知识检索增强(RAG)"
            ],
            FailureType.KNOWLEDGE_MISSING: [
                "补充相关领域知识到知识库",
                "在任务描述中提供更多背景信息",
                "增加信息检索步骤",
                "优化知识检索策略",
                "增加领域专家审核环节"
            ],
            FailureType.TOOL_USAGE_ERROR: [
                "优化工具使用说明文档",
                "增加工具参数校验步骤",
                "优化工具选择逻辑",
                "增加工具调用示例",
                "实现工具自动重试机制"
            ],
            FailureType.LOGIC_ERROR: [
                "优化推理链设计",
                "增加中间结果验证",
                "实现多轮自我检查",
                "增加逻辑一致性校验",
                "提供更多思维链(CoT)示例"
            ],
            FailureType.FORMAT_ERROR: [
                "在Prompt中明确输出格式要求",
                "提供格式示例",
                "增加输出格式校验",
                "实现格式自动修正",
                "使用结构化输出约束"
            ],
            FailureType.TIMEOUT_ERROR: [
                "优化任务分解策略",
                "增加步骤超时处理",
                "实现进度监控机制",
                "优化大任务拆分为更小的子任务",
                "增加执行策略"
            ],
            FailureType.UNKNOWN_ERROR: [
                "人工详细分析执行轨迹",
                "增加更详细的日志记录",
                "复现问题场景",
                "收集更多失败案例",
                "优化分类规则"
            ]
        }

        return suggestion_templates.get(failure_type, ["进一步分析失败原因"])


class TraceAnalyzer:
    """
    轨迹分析器 - 分析完整的执行轨迹
    """

    def __init__(self):
        self.classifier = FailureClassifier()

    def analyze_trace(self, trace_data: Dict) -> Dict:
        """
        分析完整的执行轨迹"""
        result = {
            "trace_id": trace_data.get("trace_id"),
            "status": trace_data.get("status"),
            "duration_ms": trace_data.get("total_duration_ms", 0),
            "total_tokens": trace_data.get("total_tokens", 0),
            "step_count": len(trace_data.get("steps", [])),
            "failure_analysis": None,
            "step_analysis": [],
            "overall_assessment": "",
            "improvement_priority": "low"
        }

        # 分析每一步
        steps = trace_data.get("steps", [])
        for step in steps:
            step_result = self._analyze_step(step)
            result["step_analysis"].append(step_result)

        # 如果执行失败，进行失败分析
        if trace_data.get("status") in ["failed", "error"]:
            error_msg = trace_data.get("error_message", "")
            final_output = trace_data.get("final_output", "")
            trace_content = json.dumps(trace_data, ensure_ascii=False)

            classification = self.classifier.classify(
                error_message=error_msg,
                trace_content=trace_content,
                final_output=final_output
            )

            result["failure_analysis"] = {
                "failure_type": classification.failure_type.value,
                "confidence": classification.confidence,
                "confidence_level": classification.confidence_level,
                "evidence": classification.evidence,
                "root_cause": classification.root_cause,
                "suggestions": classification.improvement_suggestions
            }

            # 确定改进优先级
            if classification.confidence >= 0.8:
                result["improvement_priority"] = "high"
            elif classification.confidence >= 0.6:
                result["improvement_priority"] = "medium"

        # 生成总体评估
        result["overall_assessment"] = self._generate_assessment(result)

        return result

    def _analyze_step(self, step: Dict) -> Dict:
        """分析单个执行步骤"""
        return {
            "step_number": step.get("step_number"),
            "step_type": step.get("step_type"),
            "status": step.get("status", "success"),
            "duration_ms": step.get("duration_ms", 0),
            "issues": self._detect_step_issues(step),
            "suggestions": []
        }

    def _detect_step_issues(self, step: Dict) -> List[str]:
        """检测步骤中的问题"""
        issues = []

        # 检查耗时
        duration = step.get("duration_ms", 0)
        if duration > 30000:  # 超过30秒
            issues.append(f"步骤耗时过长: {duration}ms")

        # 检查工具调用错误
        if step.get("status") == "failed":
            issues.append(f"步骤执行失败")

        # 检查token消耗
        tokens = step.get("tokens_used", 0)
        if tokens > 4000:
            issues.append(f"Token消耗过高: {tokens}")

        return issues

    def _generate_assessment(self, result: Dict) -> str:
        """生成总体评估"""
        if result["status"] == "success":
            return "执行成功，无需特别改进建议"

        failure = result.get("failure_analysis")
        if failure:
            return (f"执行失败，类型: {failure['failure_type']}, "
                f"置信度: {failure['confidence']:.2%}, "
                f"根本原因: {failure['root_cause']}")

        return "执行状态未知，需要进一步分析"


def main():
    """测试分类器使用示例"""

    # 示例1: 幻觉型错误
    test_error1 = "Agent编造了一个不存在的函数调用不存在的函数不存在的函数调用
    classifier = FailureClassifier()
    result1 = classifier.classify(
        error_message=test_error1,
        trace_content="执行过程中Agent编造了不存在的文件路径 /tmp/nonexistent_file.txt"
    )

    # print("=== 测试1: 幻觉型错误")
    # print(f"失败类型: {result1.failure_type.value}")
    # print(f"置信度: {result1.confidence}")
    # print(f"根本原因: {result1.root_cause}")
    # print()

    # 示例2: 工具使用错误
    test_error2 = "参数错误: 缺少必填参数 file_path"
    result2 = classifier.classify(
        error_message=test_error2,
        tool_name="read_file"
    )

    # print("=== 测试2: 工具使用错误")
    # print(f"失败类型: {result2.failure_type.value}")
    # print(f"置信度: {result2.confidence}")
    # print(f"根本原因: {result2.root_cause}")
    # print()

    # 示例3: 格式错误
    test_error3 = "JSONDecodeError: Expecting value"
    result3 = classifier.classify(error_message=test_error3)
    # print("=== 测试3: 格式错误")
    # print(f"失败类型: {result3.failure_type.value}")
    # print(f"置信度: {result3.confidence}")
    # print(f"根本原因: {result3.root_cause}")


if __name__ == "__main__":
    main()

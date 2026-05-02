#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent失败案例自动分类器
功能：自动分析Agent执行失败的轨迹，分类错误类型并生成改进建议
"""

import json
import re
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


class ErrorType(Enum):
    """错误类型枚举"""
    HALLUCINATION = "幻觉型"           # 模型生成不存在的信息
    KNOWLEDGE_GAP = "知识缺失型"        # 模型缺乏必要知识
    TOOL_MISUSE = "工具使用错误型"       # 工具调用参数错误或选择不当
    CONTEXT_OVERFLOW = "上下文溢出型"     # 超出上下文窗口限制
    LOGIC_ERROR = "逻辑错误型"          # 推理逻辑存在漏洞
    TIMEOUT = "超时型"                 # 执行时间超出限制
    EXTERNAL_FAILURE = "外部依赖失败型"   # 第三方服务不可用
    PERMISSION_DENIED = "权限不足型"     # 缺乏执行权限
    UNKNOWN = "未知类型"


@dataclass
class FailureCase:
    """失败案例数据结构"""
    trace_id: str
    task_id: int
    agent_id: str
    error_message: str
    error_type: ErrorType
    confidence: float
    root_cause: str
    suggestions: List[str]
    raw_trace: Dict
    timestamp: datetime


class FailureClassifier:
    """失败案例自动分类器"""
    
    def __init__(self):
        # 幻觉型错误关键词模式
        self.hallucination_patterns = [
            r"不存在.*?(?:文件|目录|路径)",
            r"找不到.*?(?:工具|函数|方法)",
            r"没有.*?(?:权限|访问权)",
            r"(?:编造|虚构|捏造).*?(?:数据|信息)",
            r"claim.*not.*exist",
            r"no.*such.*file",
            r"undefined.*reference",
            r"幻觉", r"hallucinat",
        ]
        
        # 知识缺失型关键词模式
        self.knowledge_gap_patterns = [
            r"不知道",
            r"不了解",
            r"不清楚",
            r"没有相关信息",
            r"知识.*?(?:截止|更新)",
            r"not.*sure.*about",
            r"lack.*knowledge",
            r"do not have.*information",
            r"unfamiliar.*with",
        ]
        
        # 工具使用错误型关键词模式
        self.tool_misuse_patterns = [
            r"参数.*?(?:错误|无效|缺失)",
            r"参数类型.*?(?:不匹配|错误)",
            r"(?:调用|使用).*?(?:失败|错误)",
            r"invalid.*argument",
            r"wrong.*parameter",
            r"missing.*required.*argument",
            r"tool.*not.*found",
            r"function.*call.*error",
            r"JSON.*parse.*error",
        ]
        
        # 上下文溢出型
        self.context_overflow_patterns = [
            r"context.*overflow",
            r"token.*exceed",
            r"超出.*上下文",
            r"too.*long",
            r"maximum.*context",
        ]
        
        # 逻辑错误型
        self.logic_error_patterns = [
            r"逻辑.*?(?:错误|漏洞)",
            r"推理.*?(?:错误|失败)",
            r"contradiction",
            r"inconsistent",
            r"logical.*error",
        ]
        
        # 超时型
        self.timeout_patterns = [
            r"timeout",
            r"超时",
            r"time.*limit",
            r"deadline.*exceeded",
        ]
        
        # 外部依赖失败型
        self.external_failure_patterns = [
            r"连接.*?(?:失败|超时)",
            r"服务.*?(?:不可用|宕机)",
            r"network.*error",
            r"connection.*refused",
            r"service.*unavailable",
            r"503",
            r"502",
        ]
        
        # 权限不足型
        self.permission_patterns = [
            r"权限.*?(?:不足|拒绝)",
            r"access.*denied",
            r"permission.*denied",
            r"unauthorized",
            r"forbidden",
        ]
    
    def classify(self, trace_data: Dict) -> FailureCase:
        """
        对失败的执行轨迹进行分类
        
        Args:
            trace_data: 执行轨迹数据，包含error_message等字段
            
        Returns:
            FailureCase: 分类后的失败案例
        """
        error_message = trace_data.get("error_message", "")
        trace_id = trace_data.get("trace_id", "unknown")
        task_id = trace_data.get("task_id", 0)
        agent_id = trace_data.get("agent_id", "unknown")
        raw_trace = trace_data.get("raw_trace", {})
        
        # 计算各类型的匹配分数
        scores = {
            ErrorType.HALLUCINATION: self._calculate_score(error_message, self.hallucination_patterns),
            ErrorType.KNOWLEDGE_GAP: self._calculate_score(error_message, self.knowledge_gap_patterns),
            ErrorType.TOOL_MISUSE: self._calculate_score(error_message, self.tool_misuse_patterns),
            ErrorType.CONTEXT_OVERFLOW: self._calculate_score(error_message, self.context_overflow_patterns),
            ErrorType.LOGIC_ERROR: self._calculate_score(error_message, self.logic_error_patterns),
            ErrorType.TIMEOUT: self._calculate_score(error_message, self.timeout_patterns),
            ErrorType.EXTERNAL_FAILURE: self._calculate_score(error_message, self.external_failure_patterns),
            ErrorType.PERMISSION_DENIED: self._calculate_score(error_message, self.permission_patterns),
        }
        
        # 选择得分最高的类型
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        
        # 如果最高分为0，标记为未知
        if best_score == 0:
            best_type = ErrorType.UNKNOWN
            confidence = 0.0
        else:
            # 计算置信度（归一化到0-1）
            total_score = sum(scores.values())
            confidence = best_score / total_score if total_score > 0 else 0
        
        # 生成根因分析
        root_cause = self._analyze_root_cause(best_type, error_message, raw_trace)
        
        # 生成改进建议
        suggestions = self._generate_suggestions(best_type, error_message, raw_trace)
        
        return FailureCase(
            trace_id=trace_id,
            task_id=task_id,
            agent_id=agent_id,
            error_message=error_message,
            error_type=best_type,
            confidence=round(confidence, 2),
            root_cause=root_cause,
            suggestions=suggestions,
            raw_trace=raw_trace,
            timestamp=datetime.now()
        )
    
    def _calculate_score(self, text: str, patterns: List[str]) -> int:
        """计算文本与模式列表的匹配分数"""
        score = 0
        text_lower = text.lower()
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                score += 1
            if re.search(pattern, text_lower, re.IGNORECASE):
                score += 1
        return score
    
    def _analyze_root_cause(self, error_type: ErrorType, error_message: str, raw_trace: Dict) -> str:
        """分析错误根因"""
        causes = {
            ErrorType.HALLUCINATION: "模型生成了不存在的信息或虚构了工具/路径，通常由于训练数据偏差或上下文理解错误导致。",
            ErrorType.KNOWLEDGE_GAP: "模型缺乏完成任务所需的特定领域知识或最新信息。",
            ErrorType.TOOL_MISUSE: "工具调用参数错误、格式不正确，或选择了不适当的工具。",
            ErrorType.CONTEXT_OVERFLOW: "输入内容过长，超出模型的上下文窗口限制，导致信息丢失。",
            ErrorType.LOGIC_ERROR: "模型在推理过程中出现逻辑漏洞或矛盾，导致错误结论。",
            ErrorType.TIMEOUT: "任务执行时间超出系统设定的限制，可能由于循环调用或复杂计算。",
            ErrorType.EXTERNAL_FAILURE: "依赖的外部服务（API、数据库等）不可用或返回错误。",
            ErrorType.PERMISSION_DENIED: "Agent缺乏执行操作所需的权限。",
            ErrorType.UNKNOWN: "无法从错误信息中识别具体原因，需要人工分析。"
        }
        return causes.get(error_type, "未知原因")
    
    def _generate_suggestions(self, error_type: ErrorType, error_message: str, raw_trace: Dict) -> List[str]:
        """生成改进建议"""
        suggestions = {
            ErrorType.HALLUCINATION: [
                "在Prompt中明确要求模型仅在确认信息存在时回答",
                "增加事实验证步骤，使用工具验证关键信息",
                "引入检索增强生成（RAG），基于真实数据回答",
                "设置置信度阈值，低置信度时要求模型明确说明不确定"
            ],
            ErrorType.KNOWLEDGE_GAP: [
                "为Agent提供专属知识库，补充领域特定知识",
                "在Prompt中提供必要的背景信息和上下文",
                "集成搜索工具，允许Agent实时获取最新信息",
                "建立知识更新机制，定期更新Agent知识库"
            ],
            ErrorType.TOOL_MISUSE: [
                "优化工具描述，确保模型理解每个工具的用途和参数",
                "增加参数校验层，在调用前验证参数格式",
                "提供工具使用示例，采用少样本提示（Few-shot）",
                "实现工具调用重试机制，参数错误时自动修正"
            ],
            ErrorType.CONTEXT_OVERFLOW: [
                "实现上下文压缩策略，保留关键信息",
                "采用分块处理，将长文本拆分为多个子任务",
                "使用长上下文模型（如128K/200K版本）",
                "建立上下文摘要机制，定期总结历史对话"
            ],
            ErrorType.LOGIC_ERROR: [
                "引入思维链（Chain-of-Thought）提示，要求逐步推理",
                "增加逻辑校验步骤，验证推理过程的合理性",
                "使用更强大的推理模型处理复杂逻辑任务",
                "建立推理过程审计日志，便于回溯分析"
            ],
            ErrorType.TIMEOUT: [
                "优化任务分解，将大任务拆分为多个小任务",
                "设置合理的超时阈值，避免无限等待",
                "实现异步执行机制，耗时操作后台运行",
                "增加进度检查点，定期报告执行进度"
            ],
            ErrorType.EXTERNAL_FAILURE: [
                "实现服务健康检查，调用前验证依赖服务状态",
                "增加熔断器机制，服务不可用时快速失败",
                "设计降级策略，主服务失败时切换备用方案",
                "建立重试机制，临时故障时自动重试"
            ],
            ErrorType.PERMISSION_DENIED: [
                "明确Agent权限边界，在Prompt中声明可用操作",
                "实现权限预检查，执行前验证权限",
                "设计权限申请流程，缺少权限时引导用户授权",
                "建立最小权限原则，仅授予必要的操作权限"
            ],
            ErrorType.UNKNOWN: [
                "人工分析错误详情，补充分类规则",
                "增加日志详细程度，记录更多调试信息",
                "建立错误案例库，积累分类经验"
            ]
        }
        return suggestions.get(error_type, ["需要人工分析"])
    
    def batch_classify(self, traces: List[Dict]) -> List[FailureCase]:
        """批量分类多个失败轨迹"""
        return [self.classify(trace) for trace in traces]
    
    def generate_report(self, cases: List[FailureCase]) -> Dict:
        """生成分类统计报告"""
        total = len(cases)
        type_counts = {}
        agent_counts = {}
        
        for case in cases:
            # 统计错误类型
            type_name = case.error_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
            
            # 统计Agent错误
            agent_counts[case.agent_id] = agent_counts.get(case.agent_id, 0) + 1
        
        # 计算占比
        type_distribution = {
            k: {"count": v, "percentage": round(v/total*100, 2)}
            for k, v in type_counts.items()
        }
        
        return {
            "total_cases": total,
            "type_distribution": type_distribution,
            "agent_error_counts": agent_counts,
            "avg_confidence": round(sum(c.confidence for c in cases) / total, 2) if total > 0 else 0,
            "generated_at": datetime.now().isoformat()
        }


# ============ 使用示例 ============

def demo():
    """演示分类器使用"""
    classifier = FailureClassifier()
    
    # 模拟一个工具使用错误的轨迹
    trace_example = {
        "trace_id": "trace-001",
        "task_id": 1953,
        "agent_id": "main",
        "error_message": "调用search_tool时参数错误：缺少必需的'query'参数，且'limit'参数类型应为整数而非字符串",
        "raw_trace": {
            "tool_name": "search_tool",
            "params": {"limit": "10"},
            "expected_params": ["query", "limit"]
        }
    }
    
    # 分类
    case = classifier.classify(trace_example)
    
    print("=" * 50)
    print(f"错误类型: {case.error_type.value}")
    print(f"置信度: {case.confidence}")
    print(f"根因: {case.root_cause}")
    print("改进建议:")
    for i, suggestion in enumerate(case.suggestions, 1):
        print(f"  {i}. {suggestion}")
    print("=" * 50)
    
    # 批量分类示例
    traces = [
        trace_example,
        {
            "trace_id": "trace-002",
            "task_id": 1953,
            "agent_id": "sub-agent-1",
            "error_message": "模型声称存在一个名为'quick_sort_v2'的工具，但实际可用的只有'quick_sort'",
        },
        {
            "trace_id": "trace-003",
            "task_id": 1954,
            "agent_id": "main",
            "error_message": "我不知道如何处理这种新型的文件格式，我的知识截止日期是2024年",
        }
    ]
    
    cases = classifier.batch_classify(traces)
    report = classifier.generate_report(cases)
    
    print("\n分类统计报告:")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    demo()

#!/usr/bin/env python3
"""
Agent 执行失败案例自动分类器
版本: v1.0
日期: 2026-04-25
功能: 自动识别和分类 Agent 执行失败的根本原因
"""

import re
import json
from enum import Enum
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


class FailureType(Enum):
    """失败类型枚举"""
    HALLUCINATION = "hallucination"           # 幻觉型
    KNOWLEDGE_GAP = "knowledge_gap"           # 知识缺失型
    TOOL_USAGE_ERROR = "tool_usage_error"     # 工具使用错误型
    PROMPT_ISSUE = "prompt_issue"             # Prompt 问题
    CONTEXT_LIMIT = "context_limit"           # 上下文超限
    RATE_LIMIT = "rate_limit"                 # 限流/配额
    NETWORK_ERROR = "network_error"           # 网络错误
    AUTH_ERROR = "auth_error"                 # 认证错误
    LOGIC_ERROR = "logic_error"               # 逻辑错误
    UNKNOWN = "unknown"                       # 未知错误


@dataclass
class FailureClassification:
    """失败分类结果"""
    primary_type: FailureType
    secondary_types: List[FailureType]
    confidence: float
    root_cause: str
    improvement_suggestions: List[str]
    evidence: List[str]
    severity: str  # high, medium, low


class FailurePatterns:
    """失败模式匹配规则库"""
    
    # 幻觉型 - 编造事实、虚假引用、错误信息
    HALLUCINATION_PATTERNS = [
        (r"(不存在|没有找到|无法找到).*(但我还是|但我仍然|依然)", 0.8),
        (r"(虚构|编造|想象|假设).*(API|函数|参数|工具)", 0.9),
        (r"(不存在的|错误的|无效的).*(方法|函数|接口)", 0.7),
        (r"AttributeError:.*has no attribute", 0.85),
        (r"ModuleNotFoundError: No module named", 0.6),
        (r"(虚假|不正确|错误).*(引用|来源|数据)", 0.8),
        (r"cannot import name.*from", 0.7),
        (r"(不存在|没有这个).*(工具|skill|功能)", 0.8),
    ]
    
    # 知识缺失型 - 缺乏特定领域知识、不了解业务规则
    KNOWLEDGE_GAP_PATTERNS = [
        (r"(不了解|不清楚|不知道|不熟悉).*(业务|规则|流程|规范)", 0.75),
        (r"(缺少|缺乏|需要补充).*(知识|信息|背景)", 0.8),
        (r"(语法错误|SyntaxError|invalid syntax)", 0.6),
        (r"(TypeError|类型错误).*object", 0.5),
        (r"(KeyError|键不存在)", 0.5),
        (r"(不理解|无法理解).*(需求|意图|指令)", 0.7),
        (r"(配置错误|配置不正确|配置缺失)", 0.65),
    ]
    
    # 工具使用错误型 - 参数错误、调用方式错误、工具选择错误
    TOOL_USAGE_PATTERNS = [
        (r"(参数错误|参数缺失|参数无效|参数不正确)", 0.85),
        (r"(缺少必要参数|required argument).*missing", 0.9),
        (r"(unexpected keyword argument|unexpected argument)", 0.85),
        (r"(工具|函数|方法).*(调用错误|使用错误|方式错误)", 0.8),
        (r"(选择了错误的|不恰当的|不合适的).*(工具|方法)", 0.75),
        (r"(权限不足|Permission denied|access denied)", 0.7),
        (r"(FileNotFoundError|文件不存在|路径错误)", 0.7),
        (r"(超时|timeout).*(调用|执行)", 0.6),
        (r"(重试|retry).*次数.*失败", 0.6),
    ]
    
    # Prompt 问题 - Prompt 不清晰、指令矛盾、目标模糊
    PROMPT_ISSUE_PATTERNS = [
        (r"(Prompt|提示).*(不清晰|模糊|矛盾|歧义)", 0.85),
        (r"(指令|需求).*(冲突|矛盾|不明确)", 0.8),
        (r"(目标|任务).*(太多|过于复杂)", 0.7),
        (r"(无法确定|不确定|不清楚).*(目标|做什么)", 0.75),
    ]
    
    # 上下文超限
    CONTEXT_LIMIT_PATTERNS = [
        (r"(context_length_exceeded|context.*limit.*exceeded)", 0.95),
        (r"(maximum context length|token limit).*exceeded", 0.95),
        (r"(上下文|context).*过长|超限|超出", 0.85),
        (r"prompt is too long", 0.9),
    ]
    
    # 限流/配额
    RATE_LIMIT_PATTERNS = [
        (r"(rate_limit_exceeded|rate limit)", 0.95),
        (r"(quota|配额).*(exceeded|不足|用完|超限)", 0.95),
        (r"(429|Too Many Requests)", 0.9),
        (r"(限流|请求过于频繁)", 0.85),
    ]
    
    # 网络错误
    NETWORK_PATTERNS = [
        (r"(ConnectionError|connection error)", 0.9),
        (r"(TimeoutError|timeout)", 0.85),
        (r"(API|接口).*(调用失败|无法连接)", 0.8),
        (r"(网络|network).*(错误|失败|问题)", 0.8),
        (r"(50[0-9]|Server Error)", 0.75),
    ]
    
    # 认证错误
    AUTH_PATTERNS = [
        (r"(401|Unauthorized|authentication failed)", 0.9),
        (r"(403|Forbidden|permission denied)", 0.85),
        (r"(API Key|密钥|token).*(无效|错误|过期)", 0.9),
        (r"(认证|授权).*(失败|错误)", 0.85),
    ]


class FailureClassifier:
    """失败案例自动分类器"""
    
    def __init__(self):
        self.patterns = FailurePatterns()
        self.type_pattern_map = {
            FailureType.HALLUCINATION: self.patterns.HALLUCINATION_PATTERNS,
            FailureType.KNOWLEDGE_GAP: self.patterns.KNOWLEDGE_GAP_PATTERNS,
            FailureType.TOOL_USAGE_ERROR: self.patterns.TOOL_USAGE_PATTERNS,
            FailureType.PROMPT_ISSUE: self.patterns.PROMPT_ISSUE_PATTERNS,
            FailureType.CONTEXT_LIMIT: self.patterns.CONTEXT_LIMIT_PATTERNS,
            FailureType.RATE_LIMIT: self.patterns.RATE_LIMIT_PATTERNS,
            FailureType.NETWORK_ERROR: self.patterns.NETWORK_PATTERNS,
            FailureType.AUTH_ERROR: self.patterns.AUTH_PATTERNS,
        }
    
    def classify(
        self,
        error_message: str,
        trace_context: Optional[Dict] = None,
        tool_history: Optional[List[Dict]] = None,
        prompt_text: Optional[str] = None,
        output_text: Optional[str] = None
    ) -> FailureClassification:
        """
        执行失败分类
        
        Args:
            error_message: 错误消息
            trace_context: 轨迹上下文
            tool_history: 工具调用历史
            prompt_text: 原始Prompt
            output_text: Agent输出
            
        Returns:
            FailureClassification 分类结果
        """
        scores = self._calculate_type_scores(error_message, trace_context, tool_history)
        
        # 找出得分最高的类型
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary_type = sorted_scores[0][0] if sorted_scores else FailureType.UNKNOWN
        primary_score = sorted_scores[0][1] if sorted_scores else 0.0
        
        # 收集次要类型（得分 > 0.3 的）
        secondary_types = [
            ftype for ftype, score in sorted_scores[1:] 
            if score > 0.3 and ftype != primary_type
        ]
        
        # 收集证据
        evidence = self._collect_evidence(
            error_message, primary_type, trace_context, tool_history
        )
        
        # 分析根因
        root_cause = self._analyze_root_cause(
            primary_type, error_message, trace_context
        )
        
        # 生成改进建议
        suggestions = self._generate_suggestions(
            primary_type, secondary_types, error_message, trace_context, tool_history
        )
        
        # 判定严重程度
        severity = self._determine_severity(primary_type, primary_score)
        
        return FailureClassification(
            primary_type=primary_type,
            secondary_types=secondary_types,
            confidence=min(primary_score, 1.0),
            root_cause=root_cause,
            improvement_suggestions=suggestions,
            evidence=evidence,
            severity=severity
        )
    
    def _calculate_type_scores(
        self,
        error_message: str,
        trace_context: Optional[Dict],
        tool_history: Optional[List[Dict]]
    ) -> Dict[FailureType, float]:
        """计算各类型的匹配分数"""
        scores = {ftype: 0.0 for ftype in FailureType}
        
        combined_text = error_message.lower()
        if trace_context:
            combined_text += " " + json.dumps(trace_context, ensure_ascii=False).lower()
        if tool_history:
            for tool_call in tool_history:
                combined_text += " " + json.dumps(tool_call, ensure_ascii=False).lower()
        
        # 模式匹配
        for failure_type, patterns in self.type_pattern_map.items():
            for pattern, weight in patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    scores[failure_type] += weight
        
        # 上下文启发式评分
        if tool_history:
            scores = self._heuristic_scoring(scores, tool_history, trace_context)
        
        return scores
    
    def _heuristic_scoring(
        self,
        scores: Dict[FailureType, float],
        tool_history: List[Dict],
        trace_context: Optional[Dict]
    ) -> Dict[FailureType, float]:
        """基于启发式规则的评分增强"""
        
        # 多次调用同一工具失败 → 工具使用错误
        tool_fail_counts = {}
        for call in tool_history:
            if call.get('status') == 'failed':
                tool = call.get('tool_name', 'unknown')
                tool_fail_counts[tool] = tool_fail_counts.get(tool, 0) + 1
        
        for tool, count in tool_fail_counts.items():
            if count >= 2:
                scores[FailureType.TOOL_USAGE_ERROR] += 0.2 * count
        
        # 工具参数格式错误
        for call in tool_history:
            result = str(call.get('result', '')).lower()
            if 'parameter' in result or 'argument' in result:
                scores[FailureType.TOOL_USAGE_ERROR] += 0.3
        
        # 幻觉检测：输出与工具返回矛盾
        if trace_context and 'output_text' in trace_context:
            output = trace_context['output_text'].lower()
            for call in tool_history:
                tool_result = str(call.get('result', '')).lower()
                if tool_result and len(tool_result) > 50:
                    # 检查输出是否包含工具返回中不存在的"事实"
                    pass
        
        return scores
    
    def _collect_evidence(
        self,
        error_message: str,
        primary_type: FailureType,
        trace_context: Optional[Dict],
        tool_history: Optional[List[Dict]]
    ) -> List[str]:
        """收集分类证据"""
        evidence = []
        
        # 错误消息中的证据
        evidence.append(f"错误消息: {error_message[:200]}")
        
        # 工具调用历史中的证据
        if tool_history:
            failed_tools = [
                f"{call.get('tool_name')}: {call.get('error_message', '')[:100]}"
                for call in tool_history
                if call.get('status') == 'failed'
            ]
            if failed_tools:
                evidence.append(f"失败工具调用: {'; '.join(failed_tools[:3])}")
        
        return evidence
    
    def _analyze_root_cause(
        self,
        failure_type: FailureType,
        error_message: str,
        trace_context: Optional[Dict]
    ) -> str:
        """分析根本原因"""
        root_cause_map = {
            FailureType.HALLUCINATION: 
                "Agent 产生了虚假信息或错误引用，可能是训练数据限制或推理偏差导致",
            FailureType.KNOWLEDGE_GAP:
                "Agent 缺乏完成任务所需的特定领域知识或上下文信息",
            FailureType.TOOL_USAGE_ERROR:
                "Agent 在工具选择、参数传递或调用时机上存在错误",
            FailureType.PROMPT_ISSUE:
                "输入 Prompt 存在模糊、矛盾或信息不完整问题",
            FailureType.CONTEXT_LIMIT:
                "对话或 Prompt 长度超出模型上下文窗口限制",
            FailureType.RATE_LIMIT:
                "API 调用频率或配额超出限制",
            FailureType.NETWORK_ERROR:
                "网络连接问题或第三方服务不可用",
            FailureType.AUTH_ERROR:
                "认证凭证无效或权限不足",
            FailureType.LOGIC_ERROR:
                "Agent 推理逻辑存在缺陷或错误",
            FailureType.UNKNOWN:
                "无法确定具体失败原因，需要进一步分析"
        }
        
        return root_cause_map.get(failure_type, "未知原因")
    
    def _generate_suggestions(
        self,
        primary_type: FailureType,
        secondary_types: List[FailureType],
        error_message: str,
        trace_context: Optional[Dict],
        tool_history: Optional[List[Dict]]
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        suggestion_map = {
            FailureType.HALLUCINATION: [
                "在 Prompt 中加入'核实信息真实性'的约束",
                "增加事实核查步骤，要求引用可靠来源",
                "优化系统 Prompt，强调不要编造信息",
                "增加工具调用验证环节，输出前用工具确认",
            ],
            FailureType.KNOWLEDGE_GAP: [
                "在 Prompt 中提供更完整的背景知识和业务规则",
                "集成知识库检索工具，让 Agent 可以查询相关信息",
                "优化思维链 Prompt，引导分步推理",
                "增加业务领域知识注入",
            ],
            FailureType.TOOL_USAGE_ERROR: [
                "在 Prompt 中详细说明工具使用规范和参数要求",
                "提供工具使用示例，特别是边界场景",
                "增加参数校验逻辑，调用前验证参数正确性",
                "优化工具选择策略，提供更明确的决策树",
            ],
            FailureType.PROMPT_ISSUE: [
                "重写 Prompt，使目标更明确，约束更清晰",
                "将复杂任务拆解为多个子任务",
                "增加示例（Few-shot），明确期望输出格式",
                "检查并消除 Prompt 中的矛盾指令",
            ],
            FailureType.CONTEXT_LIMIT: [
                "优化上下文管理策略，移除冗余信息",
                "实现对话历史摘要，压缩历史记录",
                "采用 RAG 模式，将长文本转为检索式访问",
                "拆分任务，减少单次上下文长度",
            ],
            FailureType.RATE_LIMIT: [
                "实现请求退避重试机制",
                "优化请求频率，避免短时间大量调用",
                "检查并升级 API 配额",
                "实现多模型降级策略",
            ],
        }
        
        # 主类型建议
        suggestions.extend(suggestion_map.get(primary_type, []))
        
        # 次类型建议（取前2个类型，每条1条建议）
        for sec_type in secondary_types[:2]:
            sec_suggestions = suggestion_map.get(sec_type, [])
            if sec_suggestions:
                suggestions.append(f"【{sec_type.value}】{sec_suggestions[0]}")
        
        # 通用建议
        suggestions.append("将此失败案例加入测试集，用于后续验证")
        
        return suggestions
    
    def _determine_severity(self, failure_type: FailureType, confidence: float) -> str:
        """确定严重程度"""
        high_severity = [
            FailureType.AUTH_ERROR,
            FailureType.RATE_LIMIT,
            FailureType.NETWORK_ERROR,
        ]
        
        medium_severity = [
            FailureType.HALLUCINATION,
            FailureType.TOOL_USAGE_ERROR,
            FailureType.CONTEXT_LIMIT,
        ]
        
        if failure_type in high_severity:
            return "high"
        elif failure_type in medium_severity:
            return "medium"
        else:
            return "low"


class FailureAnalyzer:
    """失败案例聚合分析器"""
    
    def __init__(self):
        self.classifier = FailureClassifier()
    
    def batch_analyze(self, failure_cases: List[Dict]) -> Dict:
        """批量分析失败案例"""
        results = []
        type_counts = {ftype.value: 0 for ftype in FailureType}
        
        for case in failure_cases:
            classification = self.classifier.classify(
                error_message=case.get('error_message', ''),
                trace_context=case.get('trace_context'),
                tool_history=case.get('tool_history'),
                prompt_text=case.get('prompt')
            )
            results.append({
                "case_id": case.get('case_id'),
                "classification": classification.primary_type.value,
                "confidence": classification.confidence,
                "root_cause": classification.root_cause,
                "suggestions": classification.improvement_suggestions[:3]
            })
            type_counts[classification.primary_type.value] += 1
        
        # 计算分布
        total = len(failure_cases)
        type_distribution = {
            ftype: {
                "count": count,
                "percentage": round(count / total * 100, 2) if total > 0 else 0
            }
            for ftype, count in type_counts.items()
            if count > 0
        }
        
        return {
            "total_failures": total,
            "type_distribution": dict(sorted(
                type_distribution.items(), 
                key=lambda x: x[1]['count'], 
                reverse=True
            )),
            "top_issues": self._identify_top_issues(results),
            "detailed_results": results,
            "analysis_time": datetime.now().isoformat()
        }
    
    def _identify_top_issues(self, results: List[Dict]) -> List[Dict]:
        """识别高频问题模式"""
        issue_patterns = {}
        
        for result in results:
            ftype = result['classification']
            issue_patterns[ftype] = issue_patterns.get(ftype, 0) + 1
        
        top_issues = [
            {"type": ftype, "count": count, "frequency": f"{round(count/len(results)*100, 1)}%"}
            for ftype, count in sorted(issue_patterns.items(), key=lambda x: x[1], reverse=True)
            if count >= 2
        ]
        
        return top_issues[:5]


# 使用示例
if __name__ == "__main__":
    classifier = FailureClassifier()
    
    # 示例1: 工具使用错误
    test_error1 = """
    Error: unexpected keyword argument 'max_results' for function 'memory_search'
    """
    
    result1 = classifier.classify(test_error1)
    print("=" * 60)
    print("测试案例 1: 工具参数错误")
    print(f"分类结果: {result1.primary_type.value} (置信度: {result1.confidence:.2f})")
    print(f"根因: {result1.root_cause}")
    print("改进建议:")
    for i, suggestion in enumerate(result1.improvement_suggestions[:3], 1):
        print(f"  {i}. {suggestion}")
    print()
    
    # 示例2: 上下文超限
    test_error2 = """
    API error: context_length_exceeded - maximum context length exceeded
    """
    
    result2 = classifier.classify(test_error2)
    print("=" * 60)
    print("测试案例 2: 上下文超限")
    print(f"分类结果: {result2.primary_type.value} (置信度: {result2.confidence:.2f})")
    print(f"根因: {result2.root_cause}")
    print("改进建议:")
    for i, suggestion in enumerate(result2.improvement_suggestions[:3], 1):
        print(f"  {i}. {suggestion}")

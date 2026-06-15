#!/usr/bin/env python3
"""
Agent失败案例自动分类器
支持三种主要错误类型的自动识别与分类：
1. 幻觉型错误 (Hallucination) - 模型编造不存在的事实
2. 知识缺失型错误 (KnowledgeGap) - 模型缺乏必要的知识
3. 工具使用错误型 (ToolMisuse) - 工具调用方式或参数错误
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class ErrorType(Enum):
    HALLUCINATION = "hallucination"
    KNOWLEDGE_GAP = "knowledge_gap"
    TOOL_MISUSE = "tool_misuse"
    UNKNOWN = "unknown"


@dataclass
class ClassificationResult:
    error_type: ErrorType
    confidence: float  # 0.0 - 1.0
    evidence: List[str]
    severity: str  # low, medium, high, critical
    suggested_fix: str
    categories: List[str]


class ErrorPattern:
    """错误模式定义"""
    
    # 幻觉型错误关键词
    HALLUCINATION_KEYWORDS = [
        r"不存在.*文件",
        r"不存在.*目录",
        r"找不到.*模块",
        r"没有.*函数",
        r"没有.*方法",
        r"不存在.*属性",
        r"invalid.*syntax",
        r"syntax.*error",
        r"name.*is.*not.*defined",
        r"module.*has.*no.*attribute",
        r"no such file",
        r"file not found",
        r"directory not found",
    ]
    
    HALLUCINATION_PATTERNS = [
        # 编造API/函数名
        r"AttributeError: module '[\w.]+' has no attribute '[\w_]+'",
        # 编造文件路径
        r"FileNotFoundError: No such file or directory: '[^']+'",
        # 编造参数名称
        r"TypeError: [\w_]+\(\) got an unexpected keyword argument '[\w_]+'",
        # 编造不存在的命令
        r"command not found: [\w-]+",
        # 编造依赖包
        r"ModuleNotFoundError: No module named '[\w.]+'",
    ]
    
    # 知识缺失型错误关键词
    KNOWLEDGE_GAP_KEYWORDS = [
        r"我不了解",
        r"我不知道",
        r"我不清楚",
        r"需要了解",
        r"需要查阅",
        r"需要确认",
        r"不熟悉",
        r"未学习过",
        r"permission denied",
        r"access denied",
        r"authorization required",
        r"rate limit",
        r"quota exceeded",
        r"API key",
        r"credentials",
    ]
    
    KNOWLEDGE_GAP_PATTERNS = [
        # 权限知识缺失
        r"PermissionError: \[Errno 13\] Permission denied",
        # API知识缺失
        r"401 Unauthorized",
        r"403 Forbidden",
        # 领域知识缺失
        r"429 Too Many Requests",
        r"API rate limit exceeded",
        # 环境知识缺失
        r"ImportError: cannot import name",
        r"VersionConflict",
    ]
    
    # 工具使用错误关键词
    TOOL_MISUSE_KEYWORDS = [
        r"参数.*错误",
        r"参数.*缺失",
        r"参数.*无效",
        r"缺少.*参数",
        r"无效.*参数",
        r"格式.*错误",
        r"expected.*argument",
        r"missing.*required",
        r"invalid.*value",
        r"bad request",
        r"400 Bad Request",
    ]
    
    TOOL_MISUSE_PATTERNS = [
        # 参数缺失
        r"TypeError: [\w_]+\(\) missing \d+ required positional argument",
        # 参数类型错误
        r"TypeError: [\w_]+\(\) argument must be",
        # JSON解析错误
        r"json\.decoder\.JSONDecodeError",
        # 工具超时
        r"TimeoutError",
        # 工具返回格式错误
        r"KeyError: '[\w_]+'",
        r"IndexError: (list|tuple) index out of range",
    ]


class FailureClassifier:
    """失败案例自动分类器"""
    
    def __init__(self):
        self.patterns = ErrorPattern()
        self.confidence_weights = {
            'keyword_match': 0.3,
            'pattern_match': 0.5,
            'context_match': 0.2,
        }
    
    def classify(self, 
                 error_message: str, 
                 trace_context: Optional[Dict] = None,
                 tool_name: Optional[str] = None) -> ClassificationResult:
        """
        对错误进行分类
        
        Args:
            error_message: 错误信息文本
            trace_context: 轨迹上下文信息
            tool_name: 涉及的工具名称
            
        Returns:
            ClassificationResult 分类结果
        """
        if trace_context is None:
            trace_context = {}
        
        error_lower = error_message.lower()
        
        # 计算各类型的置信度
        hallucination_score = self._calculate_hallucination_score(
            error_message, error_lower, trace_context
        )
        knowledge_score = self._calculate_knowledge_gap_score(
            error_message, error_lower, trace_context
        )
        tool_misuse_score = self._calculate_tool_misuse_score(
            error_message, error_lower, tool_name, trace_context
        )
        
        # 收集证据
        evidence = []
        
        # 确定主要错误类型
        scores = {
            ErrorType.HALLUCINATION: hallucination_score,
            ErrorType.KNOWLEDGE_GAP: knowledge_score,
            ErrorType.TOOL_MISUSE: tool_misuse_score,
        }
        
        max_score = max(scores.values())
        if max_score < 0.1:
            error_type = ErrorType.UNKNOWN
            confidence = 0.1
            evidence.append("无法匹配到已知错误模式")
        else:
            error_type = max(scores, key=scores.get)
            confidence = max_score
            evidence = self._collect_evidence(error_type, error_message, trace_context)
        
        # 评估严重程度
        severity = self._assess_severity(error_type, error_message)
        
        # 生成修复建议
        suggested_fix = self._generate_suggestion(error_type, error_message, tool_name)
        
        # 细分类别
        categories = self._get_subcategories(error_type, error_message)
        
        return ClassificationResult(
            error_type=error_type,
            confidence=round(confidence, 2),
            evidence=evidence,
            severity=severity,
            suggested_fix=suggested_fix,
            categories=categories
        )
    
    def _calculate_hallucination_score(self, 
                                       error_msg: str, 
                                       error_lower: str,
                                       context: Dict) -> float:
        """计算幻觉型错误置信度"""
        score = 0.0
        
        # 关键词匹配
        keyword_hits = sum(
            1 for pattern in self.patterns.HALLUCINATION_KEYWORDS
            if re.search(pattern, error_lower, re.IGNORECASE)
        )
        score += min(keyword_hits * 0.15, self.confidence_weights['keyword_match'])
        
        # 正则模式匹配
        pattern_hits = sum(
            1 for pattern in self.patterns.HALLUCINATION_PATTERNS
            if re.search(pattern, error_msg)
        )
        score += min(pattern_hits * 0.25, self.confidence_weights['pattern_match'])
        
        # 上下文检查
        if context.get('tool_calls', 0) == 0 and '不存在' in error_msg:
            score += self.confidence_weights['context_match']
        
        return min(score, 1.0)
    
    def _calculate_knowledge_gap_score(self,
                                       error_msg: str,
                                       error_lower: str,
                                       context: Dict) -> float:
        """计算知识缺失型错误置信度"""
        score = 0.0
        
        # 关键词匹配
        keyword_hits = sum(
            1 for pattern in self.patterns.KNOWLEDGE_GAP_KEYWORDS
            if re.search(pattern, error_lower, re.IGNORECASE)
        )
        score += min(keyword_hits * 0.15, self.confidence_weights['keyword_match'])
        
        # 正则模式匹配
        pattern_hits = sum(
            1 for pattern in self.patterns.KNOWLEDGE_GAP_PATTERNS
            if re.search(pattern, error_msg)
        )
        score += min(pattern_hits * 0.25, self.confidence_weights['pattern_match'])
        
        # 上下文检查
        if 'API' in error_msg or '权限' in error_msg or 'quota' in error_lower:
            score += self.confidence_weights['context_match']
        
        return min(score, 1.0)
    
    def _calculate_tool_misuse_score(self,
                                     error_msg: str,
                                     error_lower: str,
                                     tool_name: Optional[str],
                                     context: Dict) -> float:
        """计算工具使用错误置信度"""
        score = 0.0
        
        # 有关联工具，基础分提升
        if tool_name:
            score += 0.1
        
        # 关键词匹配
        keyword_hits = sum(
            1 for pattern in self.patterns.TOOL_MISUSE_KEYWORDS
            if re.search(pattern, error_lower, re.IGNORECASE)
        )
        score += min(keyword_hits * 0.15, self.confidence_weights['keyword_match'])
        
        # 正则模式匹配
        pattern_hits = sum(
            1 for pattern in self.patterns.TOOL_MISUSE_PATTERNS
            if re.search(pattern, error_msg)
        )
        score += min(pattern_hits * 0.25, self.confidence_weights['pattern_match'])
        
        # 上下文检查
        if context.get('tool_calls', 0) > 0:
            score += 0.1
        if '参数' in error_msg or 'argument' in error_lower:
            score += 0.1
        
        return min(score, 1.0)
    
    def _collect_evidence(self, error_type: ErrorType, 
                         error_msg: str, context: Dict) -> List[str]:
        """收集分类证据"""
        evidence = []
        
        if error_type == ErrorType.HALLUCINATION:
            if 'No such file' in error_msg:
                evidence.append("引用了不存在的文件路径")
            if 'has no attribute' in error_msg:
                evidence.append("调用了不存在的API/方法")
            if 'ModuleNotFoundError' in error_msg:
                evidence.append("假设不存在的依赖包")
        
        elif error_type == ErrorType.KNOWLEDGE_GAP:
            if 'Permission denied' in error_msg:
                evidence.append("缺乏权限相关知识")
            if 'API key' in error_msg.lower() or 'Unauthorized' in error_msg:
                evidence.append("缺乏API认证知识")
            if 'rate limit' in error_msg.lower():
                evidence.append("缺乏API限流知识")
        
        elif error_type == ErrorType.TOOL_MISUSE:
            if 'missing' in error_msg.lower() and 'argument' in error_msg.lower():
                evidence.append("缺失必要参数")
            if 'JSONDecodeError' in error_msg:
                evidence.append("JSON解析格式错误")
            if 'KeyError' in error_msg:
                evidence.append("访问不存在的字段")
            if 'IndexError' in error_msg:
                evidence.append("数组越界访问")
        
        return evidence
    
    def _assess_severity(self, error_type: ErrorType, error_msg: str) -> str:
        """评估错误严重程度"""
        critical_markers = [
            'permission denied', '401', '403',
            'API key', 'credentials', 'quota'
        ]
        
        high_markers = [
            'ModuleNotFoundError', 'FileNotFoundError',
            'JSONDecodeError', 'TimeoutError'
        ]
        
        error_lower = error_msg.lower()
        
        if any(marker in error_lower for marker in critical_markers):
            return 'critical'
        elif any(marker in error_msg for marker in high_markers):
            return 'high'
        elif 'syntax error' in error_lower or 'invalid' in error_lower:
            return 'medium'
        else:
            return 'low'
    
    def _generate_suggestion(self, error_type: ErrorType, 
                            error_msg: str, tool_name: Optional[str]) -> str:
        """生成修复建议"""
        if error_type == ErrorType.HALLUCINATION:
            if 'file' in error_msg.lower():
                return "执行前使用read工具验证文件是否存在，或先执行ls查看目录结构"
            elif 'module' in error_msg.lower() or 'attribute' in error_msg.lower():
                return "使用web_fetch查阅官方文档确认API存在性，或使用dir()查看可用方法"
            else:
                return "在作出假设前，使用工具验证事实正确性，避免编造信息"
        
        elif error_type == ErrorType.KNOWLEDGE_GAP:
            if 'permission' in error_msg.lower():
                return "添加sudo权限检查，或使用trash替代rm避免权限问题"
            elif 'API' in error_msg or '401' in error_msg or '403' in error_msg:
                return "检查~/.openclaw/.env中的API密钥配置，验证权限是否充足"
            elif 'rate' in error_msg.lower() or 'quota' in error_msg.lower():
                return "添加重试机制和限流控制，或切换备用API提供商"
            else:
                return "触发web_search工具补充缺失知识，避免在信息不完整时继续执行"
        
        elif error_type == ErrorType.TOOL_MISUSE:
            if tool_name:
                return f"查阅{tool_name}工具的SKILL.md文档，确认参数格式和调用规范"
            elif 'JSON' in error_msg:
                return "验证JSON格式正确性，确保工具调用参数符合schema要求"
            elif 'parameter' in error_msg.lower() or 'argument' in error_msg.lower():
                return "检查所有必填参数，使用默认值或用户确认补全缺失参数"
            else:
                return "参考工具文档调整调用方式，添加参数校验逻辑"
        
        return "分析完整执行轨迹，定位根本原因后制定修复策略"
    
    def _get_subcategories(self, error_type: ErrorType, error_msg: str) -> List[str]:
        """获取错误细分类别"""
        categories = [error_type.value]
        error_lower = error_msg.lower()
        
        if error_type == ErrorType.HALLUCINATION:
            if 'file' in error_lower:
                categories.append('file_path_hallucination')
            if 'module' in error_lower or 'import' in error_lower:
                categories.append('code_api_hallucination')
            if 'command not found' in error_lower:
                categories.append('command_hallucination')
        
        elif error_type == ErrorType.KNOWLEDGE_GAP:
            if 'permission' in error_lower or '401' in error_msg or '403' in error_msg:
                categories.append('authorization_knowledge')
            if 'rate' in error_lower or 'quota' in error_lower:
                categories.append('api_limit_knowledge')
            if 'version' in error_lower:
                categories.append('version_knowledge')
        
        elif error_type == ErrorType.TOOL_MISUSE:
            if 'missing' in error_lower and 'argument' in error_lower:
                categories.append('missing_parameter')
            if 'json' in error_lower and 'decode' in error_lower:
                categories.append('format_error')
            if 'timeout' in error_lower:
                categories.append('timeout_error')
            if 'keyerror' in error_lower or 'indexerror' in error_lower:
                categories.append('data_access_error')
        
        return categories
    
    def batch_classify(self, failures: List[Dict]) -> List[Dict]:
        """批量分类失败案例"""
        results = []
        for failure in failures:
            result = self.classify(
                error_message=failure.get('error_message', ''),
                trace_context=failure.get('context', {}),
                tool_name=failure.get('tool_name')
            )
            results.append({
                'trace_uuid': failure.get('trace_uuid'),
                'error_type': result.error_type.value,
                'confidence': result.confidence,
                'severity': result.severity,
                'evidence': result.evidence,
                'suggested_fix': result.suggested_fix,
                'categories': result.categories,
                'classified_at': datetime.now().isoformat()
            })
        return results
    
    def generate_statistics(self, classifications: List[Dict]) -> Dict:
        """生成分类统计报告"""
        type_counts = {}
        severity_counts = {}
        category_counts = {}
        
        for item in classifications:
            error_type = item['error_type']
            type_counts[error_type] = type_counts.get(error_type, 0) + 1
            
            severity = item['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            for category in item['categories']:
                category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            'total_failures': len(classifications),
            'type_distribution': type_counts,
            'severity_distribution': severity_counts,
            'category_distribution': category_counts,
            'high_confidence_count': sum(1 for c in classifications if c['confidence'] >= 0.7),
        }


# 使用示例
if __name__ == '__main__':
    classifier = FailureClassifier()
    
    # 测试案例1: 幻觉型错误
    test_error1 = """
    FileNotFoundError: No such file or directory: '/tmp/nonexistent_file.txt'
    """
    result1 = classifier.classify(test_error1)
    # print("测试1 - 幻觉型错误:")
    # print(f"  类型: {result1.error_type.value}")
    # print(f"  置信度: {result1.confidence}")
    # print(f"  证据: {result1.evidence}")
    # print(f"  建议: {result1.suggested_fix}\n")
    
    # 测试案例2: 工具使用错误
    test_error2 = """
    TypeError: read() missing 1 required positional argument: 'path'
    """
    result2 = classifier.classify(test_error2, tool_name='read')
    # print("测试2 - 工具使用错误:")
    # print(f"  类型: {result2.error_type.value}")
    # print(f"  置信度: {result2.confidence}")
    # print(f"  证据: {result2.evidence}")
    # print(f"  建议: {result2.suggested_fix}\n")
    
    # 测试案例3: 知识缺失型错误
    test_error3 = """
    PermissionError: [Errno 13] Permission denied: '/root/config'
    """
    result3 = classifier.classify(test_error3)
    # print("测试3 - 知识缺失型错误:")
    # print(f"  类型: {result3.error_type.value}")
    # print(f"  置信度: {result3.confidence}")
    # print(f"  证据: {result3.evidence}")
    # print(f"  建议: {result3.suggested_fix}")

"""
失败案例自动分类器 - failure_classifier.py

功能: 分析 Agent 执行轨迹，自动判定失败类型并生成改善建议。
支持三种核心分类 + 兜底 LLM 分析。

分类体系:
- hallucination: 幻觉型（虚构事实/数据）
- knowledge_gap: 知识缺失型（明确承认不知道）
- tool_error: 工具使用错误型（API参数错误/解析失败/文件路径错误）
- logic_error: 逻辑推理错误型（推理链不完整/前提错误）
- timeout_resource: 超时或资源不足型
"""

import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from lib.db_connector import get_db_connection


# =============================================================================
# 数据模型
# =============================================================================

@dataclass
class FailureCase:
    """单个失败案例的完整分析结果"""
    trace_id: str
    session_id: str
    failure_type: str               # 主分类: hallucination/knowledge_gap/tool_error/logic_error/timeout_resource/other
    failure_subtype: str = ""        # 子分类（由具体匹配规则填充）
    severity: int = 3               # 严重程度 1-5 (5最严重)
    confidence: float = 0.0         # 置信度 0.0-1.0
    error_detail: str = ""          # 错误详情摘要
    root_cause: str = ""            # 根因分析
    improvement_suggestion: str = "" # 改善建议
    matched_patterns: list = field(default_factory=list)  # 匹配到的模式列表
    analysis_raw: str = ""          # LLM分析原文（如有）


# =============================================================================
# 规则引擎 - 关键词与模式匹配
# =============================================================================

class RuleEngine:
    """基于规则的快速分类引擎"""
    
    # ── 幻觉型关键词 ──
    HALLUCINATION_PATTERNS = [
        # 虚构引用
        (r"(?:引用|参考|基于).{0,20}(?:不存|未见|未找到|虚构|不存在的)", "fictional_reference"),
        (r"(?:论文|文献|研究).{0,10}(?:DOI|PMID|arXiv).{0,10}(?:不|未)", "fake_paper"),
        (r"(?:声称|宣称|认为).{0,30}(?:不属实|不一致|矛盾)", "factual_contradiction"),
        (r"(?:数据|数字|统计).{0,10}(?:编造|虚构|不真实|没有来源)", "fabricated_data"),
        # 自相矛盾
        (r"(?:以上|前面|之前).{0,20}(?:矛盾|冲突|不一致)", "self_contradiction"),
        (r"(?:同一|相同).{0,20}(?:不同结果|结果不同)", "inconsistent_result"),
    ]
    
    # ── 知识缺失型关键词 ──
    KNOWLEDGE_GAP_PATTERNS = [
        (r"(?:我不|我无法|不能|不知道|不清楚|不确定|不了解)", "explicit_unknown"),
        (r"(?:超出).{0,10}(?:知识|范围|能力)", "beyond_capability"),
        (r"(?:没有足够|缺乏|缺少).{0,10}(?:信息|上下文|数据)", "insufficient_info"),
        (r"(?:请提供|请给出|需要更多).{0,10}(?:信息|细节|上下文)", "need_more_info"),
        (r"(?:我不).{0,5}(?:擅长|熟悉|了解)", "not_proficient"),
        (r"(?:不在).{0,5}(?:知识库|训练数据|语料)", "not_in_training"),
    ]
    
    # ── 工具错误型关键词 ──
    TOOL_ERROR_PATTERNS = [
        (r"(?:FileNotFoundError|PermissionError|IOError|OSError)", "file_system_error"),
        (r"(?:KeyError|IndexError|TypeError|ValueError|AttributeError)", "python_error"),
        (r"(?:ConnectionError|TimeoutError|HTTPError|RequestException)", "network_error"),
        (r"(?:参数|argument|parameter).{0,10}(?:错误|无效|missing|required)", "parameter_error"),
        (r"(?:API|api).{0,10}(?:key|密钥|token|认证|认证失败|unauthorized)", "api_auth_error"),
        (r"(?:rate_limit|频率|限流|too many requests)", "rate_limit"),
        (r"(?:解析|parse|decode|encoding).{0,10}(?:失败|error|failed)", "parse_error"),
        (r"(?:路径|path|directory|dir).{0,10}(?:不存在|not found|not exist)", "path_error"),
        (r"(?:模型|model).{0,10}(?:不存在|not found|不支持)", "model_not_found"),
        (r"(?:token|tokens).{0,10}(?:超|exceed|limit|limit)", "token_limit"),
    ]
    
    # ── 逻辑错误型 ──
    LOGIC_ERROR_PATTERNS = [
        (r"(?:推理|推断).{0,10}(?:有误|错误|不成立)", "faulty_reasoning"),
        (r"(?:前提|假设).{0,10}(?:错误|不成立|不符合)", "wrong_premise"),
        (r"(?:遗漏|忽略|漏掉).{0,10}(?:关键|重要|核心)", "missed_key_info"),
        (r"(?:步骤).{0,5}(?:缺失|缺少|跳过)", "missing_step"),
        (r"(?:因果).{0,10}(?:倒置|混乱|错误)", "causality_error"),
    ]
    
    # ── 超时/资源不足 ──
    TIMEOUT_PATTERNS = [
        (r"(?:超时|timeout|timed?[ _]?out)", "timeout"),
        (r"(?:资源|resource).{0,10}(?:不足|耗尽|exhaust)", "resource_exhausted"),
        (r"(?:max.{0,5}tokens|context.{0,5}length|太长|太长)", "context_overflow"),
        (r"(?:内存|memory).{0,10}(?:不足|不够|out of)", "memory_exhausted"),
    ]
    
    # 严重程度评分
    SEVERITY_MAP = {
        "hallucination": {
            "fictional_reference": 5,
            "fake_paper": 5,
            "fabricated_data": 5,
            "self_contradiction": 4,
            "factual_contradiction": 4,
            "inconsistent_result": 3,
        },
        "knowledge_gap": {
            "explicit_unknown": 2,
            "beyond_capability": 3,
            "insufficient_info": 2,
            "need_more_info": 1,
            "not_proficient": 2,
            "not_in_training": 3,
        },
        "tool_error": {
            "file_system_error": 4,
            "python_error": 3,
            "network_error": 3,
            "parameter_error": 3,
            "api_auth_error": 5,
            "rate_limit": 2,
            "parse_error": 3,
            "path_error": 3,
            "model_not_found": 4,
            "token_limit": 3,
        },
        "logic_error": {
            "faulty_reasoning": 4,
            "wrong_premise": 4,
            "missed_key_info": 3,
            "missing_step": 3,
            "causality_error": 4,
        },
        "timeout_resource": {
            "timeout": 3,
            "resource_exhausted": 4,
            "context_overflow": 3,
            "memory_exhausted": 4,
        },
    }
    
    def __init__(self):
        self._patterns = [
            ("hallucination", self.HALLUCINATION_PATTERNS),
            ("knowledge_gap", self.KNOWLEDGE_GAP_PATTERNS),
            ("tool_error", self.TOOL_ERROR_PATTERNS),
            ("logic_error", self.LOGIC_ERROR_PATTERNS),
            ("timeout_resource", self.TIMEOUT_PATTERNS),
        ]
    
    def classify(self, trace_entry: dict) -> Optional[FailureCase]:
        """
        对单个轨迹条目进行规则分类
        Returns: 如果匹配到规则返回 FailureCase，否则返回 None
        """
        # 获取待分析的文本
        text_sources = []
        
        # 错误详情
        if trace_entry.get("error_detail"):
            text_sources.append(trace_entry["error_detail"])
        if trace_entry.get("error_type"):
            text_sources.append(trace_entry["error_type"])
        
        # 最终输出
        if trace_entry.get("final_output"):
            text_sources.append(trace_entry["final_output"][:3000])
        
        # 思维链
        if trace_entry.get("thinking_chain"):
            try:
                chain = json.loads(trace_entry["thinking_chain"]) if isinstance(trace_entry["thinking_chain"], str) else trace_entry["thinking_chain"]
                text_sources.append(" ".join([s.get("content", "") for s in chain]))
            except (json.JSONDecodeError, TypeError):
                pass
        
        # 工具调用
        if trace_entry.get("tool_calls"):
            try:
                calls = json.loads(trace_entry["tool_calls"]) if isinstance(trace_entry["tool_calls"], str) else trace_entry["tool_calls"]
                for call in calls:
                    if not call.get("success", True):
                        text_sources.append(f"tool:{call.get('tool','')} result:{call.get('result_summary','')}")
            except (json.JSONDecodeError, TypeError):
                pass
        
        combined_text = "\n".join(text_sources).lower()
        
        best_match = None
        best_score = 0
        matched_patterns = []
        
        for category, patterns in self._patterns:
            for pattern, subtype in patterns:
                matches = re.findall(pattern, combined_text, re.IGNORECASE)
                if matches:
                    score = len(matches)
                    if score > best_score:
                        best_score = score
                        best_match = (category, subtype, score)
                    matched_patterns.append({
                        "category": category,
                        "subtype": subtype,
                        "pattern": pattern,
                        "matches": len(matches)
                    })
        
        if not best_match or best_score == 0:
            return None
        
        category, subtype, score = best_match
        severity = self.SEVERITY_MAP.get(category, {}).get(subtype, 3)
        confidence = min(0.5 + score * 0.15, 0.95)
        
        improvement = self._generate_improvement_suggestion(category, subtype)
        root_cause = self._generate_root_cause(category, subtype)
        
        return FailureCase(
            trace_id=trace_entry.get("trace_id", ""),
            session_id=trace_entry.get("session_id", ""),
            failure_type=category,
            failure_subtype=subtype,
            severity=severity,
            confidence=confidence,
            matched_patterns=matched_patterns,
            improvement_suggestion=improvement,
            root_cause=root_cause,
        )
    
    def _generate_improvement_suggestion(self, category: str, subtype: str) -> str:
        """根据分类生成改善建议"""
        suggestions = {
            "hallucination": {
                "fictional_reference": "在prompt中加入"I will only cite verifiable sources"约束，并在工具调用后增加事实核查步骤",
                "fake_paper": "对引用信息增加交叉验证步骤，使用搜索工具确认论文/文献是否存在",
                "fabricated_data": "要求Agent在输出数据时必须注明来源，对无来源的数据标注'推测/非确认'",
                "self_contradiction": "在最终输出前增加一致性检查步骤，检测同一事实的前后表述是否一致",
                "factual_contradiction": "添加事实核查子代理，在输出前验证关键声明的一致性",
            },
            "knowledge_gap": {
                "explicit_unknown": "在prompt中加入'如需补充信息，请明确告知用户并说明需要什么'的指示",
                "beyond_capability": "配置Agent识别能力边界并优雅降级，提供替代方案或建议",
                "insufficient_info": "练习信息收集：在初始prompt中引导Agent先问清楚所有必要的上下文再开始执行",
            },
            "tool_error": {
                "file_system_error": "所有文件操作前先执行确认文件存在的检查（os.path.exists或等效方法）",
                "api_auth_error": "在系统prompt中预置API密钥管理流程，包括密钥轮换和权限检查",
                "parameter_error": "为高频工具建立参数模板库，使用前自动校验参数格式",
                "parse_error": "增加异常处理和重试机制，为外部数据解析添加格式验证",
            },
            "logic_error": {
                "faulty_reasoning": "在思维链中增加'分步验证'环节，每步推理完成后检查逻辑自洽性",
                "wrong_premise": "开始推理前，要求Agent明确列出所有前提假设并检查其有效性",
                "missed_key_info": "在prompt中加入checklist要求，确保关键信息不被遗漏",
            },
            "timeout_resource": {
                "timeout": "为长时间运行的任务设置断点续传机制，增加进度报告",
                "context_overflow": "实现token预算管理：超长任务自动分块处理，压缩历史上下文",
            },
        }
        return suggestions.get(category, {}).get(subtype, f"定期检查{category}类型错误，分析模式并优化prompt")


# =============================================================================
# LLM 兜底分类器
# =============================================================================

# 分类 prompt 模板
CLASSIFIER_PROMPT_TEMPLATE = """你是一个AI Agent执行轨迹分析专家。请分析以下执行轨迹，判断失败原因。

## 执行信息
- 任务描述: {task_desc}
- 错误类型: {error_type}
- 错误详情: {error_detail}

## 工具调用记录
{tool_calls_summary}

## 思维链节选
{thinking_summary}

## 最终输出（前500字）
{final_output}

## 分类任务
请从以下类别中选择最匹配的一个：
1. **hallucination** - 幻觉型：Agent虚构了不存在的论文/数据/事实
2. **knowledge_gap** - 知识缺失型：Agent缺乏完成任务所需的知识
3. **tool_error** - 工具使用错误：工具参数错误/API失败/文件系统错误
4. **logic_error** - 逻辑推理错误：推理过程有缺陷
5. **timeout_resource** - 超时或资源不足
6. **other** - 其他

请以JSON格式输出：
{{
    "failure_type": "选中的类别",
    "confidence": 置信度0-1,
    "severity": 严重程度1-5,
    "error_detail": "错误详情的简短描述",
    "root_cause": "根因分析（50-100字）",
    "improvement_suggestion": "改善建议（50-100字）",
    "analysis": "详细分析过程"
}}"""


class LLMClassifier:
    """基于 LLM 的兜底分类器（当规则引擎无法判定时使用）"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client  # 可选的 LLM 客户端
    
    def classify(self, trace_entry: dict) -> Optional[FailureCase]:
        """使用 LLM 分析轨迹"""
        if not self.llm_client:
            return None
        
        # 构建分类 prompt
        tool_calls_summary = "无"
        if trace_entry.get("tool_calls"):
            try:
                calls = json.loads(trace_entry["tool_calls"]) if isinstance(trace_entry["tool_calls"], str) else trace_entry["tool_calls"]
                tool_calls_summary = "\n".join([
                    f"  - [{c['tool']}] 耗时{c.get('duration_ms','?')}ms 成功:{c.get('success','?')} 结果:{c.get('result_summary','')[:200]}"
                    for c in calls[:5]
                ])
            except (json.JSONDecodeError, TypeError):
                pass
        
        thinking_summary = "无"
        if trace_entry.get("thinking_chain"):
            try:
                chain = json.loads(trace_entry["thinking_chain"]) if isinstance(trace_entry["thinking_chain"], str) else trace_entry["thinking_chain"]
                thinking_summary = "\n".join([
                    f"  Step {s.get('step','?')}: {s.get('content','')[:200]}"
                    for s in chain[:3]
                ])
            except (json.JSONDecodeError, TypeError):
                pass
        
        prompt = CLASSIFIER_PROMPT_TEMPLATE.format(
            task_desc=(trace_entry.get("task_desc") or "")[:500],
            error_type=trace_entry.get("error_type") or "",
            error_detail=(trace_entry.get("error_detail") or "")[:500],
            tool_calls_summary=tool_calls_summary,
            thinking_summary=thinking_summary,
            final_output=(trace_entry.get("final_output") or "")[:500],
        )
        
        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",  # 使用轻量模型
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500,
            )
            result = json.loads(response.choices[0].message.content)
            
            return FailureCase(
                trace_id=trace_entry.get("trace_id", ""),
                session_id=trace_entry.get("session_id", ""),
                failure_type=result.get("failure_type", "other"),
                severity=result.get("severity", 3),
                confidence=result.get("confidence", 0.5),
                error_detail=result.get("error_detail", ""),
                root_cause=result.get("root_cause", ""),
                improvement_suggestion=result.get("improvement_suggestion", ""),
                analysis_raw=result.get("analysis", ""),
            )
        except Exception as e:
            # print(f"[LLMClassifier] LLM分析失败: {e}")
            return None


# =============================================================================
# 主分类器
# =============================================================================

class FailureClassifier:
    """失败案例自动分类器 —— 主入口"""
    
    def __init__(self, use_llm_fallback: bool = False, llm_client=None):
        self.rule_engine = RuleEngine()
        self.llm_classifier = LLMClassifier(llm_client) if use_llm_fallback else None
        self.stats = {"rule_matched": 0, "llm_used": 0, "total": 0}
    
    def classify(self, trace_entry: dict) -> FailureCase:
        """
        对轨迹条目进行分类
        先尝试规则引擎（快速），规则引擎无法判定时使用 LLM 兜底
        """
        self.stats["total"] += 1
        
        # Step 1: 规则引擎
        result = self.rule_engine.classify(trace_entry)
        if result:
            self.stats["rule_matched"] += 1
            return result
        
        # Step 2: LLM 兜底
        if self.llm_classifier:
            self.stats["llm_used"] += 1
            result = self.llm_classifier.classify(trace_entry)
            if result:
                return result
        
        # Step 3: 无法分类
        return FailureCase(
            trace_id=trace_entry.get("trace_id", ""),
            session_id=trace_entry.get("session_id", ""),
            failure_type="other",
            severity=2,
            confidence=0.3,
            error_detail="未能自动分类，请人工审核",
            root_cause="无法自动识别根因",
            improvement_suggestion="请人工分析并补充改善建议",
        )
    
    def batch_classify(self, trace_entries: list) -> List[FailureCase]:
        """批量分类"""
        results = []
        for entry in trace_entries:
            results.append(self.classify(entry))
        return results
    
    def save_results(self, results: List[FailureCase]):
        """将分类结果写回数据库"""
        conn = get_db_connection()
        c = conn.cursor()
        
        for case in results:
            c.execute('''UPDATE trace_entries SET
                failure_type = %s,
                failure_severity = %s,
                failure_analysis = %s
                WHERE trace_id = %s''',
                (case.failure_type, case.severity,
                 json.dumps({
                     "subtype": case.failure_subtype,
                     "confidence": case.confidence,
                     "root_cause": case.root_cause,
                     "improvement_suggestion": case.improvement_suggestion,
                     "matched_patterns": case.matched_patterns,
                     "analysis_raw": case.analysis_raw,
                 }, ensure_ascii=False),
                 case.trace_id))
        
        conn.commit()
        conn.close()
    
    def get_stats(self) -> dict:
        """获取分类统计信息"""
        return {
            **self.stats,
            "rule_success_rate": round(self.stats["rule_matched"] / max(self.stats["total"], 1), 3),
        }


# =============================================================================
# 命令行入口（用于定时任务或手动触发）
# =============================================================================

def auto_classify_recent_failures(limit: int = 50):
    """
    自动分析最近的失败轨迹
    适用于 cron 定时任务调用
    
    Args:
        limit: 最多分析的失败轨迹条数
    Returns:
        dict: 分类结果统计
    """
    # print(f"[FailureClassifier] 开始分析最近 {limit} 条失败轨迹...")
    
    conn = get_db_connection()
    c = conn.cursor(pymysql.cursors.DictCursor)
    c.execute('''SELECT * FROM trace_entries 
                 WHERE status = 'failed' AND failure_type IS NULL
                 ORDER BY created_at DESC LIMIT %s''', (limit,))
    entries = c.fetchall()
    conn.close()
    
    if not entries:
        # print("[FailureClassifier] 没有未分类的失败轨迹")
        return {"total": 0, "classified": 0}
    
    classifier = FailureClassifier(use_llm_fallback=True)
    results = classifier.batch_classify(entries)
    classifier.save_results(results)
    
    # 统计
    type_stats = {}
    for r in results:
        type_stats[r.failure_type] = type_stats.get(r.failure_type, 0) + 1
    
    # print(f"[FailureClassifier] 完成: 共分析 {len(entries)} 条")
    # print(f"[FailureClassifier] 分类分布: {json.dumps(type_stats, ensure_ascii=False)}")
    # print(f"[FailureClassifier] 规则引擎匹配率: {classifier.stats['rule_matched']}/{classifier.stats['total']}")
    
    return {
        "total": len(entries),
        "classified": len(results),
        "type_distribution": type_stats,
        "stats": classifier.get_stats(),
    }


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    result = auto_classify_recent_failures(n)
    # print(json.dumps(result, ensure_ascii=False, indent=2))

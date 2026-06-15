"""
自改进Prompt生成模板库 - prompt_template_lib.py

功能: 基于失败分类结果，自动匹配和生成优化的系统提示词模板，
     嵌入到 Agent 的 system prompt 中以避免同类错误重复发生。

设计目标:
1. 每个失败类型对应一个或多个精调模板
2. 模板支持参数化填充（注入具体错误信息）
3. 支持版本管理和效果追踪
"""

import json
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from lib.db_connector import get_db_connection


# =============================================================================
# 数据模型
# =============================================================================

@dataclass
class PromptTemplate:
    """单个 Prompt 模板"""
    template_id: str                     # 唯一标识
    name: str                            # 模板名称
    version: str                         # 版本号
    target_type: str                     # 目标失败类型
    target_subtypes: list = field(default_factory=list)  # 目标子类型（空表示匹配所有）
    priority: int = 0                    # 优先级（高优先级先匹配）
    system_prompt: str = ""              # 系统 prompt 模板（用 {var} 占位）
    user_prompt_prefix: str = ""         # 用户 prompt 前缀模板
    apply_condition: str = "always"      # 应用条件: always/recent_fail/continuous_fail
    created_at: str = ""
    effect_count: int = 0                # 已应用次数
    success_rate: float = 0.0            # 应用后的成功率
    
    def render(self, **kwargs) -> Dict[str, str]:
        """渲染模板，填充变量"""
        return {
            "system_prompt": self.system_prompt.format(**kwargs),
            "user_prompt_prefix": self.user_prompt_prefix.format(**kwargs),
            "template_id": self.template_id,
            "version": self.version,
        }


@dataclass
class TemplateMatchResult:
    """模板匹配结果"""
    matched_templates: list = field(default_factory=list)
    applied_template_ids: list = field(default_factory=list)
    rendered_prompts: list = field(default_factory=list)
    match_reason: str = ""


# =============================================================================
# 模板库
# =============================================================================

class PromptTemplateLibrary:
    """自改进 prompt 模板库 —— 模板定义与管理"""
    
    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
        self._load_builtin_templates()
    
    def _load_builtin_templates(self):
        """加载内置模板"""
        builtins = self._get_builtin_templates()
        for tpl in builtins:
            self._templates[tpl.template_id] = tpl
    
    def _get_builtin_templates(self) -> list:
        """定义所有内置模板 —— 这是模板库的核心"""
        now = datetime.now().isoformat()
        
        return [
            # ═══════════════════════════════════════════════
            # 类别 1: 幻觉型 (hallucination)
            # ═══════════════════════════════════════════════
            
            PromptTemplate(
                template_id="anti-hallucination-v1",
                name="反幻觉基础约束",
                version="1.0",
                target_type="hallucination",
                priority=100,
                system_prompt=(
                    "## 反幻觉规则（自动启用 - {reason}）\n"
                    "- 🔴 **严禁虚构事实**：如果不确定某信息是否准确，请明确说"我不确定"而非编造\n"
                    "- 🔴 **引用必须可验证**：所有引用（论文/数据/来源）必须可追溯，不能自行编造\n"
                    "- 🔴 **数据来源标注**：输出的数据必须注明来源，推测性数据标注为"预估"\n"
                    "- ✅ **不确定时**：使用工具搜索验证，或明确告知用户需要更多信息\n"
                    "- ✅ **一致性检查**：最终输出前自我检查关键声明的前后一致性"
                ),
                apply_condition="recent_fail",
                created_at=now,
            ),
            
            PromptTemplate(
                template_id="citation-validator-v1",
                name="引用真实性验证",
                version="1.0",
                target_type="hallucination",
                target_subtypes=["fictional_reference", "fake_paper"],
                priority=90,
                system_prompt=(
                    "## 引用验证规则（自动启用 - 检测到虚构引用风险）\n"
                    "- 输出任何学术引用前，调用搜索工具验证来源是否存在\n"
                    "- 仅引用通过验证的来源\n"
                    "- 如果无法验证引用，在引用后添加标记: [来源待验证]\n"
                    "- 优先引用知名数据库索引的文献（PubMed/arXiv/CrossRef有DOI）"
                ),
                apply_condition="continuous_fail",
                created_at=now,
            ),
            
            PromptTemplate(
                template_id="data-fact-check-v1",
                name="数据事实核查",
                version="1.0",
                target_type="hallucination",
                target_subtypes=["fabricated_data"],
                priority=85,
                system_prompt=(
                    "## 数据真实性规则（自动启用 - 检测到数据编造风险）\n"
                    "- 所有统计数据必须注明来源（URL或文献引用）\n"
                    "- 估算值必须明确标注为"估算"或"预估"\n"
                    "- 提供的数字需要做合理性校验（是否符合常识范围）\n"
                    "- 两个或以上来源矛盾时，应说明分歧而不是选择性地使用"
                ),
                apply_condition="continuous_fail",
                created_at=now,
            ),
            
            # ═══════════════════════════════════════════════
            # 类别 2: 知识缺失型 (knowledge_gap)
            # ═══════════════════════════════════════════════
            
            PromptTemplate(
                template_id="knowledge-gap-handler-v1",
                name="知识缺口优雅处理",
                version="1.0",
                target_type="knowledge_gap",
                priority=95,
                system_prompt=(
                    "## 知识缺口处理规则（自动启用 - {reason}）\n"
                    "- 🔴 遇到不确定的信息时，使用工具搜索验证，不要直接猜测\n"
                    "- ✅ 明确区分"我知道"和"我推测"的信息\n"
                    "- ✅ 如果缺少关键上下文，明确告知用户缺少什么信息才能继续\n"
                    "- ✅ 对于超出能力范围的问题，提供替代方案或建议后续步骤\n"
                    "- 💡 处理流程: 自检 → 搜索验证 → 不确定时如实相告"
                ),
                apply_condition="recent_fail",
                created_at=now,
            ),
            
            PromptTemplate(
                template_id="info-collection-checklist-v1",
                name="信息收集检查清单",
                version="1.0",
                target_type="knowledge_gap",
                target_subtypes=["insufficient_info", "need_more_info"],
                priority=80,
                user_prompt_prefix=(
                    "【信息收集提示】在执行前，请先确认你是否拥有完成任务所需的全部信息。\n"
                    "如缺少关键信息，请列出你需要获取的内容，然后再开始执行。\n"
                    "---"
                ),
                apply_condition="recent_fail",
                created_at=now,
            ),
            
            # ═══════════════════════════════════════════════
            # 类别 3: 工具使用错误型 (tool_error)
            # ═══════════════════════════════════════════════
            
            PromptTemplate(
                template_id="tool-error-prevention-v1",
                name="工具使用安全检查",
                version="1.0",
                target_type="tool_error",
                priority=95,
                system_prompt=(
                    "## 工具使用安全规则（自动启用 - {reason}）\n"
                    "- 🔴 调用任何工具前，先验证所有参数的类型和格式\n"
                    "- 🔴 文件操作前先检查文件/路径是否存在（使用 os.path.exists 或等效方法）\n"
                    "- 🔴 API 调用必须有异常处理和重试机制\n"
                    "- ✅ 每次工具调用后检查返回值是否正常\n"
                    "- ✅ 解析外部数据时使用 try/except 包裹\n"
                    "- 💡 工具调用失败时记录完整错误信息以便后续分析"
                ),
                apply_condition="recent_fail",
                created_at=now,
            ),
            
            PromptTemplate(
                template_id="file-ops-safeguard-v1",
                name="文件操作安全防护",
                version="1.0",
                target_type="tool_error",
                target_subtypes=["file_system_error", "path_error"],
                priority=90,
                system_prompt=(
                    "## 文件操作安全规则（自动启用 - 检测到文件系统错误风险）\n"
                    "文件操作三步检查:\n"
                    "  1. 确认路径格式正确（使用 os.path 标准化）\n"
                    "  2. 检查文件/目录是否存在（os.path.exists）\n"
                    "  3. 检查权限（os.access）\n"
                    "写入文件前: 确保父目录已创建（os.makedirs exist_ok=True）\n"
                    "读取文件前: 使用 try/except 包裹，FileNotFoundError 时给出明确的错误信息"
                ),
                apply_condition="continuous_fail",
                created_at=now,
            ),
            
            PromptTemplate(
                template_id="api-call-safeguard-v1",
                name="API调用安全防护",
                version="1.0",
                target_type="tool_error",
                target_subtypes=["api_auth_error", "network_error", "rate_limit"],
                priority=85,
                system_prompt=(
                    "## API调用安全规则（自动启用 - 检测到API错误风险）\n"
                    "- 每次 API 调用使用 3 次重试机制（指数退避）\n"
                    "- 所有请求添加超时设置（默认 30s）\n"
                    "- 处理 HTTP 429（Rate Limit）时等待 Retry-After 头指定的时间\n"
                    "- 密钥认证失败时不要反复重试，检查密钥是否有效\n"
                    "- 记录 API 调用的响应状态和耗时"
                ),
                apply_condition="continuous_fail",
                created_at=now,
            ),
            
            # ═══════════════════════════════════════════════
            # 类别 4: 逻辑错误型 (logic_error)
            # ═══════════════════════════════════════════════
            
            PromptTemplate(
                template_id="logic-verification-v1",
                name="逻辑推理验证",
                version="1.0",
                target_type="logic_error",
                priority=90,
                system_prompt=(
                    "## 逻辑推理验证规则（自动启用 - {reason}）\n"
                    "- 🧩 分步推理时，每一步检查是否从前提正确推导\n"
                    "- 🧩 执行前列出所有假设前提，并思考每个假设的有效性\n"
                    "- 🧩 遇到多步骤任务时，使用checklist确保所有步骤都完成\n"
                    "- 🧩 最终输出前，反向验证：从结论回溯，检查路径是否完整\n"
                    "- 🔄 如果发现推理矛盾，回溯到矛盾点重新推理"
                ),
                apply_condition="recent_fail",
                created_at=now,
            ),
            
            # ═══════════════════════════════════════════════
            # 类别 5: 超时/资源不足 (timeout_resource)
            # ═══════════════════════════════════════════════
            
            PromptTemplate(
                template_id="resource-management-v1",
                name="资源管理策略",
                version="1.0",
                target_type="timeout_resource",
                priority=85,
                system_prompt=(
                    "## 资源管理规则（自动启用 - {reason}）\n"
                    "- ⏱ 长任务自动分块处理，每块完成后输出中间结果\n"
                    "- ⏱ 监控 token 消耗，接近限制时自动精简输出\n"
                    "- ⏱ 对于大数据集，使用流式/分页方式处理\n"
                    "- 💾 大文件操作时使用缓冲区，避免一次性加载到内存\n"
                    "- 🚦 设置任务超时阈值，接近超时时输出当前进度并申请继续"
                ),
                apply_condition="recent_fail",
                created_at=now,
            ),
        ]
    
    def get_all_templates(self) -> List[PromptTemplate]:
        """获取所有模板"""
        return list(self._templates.values())
    
    def get_by_id(self, template_id: str) -> Optional[PromptTemplate]:
        """根据ID获取模板"""
        return self._templates.get(template_id)
    
    def get_by_type(self, failure_type: str) -> List[PromptTemplate]:
        """根据失败类型获取模板"""
        return [t for t in self._templates.values() 
                if t.target_type == failure_type and t.version.startswith("1.")]
    
    def add_template(self, template: PromptTemplate):
        """添加自定义模板"""
        template.template_id = template.template_id or f"custom-{hashlib.md5(template.system_prompt.encode()).hexdigest()[:8]}"
        self._templates[template.template_id] = template


# =============================================================================
# 模板匹配引擎
# =============================================================================

class TemplateMatcher:
    """模板匹配引擎 —— 根据失败案例匹配合适的优化模板"""
    
    def __init__(self):
        self.library = PromptTemplateLibrary()
    
    def match(self, failure_case: Dict[str, Any]) -> TemplateMatchResult:
        """
        根据失败案例匹配合适的模板
        Args:
            failure_case: 包含 failure_type, failure_subtype, severity, analysis 等字段
        Returns:
            TemplateMatchResult: 匹配结果（含渲染后的prompt）
        """
        result = TemplateMatchResult()
        failure_type = failure_case.get("failure_type", "")
        failure_subtype = failure_case.get("failure_subtype", "")
        severity = failure_case.get("severity", 3)
        reason = failure_case.get("error_detail", "同类错误重复发生")
        
        # 获取所有候选模板
        candidates = self.library.get_by_type(failure_type)
        
        # 按优先级排序
        candidates.sort(key=lambda t: t.priority, reverse=True)
        
        matched = []
        for tpl in candidates:
            # 检查子类型匹配
            if tpl.target_subtypes and failure_subtype not in tpl.target_subtypes:
                continue
            
            matched.append(tpl)
            result.matched_templates.append(tpl)
            
            # 渲染模板
            rendered = tpl.render(
                reason=reason[:200],
                severity=str(severity),
                failure_type=failure_type,
                failure_subtype=failure_subtype,
                timestamp=datetime.now().isoformat(),
            )
            result.rendered_prompts.append(rendered)
            result.applied_template_ids.append(tpl.template_id)
            
            # 只应用前 3 个最高优先级的模板
            if len(result.rendered_prompts) >= 3:
                break
        
        if matched:
            result.match_reason = f"匹配 {len(matched)} 个 {failure_type} 类型模板"
        else:
            result.match_reason = f"未找到 {failure_type}/{failure_subtype} 的匹配模板"
        
        return result
    
    def build_optimized_system_prompt(self, base_prompt: str, 
                                       failure_case: Dict[str, Any]) -> str:
        """
        构建优化后的完整系统 prompt
        Args:
            base_prompt: 基础系统 prompt
            failure_case: 失败案例信息
        Returns:
            优化后的系统 prompt
        """
        match_result = self.match(failure_case)
        
        if not match_result.rendered_prompts:
            return base_prompt
        
        # 收集所有优化片段
        optimization_snippets = []
        for rp in match_result.rendered_prompts:
            if rp.get("system_prompt"):
                optimization_snippets.append(rp["system_prompt"])
        
        # 组合：基础 prompt + 优化片段
        if optimization_snippets:
            separator = "\n\n---\n## 🔧 自优化补充指令（自动注入）\n"
            extra = "\n\n".join(optimization_snippets)
            return base_prompt + separator + extra + "\n"
        
        return base_prompt
    
    def batch_build(self, base_prompt: str, 
                    failure_cases: List[Dict[str, Any]]) -> str:
        """
        基于多个失败案例批量构建优化 prompt
        相同类型的去重，严重度加权
        """
        seen_types = set()
        all_snippets = []
        
        for case in failure_cases:
            ftype = case.get("failure_type", "")
            if ftype in seen_types:
                continue
            seen_types.add(ftype)
            
            optimized = self.build_optimized_system_prompt(base_prompt, case)
            # 只提取新增的优化部分
            if "## 🔧 自优化补充指令" in optimized:
                extra = optimized.split("## 🔧 自优化补充指令", 1)[1]
                all_snippets.append(extra)
        
        if all_snippets:
            summary = f"\n\n---\n## 🔧 自优化补充指令（基于历史 {len(failure_cases)} 次失败自动生成）\n"
            return base_prompt + summary + "\n".join(all_snippets)
        
        return base_prompt
    
    def save_application_record(self, template_id: str, trace_id: str, 
                                  failure_type: str, success: bool = True):
        """记录模板应用效果"""
        try:
            conn = get_db_connection()
            c = conn.cursor()
            
            # 更新模板使用统计
            c.execute('''UPDATE trace_entries SET
                improvement_applied = TRUE,
                improvement_prompt_id = %s
                WHERE trace_id = %s''', (template_id, trace_id))
            
            # 记录到模板使用日志（可选扩展）
            conn.commit()
            conn.close()
            
            # 更新模板对象的统计
            tpl = self.library.get_by_id(template_id)
            if tpl:
                tpl.effect_count += 1
                if success:
                    tpl.success_rate = (tpl.success_rate * (tpl.effect_count - 1) + 1) / tpl.effect_count
        except Exception as e:
            # print(f"[TemplateMatcher] 记录应用失败: {e}")


# =============================================================================
# 自改进自动流程
# =============================================================================

class AutoImprovementPipeline:
    """
    自改进自动流水线
    
    工作流:
    1. 从数据库获取最近未分类的失败轨迹
    2. 使用 FailureClassifier 自动分类
    3. 使用 TemplateMatcher 匹配合适模板
    4. 生成优化后的 prompt
    5. 记录模板应用
    """
    
    def __init__(self, failure_classifier=None, template_matcher=None):
        from failure_classifier import FailureClassifier
        self.classifier = failure_classifier or FailureClassifier(use_llm_fallback=False)
        self.matcher = template_matcher or TemplateMatcher()
    
    def run(self, limit: int = 20, auto_save: bool = True) -> Dict[str, Any]:
        """
        执行一次完整的自改进循环
        Args:
            limit: 最多分析的失败轨迹数
            auto_save: 是否自动保存结果到数据库
        Returns:
            执行报告
        """
        # print(f"[AutoImprovement] 开始自改进循环...")
        
        # Step 1: 获取最近失败轨迹
        conn = get_db_connection()
        c = conn.cursor(pymysql.cursors.DictCursor)
        c.execute('''SELECT * FROM trace_entries 
                     WHERE status = 'failed' AND failure_type IS NULL
                     ORDER BY created_at DESC LIMIT %s''', (limit,))
        entries = c.fetchall()
        conn.close()
        
        if not entries:
            # print("[AutoImprovement] 没有待分析的失败轨迹")
            return {"status": "no_data", "message": "没有需要分析的失败案例"}
        
        # print(f"[AutoImprovement] 获取到 {len(entries)} 条失败轨迹")
        
        # Step 2: 分类
        results = self.classifier.batch_classify(entries)
        
        if auto_save:
            self.classifier.save_results(results)
        
        # Step 3: 统计失败模式
        type_distribution = {}
        for r in results:
            type_distribution[r.failure_type] = type_distribution.get(r.failure_type, 0) + 1
        
        # print(f"[AutoImprovement] 分类分布: {type_distribution}")
        
        # Step 4: 为每种失败类型匹配合适模板
        improvements = []
        for entry, case in zip(entries, results):
            failure_case = {
                "failure_type": case.failure_type,
                "failure_subtype": case.failure_subtype,
                "severity": case.severity,
                "error_detail": case.error_detail or entry.get("error_detail", ""),
            }
            
            match_result = self.matcher.match(failure_case)
            improvements.append({
                "trace_id": entry["trace_id"],
                "failure_type": case.failure_type,
                "matched_templates": [t.template_id for t in match_result.matched_templates],
                "rendered_prompts": match_result.rendered_prompts,
            })
        
        # Step 5: 生成汇总报告
        report = {
            "status": "completed",
            "analyzed_count": len(entries),
            "type_distribution": type_distribution,
            "classifier_stats": self.classifier.get_stats(),
            "improvements": improvements[:5],  # 只保留前5个详细
            "total_improvements": len(improvements),
            "generated_at": datetime.now().isoformat(),
        }
        
        # print(f"[AutoImprovement] 自改进循环完成")
        return report


# =============================================================================
# 命令行入口
# =============================================================================

def run_improvement_pipeline():
    """运行完整的自改进流水线（适合 cron 定时调用）"""
    pipeline = AutoImprovementPipeline()
    report = pipeline.run(limit=50, auto_save=True)
    
    summary = f"""
╔═══════════════════════════════════════════╗
║       自改进流水线执行报告                ║
╚═══════════════════════════════════════════╝

📊 分析轨迹: {report.get('analyzed_count', 0)} 条
📈 分类分布: {json.dumps(report.get('type_distribution', {}), ensure_ascii=False)}

🔧 已应用模板:
"""
    for imp in report.get("improvements", [])[:3]:
        summary += f"  - [{imp['failure_type']}] trace={imp['trace_id'][:8]}... 模板={imp['matched_templates']}\n"
    
    # print(summary)
    return report


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "pipeline":
        report = run_improvement_pipeline()
        # print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        # 列出所有模板
        lib = PromptTemplateLibrary()
        for tpl in lib.get_all_templates():
            # print(f"[{tpl.target_type}] {tpl.name} (v{tpl.version}) - 优先级:{tpl.priority}")

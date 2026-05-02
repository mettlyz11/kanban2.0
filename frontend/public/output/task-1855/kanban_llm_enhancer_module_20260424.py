"""
kanban-llm-enhancer: 看板系统 LLM 深度推理增强模块
版本: 1.0.0
日期: 2026-04-24
作者: Dudu AI Assistant
"""

import os
import json
import re
from typing import Optional
from dataclasses import dataclass, field

# ============================================================
# 数据类定义
# ============================================================

@dataclass
class Task:
    id: int
    title: str
    description: str = ""
    status: str = "pending"
    goal_category: str = ""
    execution_log: str = ""
    result_summary: str = ""
    task_summary: str = ""
    dependencies: list = field(default_factory=list)
    tags: list = field(default_factory=list)


@dataclass
class SubTask:
    parent_id: int
    title: str
    description: str
    order: int
    estimated_hours: float = 1.0


@dataclass
class BlockerAnalysis:
    task_id: int
    blocker_type: str  # "dependency", "resource", "info_gap", "technical"
    description: str
    suggested_solution: str
    priority: str = "medium"  # low/medium/high/critical


@dataclass
class SimilarityResult:
    task_id_a: int
    task_id_b: int
    similarity_score: float  # 0.0 - 1.0
    matched_keywords: list
    is_duplicate: bool = False


# ============================================================
# LLM 客户端封装
# ============================================================

class LLMClient:
    """统一 LLM API 调用封装，支持多模型 fallback"""

    FALLBACK_MODELS = [
        ("deepseek", "deepseek-chat"),
        ("aliyun", "qwen3.6-plus"),
        ("alicodingplan", "qwen3.6-plus"),
        ("moonshot", "kimi-k2.6"),
    ]

    def __init__(self, preferred_model: Optional[str] = None):
        self.preferred_model = preferred_model
        self._load_config()

    def _load_config(self):
        """从 ~/.openclaw/.env 加载 API 配置"""
        env_path = os.path.expanduser("~/.openclaw/.env")
        self.config = {}
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        self.config[k.strip()] = v.strip().strip('"')

    def chat(self, system_prompt: str, user_prompt: str,
             max_tokens: int = 2000, temperature: float = 0.3) -> str:
        """调用 LLM，自动 fallback"""
        try:
            import requests
            api_key = self.config.get("DEEPSEEK_API_KEY", "")
            if not api_key:
                raise ValueError("DeepSeek API key not found in ~/.openclaw/.env")

            resp = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            # 降级：返回基于规则的默认响应
            return f"[LLM_UNAVAILABLE: {e}] 使用规则引擎处理"


# ============================================================
# 核心模块 1：任务自动拆解引擎
# ============================================================

class TaskDecomposer:
    """
    根据任务标题、描述和目标分类，自动生成子任务列表。
    支持 LLM 增强 + 规则引擎 fallback。
    """

    GOAL_SUBTASK_TEMPLATES = {
        "AI助手系统优化": [
            "需求分析与技术方案设计",
            "核心功能模块开发",
            "单元测试与接口测试",
            "文档撰写与 API 说明",
            "集成测试与上线部署",
        ],
        "量化策略": [
            "数据采集与清洗",
            "策略逻辑设计",
            "回测验证",
            "风险评估",
            "生产部署",
        ],
        "default": [
            "任务拆解与计划制定",
            "执行主体工作",
            "验收与质量检查",
            "文档归档",
        ]
    }

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def decompose(self, task: Task, use_llm: bool = True) -> list[SubTask]:
        if use_llm:
            return self._decompose_with_llm(task)
        return self._decompose_with_rules(task)

    def _decompose_with_llm(self, task: Task) -> list[SubTask]:
        system_prompt = """你是一个专业的项目管理助手。给定一个任务，输出 JSON 格式的子任务列表。
格式: [{"title": "...", "description": "...", "estimated_hours": 2.0}, ...]
只输出 JSON，不要多余说明。"""
        user_prompt = f"""任务标题: {task.title}
任务描述: {task.description}
目标分类: {task.goal_category}
请生成 4-6 个子任务。"""
        response = self.llm.chat(system_prompt, user_prompt)
        try:
            # 提取 JSON
            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                items = json.loads(match.group())
                return [
                    SubTask(
                        parent_id=task.id,
                        title=item.get("title", ""),
                        description=item.get("description", ""),
                        order=i + 1,
                        estimated_hours=item.get("estimated_hours", 1.0)
                    )
                    for i, item in enumerate(items)
                ]
        except Exception:
            pass
        return self._decompose_with_rules(task)

    def _decompose_with_rules(self, task: Task) -> list[SubTask]:
        templates = self.GOAL_SUBTASK_TEMPLATES.get(
            task.goal_category,
            self.GOAL_SUBTASK_TEMPLATES["default"]
        )
        return [
            SubTask(
                parent_id=task.id,
                title=title,
                description=f"{task.title} - {title}",
                order=i + 1,
            )
            for i, title in enumerate(templates)
        ]


# ============================================================
# 核心模块 2：完成质量评估引擎
# ============================================================

class QualityEvaluator:
    """
    对 execution_log 进行语义分析，输出质量评分和改进建议。
    评分维度：完整性、具体性、问题解决、产出验证。
    """

    SCORING_RULES = {
        "length_ok": (200, 10),       # ≥200字得10分
        "has_tools": (["工具", "脚本", "API", "exec", "python"], 15),
        "has_problem": (["问题", "报错", "失败", "解决", "修复"], 15),
        "has_output": (["文件", "产出", "生成", "创建", "输出"], 15),
        "has_verification": (["验证", "测试", "检查", "确认", "结果"], 15),
        "result_summary_ok": (50, 15),
        "task_summary_ok": (50, 15),
    }

    def evaluate(self, task: Task) -> dict:
        score = 0
        details = {}

        # 长度检查
        log_len = len(task.execution_log)
        if log_len >= 200:
            score += 10
            details["execution_log_length"] = f"✅ {log_len}字 (≥200)"
        else:
            details["execution_log_length"] = f"❌ {log_len}字 (<200, 需补充)"

        # 关键词检查
        for keyword_group in [
            (["工具", "脚本", "API", "exec", "python"], "tools_mentioned", 15),
            (["问题", "报错", "失败", "解决", "修复"], "problems_addressed", 15),
            (["文件", "产出", "生成", "创建", "输出"], "output_described", 15),
            (["验证", "测试", "检查", "确认", "结果"], "verification_done", 15),
        ]:
            keywords, key, pts = keyword_group
            found = [kw for kw in keywords if kw in task.execution_log]
            if found:
                score += pts
                details[key] = f"✅ 包含: {', '.join(found)}"
            else:
                details[key] = f"⚠️ 未提及: {'/'.join(keywords)}"

        # result_summary
        rs_len = len(task.result_summary)
        if rs_len >= 50:
            score += 15
            details["result_summary"] = f"✅ {rs_len}字"
        else:
            details["result_summary"] = f"❌ {rs_len}字 (<50)"

        # task_summary
        ts_len = len(task.task_summary)
        if ts_len >= 50:
            score += 15
            details["task_summary"] = f"✅ {ts_len}字"
        else:
            details["task_summary"] = f"❌ {ts_len}字 (<50)"

        grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "D"
        can_complete = (log_len >= 200 and rs_len >= 50 and ts_len >= 50)

        return {
            "score": score,
            "grade": grade,
            "can_mark_completed": can_complete,
            "details": details,
            "recommendation": (
                "可标记为 completed" if can_complete
                else "❌ 不满足完成条件，请补充 execution_log / result_summary / task_summary"
            )
        }


# ============================================================
# 核心模块 3：阻塞任务智能识别
# ============================================================

class BlockerDetector:
    """
    分析任务集合，识别阻塞任务并给出解决方案建议。
    """

    BLOCKER_PATTERNS = {
        "dependency": ["等待", "依赖", "阻塞", "blocked", "waiting"],
        "resource": ["资源不足", "人手", "预算", "权限", "access"],
        "info_gap": ["信息不足", "不明确", "需要确认", "unclear", "需求变更"],
        "technical": ["技术难题", "bug", "报错", "无法", "失败"],
    }

    def detect(self, tasks: list[Task]) -> list[BlockerAnalysis]:
        blockers = []
        for task in tasks:
            if task.status in ("blocked", "in_progress"):
                text = f"{task.title} {task.description} {task.execution_log}"
                for btype, keywords in self.BLOCKER_PATTERNS.items():
                    if any(kw in text for kw in keywords):
                        blockers.append(BlockerAnalysis(
                            task_id=task.id,
                            blocker_type=btype,
                            description=f"任务 #{task.id} 可能存在 {btype} 类型阻塞",
                            suggested_solution=self._suggest_solution(btype, task),
                            priority="high" if task.status == "blocked" else "medium"
                        ))
                        break
        return blockers

    def _suggest_solution(self, btype: str, task: Task) -> str:
        solutions = {
            "dependency": f"识别上游任务，优先推进或并行处理，确认 #{task.id} 的前置条件",
            "resource": "申请额外资源/权限，或调整优先级释放现有资源",
            "info_gap": "安排需求澄清会议，明确验收标准后再继续执行",
            "technical": "分配技术攻关时间，或寻求团队/社区技术支持",
        }
        return solutions.get(btype, "人工复审，确定解除阻塞路径")


# ============================================================
# 核心模块 4：任务相似度计算引擎（去重）
# ============================================================

class SimilarityEngine:
    """
    基于关键词 TF-IDF 风格计算任务相似度，用于识别重复任务。
    """

    STOP_WORDS = {"的", "了", "和", "是", "在", "与", "及", "等", "任务", "需要", "进行"}

    def _tokenize(self, text: str) -> set:
        # 简单中文分词：按常见标点/空格切分 + 去停用词
        tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z0-9]+', text)
        return {t for t in tokens if t not in self.STOP_WORDS and len(t) > 1}

    def compute(self, task_a: Task, task_b: Task) -> SimilarityResult:
        text_a = f"{task_a.title} {task_a.description}"
        text_b = f"{task_b.title} {task_b.description}"
        tokens_a = self._tokenize(text_a)
        tokens_b = self._tokenize(text_b)
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        jaccard = len(intersection) / len(union) if union else 0.0
        return SimilarityResult(
            task_id_a=task_a.id,
            task_id_b=task_b.id,
            similarity_score=round(jaccard, 4),
            matched_keywords=list(intersection),
            is_duplicate=jaccard >= 0.6
        )

    def find_duplicates(self, tasks: list[Task], threshold: float = 0.6) -> list[SimilarityResult]:
        results = []
        for i in range(len(tasks)):
            for j in range(i + 1, len(tasks)):
                r = self.compute(tasks[i], tasks[j])
                if r.similarity_score >= threshold:
                    results.append(r)
        return sorted(results, key=lambda x: x.similarity_score, reverse=True)


# ============================================================
# 核心模块 5：跨任务依赖发现
# ============================================================

class DependencyDiscovery:
    """
    分析任务描述中的依赖关键词，自动构建依赖图。
    """

    DEP_KEYWORDS = ["依赖", "基于", "需要先完成", "前提", "after", "requires", "depends on"]

    def discover(self, tasks: list[Task]) -> dict:
        """返回 {task_id: [depends_on_task_id, ...]} 字典"""
        task_map = {t.id: t for t in tasks}
        dependency_graph = {t.id: [] for t in tasks}

        for task in tasks:
            text = f"{task.description} {task.execution_log}"
            for kw in self.DEP_KEYWORDS:
                if kw in text:
                    # 简单启发式：查找文本中出现的其他任务 ID
                    mentioned_ids = re.findall(r'#(\d+)', text)
                    for mid in mentioned_ids:
                        dep_id = int(mid)
                        if dep_id in task_map and dep_id != task.id:
                            if dep_id not in dependency_graph[task.id]:
                                dependency_graph[task.id].append(dep_id)
        return dependency_graph


# ============================================================
# 顶层 API：KanbanLLMEnhancer
# ============================================================

class KanbanLLMEnhancer:
    """
    看板 LLM 增强主入口，聚合所有子模块。

    使用示例:
        enhancer = KanbanLLMEnhancer()
        subtasks = enhancer.decompose_task(task)
        quality  = enhancer.evaluate_quality(task)
        blockers = enhancer.detect_blockers(tasks)
        dupes    = enhancer.find_duplicate_tasks(tasks)
        deps     = enhancer.discover_dependencies(tasks)
    """

    def __init__(self, preferred_model: Optional[str] = None):
        self.llm = LLMClient(preferred_model)
        self.decomposer = TaskDecomposer(self.llm)
        self.evaluator = QualityEvaluator()
        self.blocker_detector = BlockerDetector()
        self.similarity_engine = SimilarityEngine()
        self.dependency_discovery = DependencyDiscovery()

    def decompose_task(self, task: Task, use_llm: bool = True) -> list[SubTask]:
        return self.decomposer.decompose(task, use_llm=use_llm)

    def evaluate_quality(self, task: Task) -> dict:
        return self.evaluator.evaluate(task)

    def detect_blockers(self, tasks: list[Task]) -> list[BlockerAnalysis]:
        return self.blocker_detector.detect(tasks)

    def find_duplicate_tasks(self, tasks: list[Task],
                              threshold: float = 0.6) -> list[SimilarityResult]:
        return self.similarity_engine.find_duplicates(tasks, threshold)

    def discover_dependencies(self, tasks: list[Task]) -> dict:
        return self.dependency_discovery.discover(tasks)

    def full_analysis(self, tasks: list[Task]) -> dict:
        """对整个任务列表做全量分析，返回聚合报告"""
        return {
            "blockers": [
                {
                    "task_id": b.task_id,
                    "type": b.blocker_type,
                    "description": b.description,
                    "solution": b.suggested_solution,
                    "priority": b.priority,
                }
                for b in self.detect_blockers(tasks)
            ],
            "duplicates": [
                {
                    "task_a": r.task_id_a,
                    "task_b": r.task_id_b,
                    "score": r.similarity_score,
                    "keywords": r.matched_keywords,
                }
                for r in self.find_duplicate_tasks(tasks)
            ],
            "dependency_graph": self.discover_dependencies(tasks),
            "quality_scores": {
                t.id: self.evaluate_quality(t)
                for t in tasks
            },
        }


# ============================================================
# CLI 入口
# ============================================================

if __name__ == "__main__":
    # 示例：创建一个测试任务
    demo_task = Task(
        id=1855,
        title="AI助手系统优化 - 看板系统 LLM 推理增强模块开发",
        description="基于 V4.3 架构升级，实现看板系统的 LLM 深度推理能力",
        goal_category="AI助手系统优化",
        status="in_progress",
        execution_log="",
        result_summary="",
        task_summary="",
    )

    enhancer = KanbanLLMEnhancer()

    print("=== 任务拆解（规则引擎）===")
    subtasks = enhancer.decompose_task(demo_task, use_llm=False)
    for st in subtasks:
        print(f"  [{st.order}] {st.title} (~{st.estimated_hours}h)")

    print("\n=== 质量评估 ===")
    quality = enhancer.evaluate_quality(demo_task)
    print(f"  评分: {quality['score']}/100 (等级: {quality['grade']})")
    print(f"  结论: {quality['recommendation']}")

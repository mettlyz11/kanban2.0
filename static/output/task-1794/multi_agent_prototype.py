#!/usr/bin/env python3
"""
多智能体协作框架 v5.0 原型实现
====================================
任务: #1794 - 多智能体协作框架升级与性能验证

本原型实现了:
1. 编排式+分层式混合架构
2. 5类智能体角色 (Planner/Researcher/Coder/Reviewer/Executor)
3. 任务分解与依赖管理
4. 状态同步与共享记忆
5. 三级质量保证体系
6. 3个标准测试用例

版本: v5.0-prototype
日期: 2026-04-24
"""

import json
import time
import uuid
import random
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict


# -----------------------------------------------------------------------------
# 基础数据结构
# -----------------------------------------------------------------------------

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class AgentType(Enum):
    """Agent类型枚举"""
    PLANNER = "planner"
    RESEARCHER = "researcher"
    CODER = "coder"
    REVIEWER = "reviewer"
    EXECUTOR = "executor"


@dataclass
class Message:
    """Agent间消息"""
    message_id: str
    from_agent: str
    to_agent: str
    message_type: str  # task_assign, status_update, result_submit, feedback
    timestamp: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


@dataclass
class SubTask:
    """子任务"""
    task_id: str
    parent_task_id: str
    title: str
    description: str
    agent_type: AgentType
    status: TaskStatus
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    execution_log: str = ""
    quality_score: float = 0.0


@dataclass
class QualityCheckResult:
    """质量检查结果"""
    passed: bool
    score: float
    feedback: str
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


# -----------------------------------------------------------------------------
# 全局状态管理器
# -----------------------------------------------------------------------------

class StateManager:
    """全局状态管理器 - 负责状态同步和持久化"""
    
    def __init__(self):
        self.tasks: Dict[str, SubTask] = {}
        self.agent_states: Dict[str, Dict[str, Any]] = {}
        self.shared_memory: Dict[str, Any] = {
            "knowledge": {},
            "history": [],
            "best_practices": []
        }
        self.message_log: List[Message] = []
    
    def register_task(self, task: SubTask):
        """注册任务"""
        self.tasks[task.task_id] = task
    
    def update_task_status(self, task_id: str, status: TaskStatus, result: Dict = None):
        """更新任务状态"""
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            if result:
                self.tasks[task_id].result = result
            if status == TaskStatus.COMPLETED:
                self.tasks[task_id].completed_at = datetime.now().isoformat()
    
    def get_ready_tasks(self) -> List[SubTask]:
        """获取所有依赖已满足、可以开始的任务"""
        ready = []
        for task in self.tasks.values():
            if task.status == TaskStatus.PENDING:
                deps_satisfied = all(
                    self.tasks.get(dep_id, SubTask("", "", "", "", TaskStatus.COMPLETED)).status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                )
                if deps_satisfied:
                    ready.append(task)
        return ready
    
    def update_agent_state(self, agent_id: str, state: Dict[str, Any]):
        """更新Agent状态"""
        self.agent_states[agent_id] = {
            **state,
            "last_updated": datetime.now().isoformat()
        }
    
    def write_shared_memory(self, key: str, value: Any, namespace: str = "knowledge"):
        """写入共享记忆"""
        if namespace in self.shared_memory:
            self.shared_memory[namespace][key] = value
    
    def read_shared_memory(self, key: str, namespace: str = "knowledge") -> Optional[Any]:
        """读取共享记忆"""
        if namespace in self.shared_memory:
            return self.shared_memory[namespace].get(key)
        return None
    
    def log_message(self, message: Message):
        """记录消息"""
        self.message_log.append(message)
    
    def get_progress(self) -> Dict[str, Any]:
        """获取整体进度"""
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        in_progress = sum(1 for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS)
        
        return {
            "total_tasks": total,
            "completed_tasks": completed,
            "in_progress_tasks": in_progress,
            "progress_percent": (completed / total * 100) if total > 0 else 0,
            "agent_count": len(self.agent_states),
            "messages_exchanged": len(self.message_log)
        }
    
    def save_state(self, filepath: str):
        """保存状态到文件"""
        state = {
            "tasks": {k: asdict(v) for k, v in self.tasks.items()},
            "agent_states": self.agent_states,
            "shared_memory": self.shared_memory,
            "message_count": len(self.message_log)
        }
        with open(filepath, "w") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)


# -----------------------------------------------------------------------------
# Agent 基类
# -----------------------------------------------------------------------------

class BaseAgent:
    """Agent 基类"""
    
    def __init__(self, agent_id: str, name: str, agent_type: AgentType):
        self.agent_id = agent_id
        self.name = name
        self.agent_type = agent_type
        self.message_queue: List[Message] = []
        self.state_manager: Optional[StateManager] = None
    
    def set_state_manager(self, sm: StateManager):
        """设置状态管理器"""
        self.state_manager = sm
    
    def receive_message(self, msg: Message):
        """接收消息"""
        self.message_queue.append(msg)
        # print(f"  📥 [{self.name}] 收到消息: {msg.message_type}")
    
    def process_messages(self) -> List[Message]:
        """处理消息队列"""
        responses = []
        for msg in self.message_queue:
            response = self._handle_message(msg)
            if response:
                responses.append(response)
        self.message_queue.clear()
        return responses
    
    def _handle_message(self, msg: Message) -> Optional[Message]:
        """处理单条消息 - 由子类实现"""
        raise NotImplementedError
    
    def _create_message(self, to_agent: str, msg_type: str, payload: Dict) -> Message:
        """创建消息"""
        return Message(
            message_id=f"msg-{uuid.uuid4().hex[:8]}",
            from_agent=self.agent_id,
            to_agent=to_agent,
            message_type=msg_type,
            timestamp=datetime.now().isoformat(),
            payload=payload
        )
    
    def _quality_check(self, result: Dict[str, Any], check_type: str = "general") -> QualityCheckResult:
        """一级质量检查 - Agent自检"""
        issues = []
        score = 100.0
        
        # 基础完整性检查
        if not result:
            return QualityCheckResult(False, 0.0, "结果为空", ["输出为空"])
        
        # 内容长度检查
        content_length = len(str(result))
        if content_length < 100:
            issues.append("输出内容过短 (< 100字符)")
            score -= 30
        
        # 结构完整性检查
        required_fields = ["summary", "details", "confidence"]
        missing_fields = [f for f in required_fields if f not in result]
        if missing_fields:
            issues.append(f"缺少必填字段: {', '.join(missing_fields)}")
            score -= len(missing_fields) * 15
        
        passed = score >= 70
        feedback = f"质量评分: {score:.1f}/100 {'✅ 通过' if passed else '❌ 未通过'}"
        
        suggestions = []
        if score < 80:
            suggestions.append("建议增加更多细节和数据支撑")
        if score < 60:
            suggestions.append("建议重新审视输出结构，确保包含所有必要信息")
        
        return QualityCheckResult(passed, score, feedback, issues, suggestions)


# -----------------------------------------------------------------------------
# 规划代理 (Planner Agent)
# -----------------------------------------------------------------------------

class PlannerAgent(BaseAgent):
    """规划代理 - 负责任务分解、调度和协调"""
    
    def __init__(self):
        super().__init__("planner_001", "规划代理", AgentType.PLANNER)
        self.task_decomposition_rules = {
            "research": ["技术调研", "竞品分析", "方案对比"],
            "code": ["需求分析", "架构设计", "代码实现", "单元测试"],
            "decision": ["信息收集", "约束分析", "方案生成", "风险评估"]
        }
    
    def decompose_task(self, task_title: str, task_description: str) -> List[SubTask]:
        """任务分解 - 将复杂任务分解为可执行的子任务"""
        # print(f"\n  🎯 [{self.name}] 开始任务分解: {task_title}")
        
        subtasks = []
        parent_task_id = f"task-{uuid.uuid4().hex[:6]}"
        
        # 根据任务类型选择分解策略
        task_type = self._identify_task_type(task_description)
        # print(f"     识别任务类型: {task_type}")
        
        decomposition_steps = self.task_decomposition_rules.get(task_type, ["信息收集", "分析处理", "结果输出"])
        
        for i, step in enumerate(decomposition_steps):
            subtask_id = f"{parent_task_id}-{i:03d}"
            agent_type = self._match_agent_type(step)
            
            # 计算依赖 (前一个任务是依赖)
            deps = [f"{parent_task_id}-{i-1:03d}"] if i > 0 else []
            
            subtask = SubTask(
                task_id=subtask_id,
                parent_task_id=parent_task_id,
                title=step,
                description=f"{task_description} - {step}",
                agent_type=agent_type,
                status=TaskStatus.PENDING,
                dependencies=deps
            )
            subtasks.append(subtask)
            # print(f"     ✅ 子任务 #{i}: {step} → {agent_type.value} (依赖: {len(deps)}个)")
        
        return subtasks
    
    def _identify_task_type(self, description: str) -> str:
        """识别任务类型"""
        keywords = {
            "research": ["研究", "调研", "调查", "收集", "综述", "对比"],
            "code": ["代码", "实现", "开发", "编程", "系统", "接口"],
            "decision": ["决策", "方案", "选择", "优化", "规划", "设计"]
        }
        
        for task_type, words in keywords.items():
            if any(w in description for w in words):
                return task_type
        return "general"
    
    def _match_agent_type(self, step: str) -> AgentType:
        """根据步骤匹配合适的Agent类型"""
        matching = {
            "调研": AgentType.RESEARCHER,
            "分析": AgentType.RESEARCHER,
            "收集": AgentType.RESEARCHER,
            "设计": AgentType.PLANNER,
            "架构": AgentType.CODER,
            "实现": AgentType.CODER,
            "编码": AgentType.CODER,
            "测试": AgentType.REVIEWER,
            "审查": AgentType.REVIEWER,
            "执行": AgentType.EXECUTOR
        }
        
        for keyword, agent_type in matching.items():
            if keyword in step:
                return agent_type
        
        # 默认根据任务类型分配
        if any(w in step for w in ["代码", "开发", "编程"]):
            return AgentType.CODER
        if any(w in step for w in ["研究", "调研"]):
            return AgentType.RESEARCHER
        if any(w in step for w in ["审查", "测试", "检查"]):
            return AgentType.REVIEWER
        
        return AgentType.EXECUTOR
    
    def _handle_message(self, msg: Message) -> Optional[Message]:
        """处理消息"""
        if msg.message_type == "new_task":
            # 分解任务
            subtasks = self.decompose_task(
                msg.payload.get("title", ""),
                msg.payload.get("description", "")
            )
            
            # 注册到状态管理器
            for task in subtasks:
                if self.state_manager:
                    self.state_manager.register_task(task)
            
            # 返回分解结果
            return self._create_message(
                msg.from_agent,
                "decomposition_complete",
                {
                    "original_task": msg.payload,
                    "subtasks_count": len(subtasks),
                    "subtasks": [asdict(t) for t in subtasks]
                }
            )
        
        return None


# -----------------------------------------------------------------------------
# 研究代理 (Researcher Agent)
# -----------------------------------------------------------------------------

class ResearcherAgent(BaseAgent):
    """研究代理 - 负责信息检索和知识收集"""
    
    def __init__(self, knowledge_level: str = "medium"):
        super().__init__(f"researcher_{uuid.uuid4().hex[:4]}", "研究代理", AgentType.RESEARCHER)
        self.knowledge_level = knowledge_level
        
        # 模拟知识库
        self.knowledge_base = {
            "多智能体架构": [
                "AutoGen: Microsoft开发的对话式多Agent框架",
                "LangGraph: LangChain的图状工作流引擎，支持循环和条件分支",
                "MetaGPT: 基于SOP的软件开发团队模拟框架",
                "CrewAI: 基于角色的Agent编排，支持工具集成"
            ],
            "性能优化": [
                "智能路由: 根据任务复杂度选择合适模型",
                "缓存机制: 相似任务结果复用，减少Token消耗",
                "并行执行: 独立子任务同时处理，缩短总时间",
                "增量更新: 只传输变更部分，减少网络开销"
            ],
            "质量保证": [
                "三级质量门: 自检→Review→验收",
                "反馈闭环: 不通过自动重写，持续改进",
                "交叉验证: 多个Agent验证同一结果",
                "置信度评分: 量化输出质量"
            ],
            "LLM模型对比": {
                "Kimi-K2.5": {"speed": 85, "quality": 90, "cost": "medium"},
                "Qwen-3.6": {"speed": 90, "quality": 85, "cost": "low"},
                "DeepSeek": {"speed": 75, "quality": 88, "cost": "low"},
                "Claude": {"speed": 70, "quality": 95, "cost": "high"}
            }
        }
    
    def _handle_message(self, msg: Message) -> Optional[Message]:
        """处理消息"""
        if msg.message_type == "task_assign":
            return self._execute_research(msg.payload)
        return None
    
    def _execute_research(self, payload: Dict) -> Message:
        """执行研究任务"""
        task_id = payload.get("task_id", "unknown")
        query = payload.get("query", "")
        
        # print(f"\n  🔍 [{self.name}] 开始研究任务: {query}")
        
        # 更新状态
        if self.state_manager:
            self.state_manager.update_task_status(task_id, TaskStatus.IN_PROGRESS)
        
        # 模拟研究过程
        time.sleep(random.uniform(1.0, 2.5))
        # print(f"     正在检索知识库...")
        time.sleep(0.5)
        
        # 查找相关知识
        findings = []
        for topic, content in self.knowledge_base.items():
            if any(k in query for k in topic.split()):
                if isinstance(content, list):
                    findings.extend(content)
                else:
                    findings.append(f"{topic}: {json.dumps(content, ensure_ascii=False)}")
        
        if not findings:
            findings = [
                "未找到精确匹配，进行通用知识检索",
                "多智能体协作是当前AI发展的重要方向",
                "专业化角色分工可显著提升输出质量",
                "状态管理和同步是协作系统的核心挑战"
            ]
        
        # print(f"     发现 {len(findings)} 条相关信息")
        
        # 构建结果
        result = {
            "summary": f"关于「{query}」的研究报告",
            "details": findings,
            "confidence": 0.85 + random.random() * 0.1,
            "sources_checked": random.randint(3, 8),
            "key_insights": self._extract_insights(findings)
        }
        
        # 一级质量检查 (自检)
        quality_result = self._quality_check(result, "research")
        
        # 写入共享记忆
        if self.state_manager:
            self.state_manager.write_shared_memory(
                f"research_{task_id}",
                {"query": query, "findings": findings, "result": result}
            )
        
        execution_log = (
            f"研究任务执行记录:\n"
            f"- 查询主题: {query}\n"
            f"- 检索数据源: {result['sources_checked']}个\n"
            f"- 发现相关信息: {len(findings)}条\n"
            f"- 质量自检得分: {quality_result.score:.1f}\n"
            f"- 置信度: {result['confidence']:.1%}\n"
            f"- 完成时间: {datetime.now().isoformat()}"
        )
        
        # 更新任务状态
        if self.state_manager:
            self.state_manager.update_task_status(task_id, TaskStatus.COMPLETED, result)
            self.state_manager.tasks[task_id].execution_log = execution_log
            self.state_manager.tasks[task_id].quality_score = quality_result.score
        
        # print(f"  ✅ [{self.name}] 研究完成 (质量得分: {quality_result.score:.1f})")
        
        return self._create_message(
            "orchestrator",
            "result_submit",
            {
                "task_id": task_id,
                "result": result,
                "quality_check": asdict(quality_result),
                "execution_log": execution_log
            }
        )
    
    def _extract_insights(self, findings: List[str]) -> List[str]:
        """提取关键洞察"""
        return [
            "💡 多智能体协作架构已成为行业标准",
            "💡 专业化角色分工提升效率和质量",
            "💡 状态管理是系统稳定性的关键",
            "💡 质量保证体系不可或缺"
        ]


# -----------------------------------------------------------------------------
# 编码代理 (Coder Agent)
# -----------------------------------------------------------------------------

class CoderAgent(BaseAgent):
    """编码代理 - 负责代码实现和功能开发"""
    
    def __init__(self):
        super().__init__(f"coder_{uuid.uuid4().hex[:4]}", "编码代理", AgentType.CODER)
    
    def _handle_message(self, msg: Message) -> Optional[Message]:
        """处理消息"""
        if msg.message_type == "task_assign":
            return self._execute_coding(msg.payload)
        return None
    
    def _execute_coding(self, payload: Dict) -> Message:
        """执行编码任务"""
        task_id = payload.get("task_id", "unknown")
        requirement = payload.get("requirement", "")
        
        # print(f"\n  💻 [{self.name}] 开始编码任务: {requirement}")
        
        # 更新状态
        if self.state_manager:
            self.state_manager.update_task_status(task_id, TaskStatus.IN_PROGRESS)
        
        # 模拟编码过程
        time.sleep(random.uniform(1.5, 3.0))
        # print(f"     正在分析需求...")
        time.sleep(0.5)
        # print(f"     正在编写代码...")
        time.sleep(0.5)
        # print(f"     正在添加注释...")
        
        # 生成示例代码
        code_result = self._generate_sample_code(requirement)
        
        result = {
            "summary": f"代码实现: {requirement}",
            "details": code_result,
            "confidence": 0.82 + random.random() * 0.15,
            "lines_of_code": len(code_result.split("\n")),
            "files_generated": 2
        }
        
        # 一级质量检查
        quality_result = self._quality_check(result, "code")
        
        execution_log = (
            f"编码任务执行记录:\n"
            f"- 需求: {requirement}\n"
            f"- 代码行数: {result['lines_of_code']}\n"
            f"- 生成文件数: {result['files_generated']}\n"
            f"- 质量自检得分: {quality_result.score:.1f}\n"
            f"- 置信度: {result['confidence']:.1%}"
        )
        
        if self.state_manager:
            self.state_manager.update_task_status(task_id, TaskStatus.COMPLETED, result)
            self.state_manager.tasks[task_id].execution_log = execution_log
            self.state_manager.tasks[task_id].quality_score = quality_result.score
        
        # print(f"  ✅ [{self.name}] 编码完成 (质量得分: {quality_result.score:.1f})")
        
        return self._create_message(
            "orchestrator",
            "result_submit",
            {
                "task_id": task_id,
                "result": result,
                "quality_check": asdict(quality_result),
                "execution_log": execution_log
            }
        )
    
    def _generate_sample_code(self, requirement: str) -> str:
        """生成示例代码"""
        return '''#!/usr/bin/env python3
"""
自动生成的示例代码
"""

import json
from typing import Dict, List

class MultiAgentOrchestrator:
    """多智能体编排器"""
    
    def __init__(self):
        self.agents = {}
        self.task_queue = []
    
    def register_agent(self, agent):
        """注册智能体"""
        self.agents[agent.agent_id] = agent
    
    def execute_task(self, task: Dict) -> Dict:
        """执行任务"""
        # 任务分解
        subtasks = self._decompose(task)
        
        # 并行执行
        results = []
        for subtask in subtasks:
            result = self._assign_and_execute(subtask)
            results.append(result)
        
        # 结果整合
        return self._integrate_results(results)
    
    def _decompose(self, task: Dict) -> List[Dict]:
        """任务分解"""
        return [{"type": "research", "query": task.get("query")}]
    
    def _assign_and_execute(self, subtask: Dict) -> Dict:
        """分配并执行子任务"""
        return {"status": "success", "data": {}}
    
    def _integrate_results(self, results: List[Dict]) -> Dict:
        """结果整合"""
        return {"status": "success", "results": results}
'''


# -----------------------------------------------------------------------------
# 审查代理 (Reviewer Agent) - 二级质量门
# -----------------------------------------------------------------------------

class ReviewerAgent(BaseAgent):
    """审查代理 - 负责质量审查和反馈 (二级质量门)"""
    
    def __init__(self):
        super().__init__(f"reviewer_{uuid.uuid4().hex[:4]}", "审查代理", AgentType.REVIEWER)
    
    def _handle_message(self, msg: Message) -> Optional[Message]:
        """处理消息"""
        if msg.message_type == "review_request":
            return self._execute_review(msg.payload)
        return None
    
    def _execute_review(self, payload: Dict) -> Message:
        """执行质量审查"""
        task_id = payload.get("task_id", "unknown")
        work_product = payload.get("work_product", {})
        original_task = payload.get("original_task", "")
        
        # print(f"\n  🔎 [{self.name}] 开始质量审查: {original_task}")
        
        # 二级质量检查 (Reviewer专业审查)
        quality_result = self._professional_review(work_product, original_task)
        
        # print(f"     审查完成 - 得分: {quality_result.score:.1f}, {'✅ 通过' if quality_result.passed else '❌ 需要改进'}")
        
        if quality_result.issues:
            # print(f"     发现问题: {len(quality_result.issues)}个")
            for issue in quality_result.issues[:3]:
                # print(f"       - {issue}")
        
        if quality_result.suggestions:
            # print(f"     改进建议: {len(quality_result.suggestions)}条")
        
        result = {
            "review_summary": f"质量审查报告: {original_task}",
            "quality_score": quality_result.score,
            "passed": quality_result.passed,
            "issues": quality_result.issues,
            "suggestions": quality_result.suggestions,
            "needs_rewrite": not quality_result.passed
        }
        
        execution_log = (
            f"质量审查记录:\n"
            f"- 审查对象: {original_task}\n"
            f"- 质量得分: {quality_result.score:.1f}\n"
            f"- 是否通过: {'是' if quality_result.passed else '否'}\n"
            f"- 发现问题: {len(quality_result.issues)}个\n"
            f"- 改进建议: {len(quality_result.suggestions)}条"
        )
        
        return self._create_message(
            "orchestrator",
            "review_complete",
            {
                "task_id": task_id,
                "review_result": result,
                "execution_log": execution_log
            }
        )
    
    def _professional_review(self, work_product: Dict, task_context: str) -> QualityCheckResult:
        """专业审查 - 二级质量门"""
        score = 85.0  # 基础分
        issues = []
        suggestions = []
        
        # 检查与原始需求的匹配度
        result_summary = str(work_product.get("summary", ""))
        if len(result_summary) < 20:
            score -= 15
            issues.append("结果摘要过于简短")
            suggestions.append("建议补充更详细的摘要信息")
        
        # 检查细节丰富度
        details = work_product.get("details", [])
        if isinstance(details, list) and len(details) < 3:
            score -= 10
            issues.append("细节内容不够丰富")
            suggestions.append("建议增加更多具体细节和数据")
        
        # 检查置信度
        confidence = work_product.get("confidence", 0)
        if confidence < 0.7:
            score -= 10
            issues.append(f"置信度较低 ({confidence:.1%})")
            suggestions.append("建议交叉验证或补充更多信息源")
        
        # 结构完整性检查
        required = ["summary", "details", "confidence"]
        missing = [f for f in required if f not in work_product]
        if missing:
            score -= len(missing) * 8
            issues.append(f"缺少关键字段: {', '.join(missing)}")
        
        passed = score >= 75
        feedback = f"专业审查得分: {score:.1f}/100"
        
        return QualityCheckResult(passed, score, feedback, issues, suggestions)


# -----------------------------------------------------------------------------
# 执行代理 (Executor Agent)
# -----------------------------------------------------------------------------

class ExecutorAgent(BaseAgent):
    """执行代理 - 负责脚本执行和任务自动化"""
    
    def __init__(self):
        super().__init__(f"executor_{uuid.uuid4().hex[:4]}", "执行代理", AgentType.EXECUTOR)
    
    def _handle_message(self, msg: Message) -> Optional[Message]:
        """处理消息"""
        if msg.message_type == "execute_command":
            return self._execute_command(msg.payload)
        return None
    
    def _execute_command(self, payload: Dict) -> Message:
        """执行命令"""
        task_id = payload.get("task_id", "unknown")
        command = payload.get("command", "")
        context = payload.get("context", {})
        
        # print(f"\n  ⚡ [{self.name}] 执行任务: {command}")
        
        if self.state_manager:
            self.state_manager.update_task_status(task_id, TaskStatus.IN_PROGRESS)
        
        # 模拟执行
        time.sleep(random.uniform(0.5, 1.5))
        # print(f"     正在执行...")
        
        success = random.random() > 0.1  # 90%成功率
        
        result = {
            "command": command,
            "success": success,
            "exit_code": 0 if success else 1,
            "output": f"命令执行成功: {command}" if success else f"命令执行失败: 模拟错误",
            "execution_time": random.uniform(0.3, 2.0)
        }
        
        quality_result = self._quality_check(result, "execution")
        
        if self.state_manager:
            self.state_manager.update_task_status(
                task_id,
                TaskStatus.COMPLETED if success else TaskStatus.FAILED,
                result
            )
        
        # print(f"  {'✅' if success else '❌'} [{self.name}] 执行{'成功' if success else '失败'}")
        
        return self._create_message(
            "orchestrator",
            "execution_complete",
            {
                "task_id": task_id,
                "result": result,
                "quality_check": asdict(quality_result)
            }
        )


# -----------------------------------------------------------------------------
# 编排器 (Orchestrator)
# -----------------------------------------------------------------------------

class MultiAgentOrchestrator:
    """多智能体编排器 - 协调所有Agent协作"""
    
    def __init__(self):
        self.state_manager = StateManager()
        self.agents: Dict[str, BaseAgent] = {}
        self.planner: Optional[PlannerAgent] = None
        
        # Agent池 - 每类Agent可以有多个实例
        self.agent_pools: Dict[AgentType, List[BaseAgent]] = defaultdict(list)
        
        # print("\n" + "="*70)
        # print("  🚀 多智能体协作框架 v5.0 原型启动")
        # print("="*70)
    
    def register_agent(self, agent: BaseAgent):
        """注册Agent"""
        agent.set_state_manager(self.state_manager)
        self.agents[agent.agent_id] = agent
        
        # 加入对应类型的池
        self.agent_pools[agent.agent_type].append(agent)
        
        if isinstance(agent, PlannerAgent):
            self.planner = agent
        
        # print(f"  ✅ 注册Agent: {agent.name} ({agent.agent_type.value})")
    
    def get_agent_for_task(self, agent_type: AgentType) -> Optional[BaseAgent]:
        """获取合适的Agent执行任务"""
        pool = self.agent_pools.get(agent_type, [])
        if not pool:
            # 降级 - 使用其他可用Agent
            for atype, agents in self.agent_pools.items():
                if agents:
                    # print(f"     ⚠️  无{agent_type.value}可用，降级使用{atype.value}")
                    return agents[0]
            return None
        # 简单轮询
        return pool[0]  # 简化: 总是返回第一个
    
    def execute_task(self, task_title: str, task_description: str) -> Dict[str, Any]:
        """执行完整的多智能体协作任务"""
        
        # print(f"\n{'='*70}")
        # print(f"  📋 任务开始: {task_title}")
        # print(f"  📝 描述: {task_description[:80]}..." if len(task_description) > 80 else f"  📝 描述: {task_description}")
        # print(f"{'='*70}")
        
        start_time = time.time()
        
        # ─── 阶段1: Planner 任务分解 ───
        # print(f"\n📦 阶段 1/4: Planner任务分解")
        # print("-" * 70)
        
        if not self.planner:
            return {"status": "failed", "error": "No planner registered"}
        
        # 发送新任务消息给Planner
        new_task_msg = Message(
            message_id=f"msg-{uuid.uuid4().hex[:8]}",
            from_agent="user",
            to_agent=self.planner.agent_id,
            message_type="new_task",
            timestamp=datetime.now().isoformat(),
            payload={"title": task_title, "description": task_description}
        )
        
        self.planner.receive_message(new_task_msg)
        responses = self.planner.process_messages()
        
        if not responses:
            return {"status": "failed", "error": "Planner did not respond"}
        
        decomposition_result = responses[0].payload
        
        # ─── 阶段2: 并行执行子任务 ───
        # print(f"\n📦 阶段 2/4: 子任务并行执行")
        # print("-" * 70)
        
        completed_count = 0
        total_subtasks = decomposition_result["subtasks_count"]
        
        while completed_count < total_subtasks:
            # 获取可以执行的任务
            ready_tasks = self.state_manager.get_ready_tasks()
            
            if not ready_tasks:
                # 等待依赖
                time.sleep(0.5)
                continue
            
            for task in ready_tasks:
                # 分配给对应Agent
                agent = self.get_agent_for_task(task.agent_type)
                if not agent:
                    # print(f"  ⚠️  无可用Agent处理任务: {task.title}")
                    continue
                
                # 发送任务分配消息
                task_msg = Message(
                    message_id=f"msg-{uuid.uuid4().hex[:8]}",
                    from_agent="orchestrator",
                    to_agent=agent.agent_id,
                    message_type="task_assign",
                    timestamp=datetime.now().isoformat(),
                    payload={
                        "task_id": task.task_id,
                        "query": task.description,
                        "requirement": task.description
                    }
                )
                
                agent.receive_message(task_msg)
                agent_responses = agent.process_messages()
                
                if agent_responses:
                    completed_count += 1
                    # print(f"  ✅ 子任务完成 ({completed_count}/{total_subtasks})")
        
        # ─── 阶段3: Reviewer质量审查 ───
        # print(f"\n📦 阶段 3/4: Reviewer质量审查")
        # print("-" * 70)
        
        reviewer = self.get_agent_for_task(AgentType.REVIEWER)
        if reviewer:
            # 对每个完成的任务进行审查
            review_count = 0
            for task in self.state_manager.tasks.values():
                if task.status == TaskStatus.COMPLETED and task.result:
                    review_msg = Message(
                        message_id=f"msg-{uuid.uuid4().hex[:8]}",
                        from_agent="orchestrator",
                        to_agent=reviewer.agent_id,
                        message_type="review_request",
                        timestamp=datetime.now().isoformat(),
                        payload={
                            "task_id": task.task_id,
                            "work_product": task.result,
                            "original_task": task.title
                        }
                    )
                    reviewer.receive_message(review_msg)
                    reviewer.process_messages()
                    review_count += 1
            
            # print(f"  ✅ 完成 {review_count} 个任务的质量审查")
        
        # ─── 阶段4: 结果整合 ───
        # print(f"\n📦 阶段 4/4: 结果整合")
        # print("-" * 70)
        
        total_time = time.time() - start_time
        progress = self.state_manager.get_progress()
        
        # 收集所有结果
        all_results = []
        total_quality_score = 0.0
        quality_count = 0
        
        for task in self.state_manager.tasks.values():
            if task.result:
                all_results.append({
                    "task_id": task.task_id,
                    "title": task.title,
                    "result": task.result,
                    "quality_score": task.quality_score
                })
                if task.quality_score > 0:
                    total_quality_score += task.quality_score
                    quality_count += 1
        
        avg_quality = total_quality_score / quality_count if quality_count > 0 else 0
        
        final_result = {
            "status": "success",
            "original_task": task_title,
            "original_description": task_description,
            "total_execution_time": total_time,
            "subtasks_count": total_subtasks,
            "agents_involved": len(self.agents),
            "messages_exchanged": progress["messages_exchanged"],
            "average_quality_score": avg_quality,
            "subtask_results": all_results,
            "summary": f"多智能体协作任务完成 - 共{total_subtasks}个子任务，耗时{total_time:.2f}秒，平均质量得分{avg_quality:.1f}"
        }
        
        # print(f"\n{'='*70}")
        # print("  🎉 多智能体协作任务完成!")
        # print(f"  📊 统计数据:")
        # print(f"     - 总耗时: {total_time:.2f}秒")
        # print(f"     - 子任务数: {total_subtasks}个")
        # print(f"     - 参与Agent: {len(self.agents)}个")
        # print(f"     - 消息交换: {progress['messages_exchanged']}条")
        # print(f"     - 平均质量: {avg_quality:.1f}分")
        # print(f"{'='*70}")
        
        return final_result


# -----------------------------------------------------------------------------
# 标准测试用例
# -----------------------------------------------------------------------------

class MultiAgentBenchmark:
    """多智能体性能基准测试"""
    
    def __init__(self):
        self.test_cases = [
            {
                "name": "信息检索任务",
                "title": "多智能体框架技术选型调研",
                "description": "研究对比AutoGen、LangGraph、MetaGPT三种多智能体框架的优缺点，给出技术选型建议",
                "type": "research"
            },
            {
                "name": "代码生成任务",
                "title": "REST API接口开发",
                "description": "设计并实现一个用户管理的REST API接口，包含CRUD操作",
                "type": "code"
            },
            {
                "name": "复杂决策任务",
                "title": "LLM模型智能路由方案设计",
                "description": "设计一个LLM模型智能路由系统，根据任务类型、复杂度、成本约束选择最优模型",
                "type": "decision"
            }
        ]
    
    def run_single_agent_test(self, test_case: Dict) -> Dict:
        """单Agent基线测试"""
        # print(f"\n{'#'*70}")
        # print(f"  🧪 单Agent基线测试: {test_case['name']}")
        # print(f"{'#'*70}")
        
        start_time = time.time()
        
        # 模拟单Agent处理整个任务
        researcher = ResearcherAgent()
        
        # 单Agent串行完成所有工作
        msg = Message(
            message_id=f"msg-{uuid.uuid4().hex[:8]}",
            from_agent="test",
            to_agent=researcher.agent_id,
            message_type="task_assign",
            timestamp=datetime.now().isoformat(),
            payload={
                "task_id": "single-agent-test",
                "query": test_case["description"]
            }
        )
        
        researcher.receive_message(msg)
        responses = researcher.process_messages()
        
        total_time = time.time() - start_time
        
        result = {
            "test_name": test_case["name"],
            "mode": "single_agent",
            "total_time": total_time,
            "agent_count": 1,
            "messages_exchanged": 1,
            "quality_score": responses[0].payload["quality_check"]["score"] if responses else 0,
            "success": len(responses) > 0
        }
        
        # print(f"  ✅ 单Agent测试完成: {total_time:.2f}秒, 质量: {result['quality_score']:.1f}分")
        return result
    
    def run_multi_agent_test(self, test_case: Dict) -> Dict:
        """多Agent协作测试"""
        # print(f"\n{'#'*70}")
        # print(f"  🧪 多Agent协作测试: {test_case['name']}")
        # print(f"{'#'*70}")
        
        # 创建编排器
        orchestrator = MultiAgentOrchestrator()
        
        # 注册所有Agent
        orchestrator.register_agent(PlannerAgent())
        orchestrator.register_agent(ResearcherAgent())
        orchestrator.register_agent(ResearcherAgent())  # 第二个Researcher
        orchestrator.register_agent(CoderAgent())
        orchestrator.register_agent(ReviewerAgent())
        orchestrator.register_agent(ExecutorAgent())
        
        # 执行任务
        result = orchestrator.execute_task(
            test_case["title"],
            test_case["description"]
        )
        
        return {
            "test_name": test_case["name"],
            "mode": "multi_agent",
            "total_time": result.get("total_execution_time", 0),
            "agent_count": result.get("agents_involved", 0),
            "messages_exchanged": result.get("messages_exchanged", 0),
            "quality_score": result.get("average_quality_score", 0),
            "success": result.get("status") == "success",
            "subtasks_count": result.get("subtasks_count", 0)
        }
    
    def run_comparison(self, runs_per_test: int = 3) -> Dict:
        """运行完整的对比测试"""
        # print("\n" + "="*70)
        # print("  📊 开始多智能体协作框架性能对比测试")
        # print(f"  每个测试用例运行 {runs_per_test} 次取平均值")
        # print("="*70)
        
        all_results = {
            "single_agent": [],
            "multi_agent": [],
            "comparison": {}
        }
        
        for test_case in self.test_cases:
            # print(f"\n\n📋 处理测试用例: {test_case['name']}")
            # print("="*70)
            
            # 单Agent测试
            single_times = []
            single_qualities = []
            for i in range(runs_per_test):
                # print(f"\n  单Agent测试 - 第{i+1}/{runs_per_test}次")
                result = self.run_single_agent_test(test_case)
                single_times.append(result["total_time"])
                single_qualities.append(result["quality_score"])
                all_results["single_agent"].append(result)
                time.sleep(0.5)
            
            # 多Agent测试
            multi_times = []
            multi_qualities = []
            for i in range(runs_per_test):
                # print(f"\n  多Agent测试 - 第{i+1}/{runs_per_test}次")
                result = self.run_multi_agent_test(test_case)
                multi_times.append(result["total_time"])
                multi_qualities.append(result["quality_score"])
                all_results["multi_agent"].append(result)
                time.sleep(0.5)
            
            # 计算平均值
            avg_single_time = sum(single_times) / len(single_times)
            avg_multi_time = sum(multi_times) / len(multi_times)
            avg_single_quality = sum(single_qualities) / len(single_qualities)
            avg_multi_quality = sum(multi_qualities) / len(multi_qualities)
            
            time_improvement = ((avg_single_time - avg_multi_time) / avg_single_time) * 100
            quality_improvement = ((avg_multi_quality - avg_single_quality) / avg_single_quality) * 100
            
            all_results["comparison"][test_case["name"]] = {
                "single_agent": {
                    "avg_time": avg_single_time,
                    "avg_quality": avg_single_quality
                },
                "multi_agent": {
                    "avg_time": avg_multi_time,
                    "avg_quality": avg_multi_quality
                },
                "improvement": {
                    "time_percent": time_improvement,
                    "quality_percent": quality_improvement
                }
            }
        
        return all_results


# -----------------------------------------------------------------------------
# 主程序入口
# -----------------------------------------------------------------------------

def main():
    """主程序"""
    
    # 演示1: 多智能体协作完整流程
    # print("\n" + "="*70)
    # print("  🎯 演示1: 多智能体协作完整流程")
    # print("="*70)
    
    orchestrator = MultiAgentOrchestrator()
    
    # 注册Agent
    orchestrator.register_agent(PlannerAgent())
    orchestrator.register_agent(ResearcherAgent())
    orchestrator.register_agent(CoderAgent())
    orchestrator.register_agent(ReviewerAgent())
    orchestrator.register_agent(ExecutorAgent())
    
    # 执行一个示例任务
    result = orchestrator.execute_task(
        "多智能体框架技术选型调研",
        "研究对比AutoGen、LangGraph、MetaGPT三种多智能体框架的优缺点，给出技术选型建议"
    )
    
    # 保存状态
    state_file = "/Users/mettlyz/.openclaw/workspace/output/task-1794/demo_state.json"
    orchestrator.state_manager.save_state(state_file)
    # print(f"\n💾 状态已保存到: {state_file}")
    
    # 演示2: 性能基准测试
    # print("\n" + "="*70)
    # print("  🎯 演示2: 性能基准测试 (简化版)")
    # print("="*70)
    
    benchmark = MultiAgentBenchmark()
    
    # 运行一个测试用例的对比
    test_case = benchmark.test_cases[0]
    single_result = benchmark.run_single_agent_test(test_case)
    multi_result = benchmark.run_multi_agent_test(test_case)
    
    # 输出对比总结
    # print("\n" + "="*70)
    # print("  📊 性能对比总结")
    # print("="*70)
    # print(f"\n  测试用例: {test_case['name']}")
    # print(f"\n  单Agent模式:")
    # print(f"    - 耗时: {single_result['total_time']:.2f}秒")
    # print(f"    - 质量: {single_result['quality_score']:.1f}分")
    # print(f"\n  多Agent模式:")
    # print(f"    - 耗时: {multi_result['total_time']:.2f}秒")
    # print(f"    - 质量: {multi_result['quality_score']:.1f}分")
    # print(f"    - 子任务: {multi_result['subtasks_count']}个")
    # print(f"    - Agent数: {multi_result['agent_count']}个")
    
    time_imp = ((single_result['total_time'] - multi_result['total_time']) / single_result['total_time']) * 100
    quality_imp = ((multi_result['quality_score'] - single_result['quality_score']) / single_result['quality_score']) * 100
    
    # print(f"\n  提升效果:")
    # print(f"    - 时间效率: {'+' if time_imp > 0 else ''}{time_imp:.1f}%")
    # print(f"    - 质量提升: {'+' if quality_imp > 0 else ''}{quality_imp:.1f}%")
    # print("\n" + "="*70)
    # print("  ✅ 原型演示完成!")
    # print("="*70 + "\n")


if __name__ == "__main__":
    main()
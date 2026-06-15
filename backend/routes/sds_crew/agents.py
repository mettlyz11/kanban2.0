#!/usr/bin/env python3
"""
SDS Agent 实现 - 对接真实 SDS 脚本和 actor_api

每个 Agent 对应 SDS 的一个任务领域：
  - DiagnosticAgent (诊断): 调用 push_actor_filter 扫描失败任务
  - AnalysisAgent (分析): 分析诊断结果，评估影响
  - StrategyAgent (策略): 制定修复计划
  - ExecutorAgent (执行): 执行修复（调用 llm_auditor, actor_db_fix）
  - ReporterAgent (报告): 生成执行报告
  - SupervisorAgent (监督): 监控流程，异常时介入
"""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime

from .framework import (
    SDSAgent, 
    run_push_actor_filter, 
    run_llm_auditor, 
    run_actor_db_fix,
)

logger = logging.getLogger(__name__)


# ─── Agent 实现 ─────────────────────────────────────────────────

class DiagnosticAgent(SDSAgent):
    """
    诊断 Agent - 子墨 🔬
    
    职责：扫描系统状态，发现失败任务、代码问题、DB异常
    工具：push_actor_filter（扫描失败任务）
    """
    def __init__(self):
        super().__init__(
            role="researcher",
            name="子墨",
            tools=["push_actor_filter_scan", "system_check", "log_analyzer"],
            prompt="你是博学审问的子墨，精于格物致知。"
                   "扫描系统状态，发现并报告所有潜在问题。"
        )
    
    async def _do_execute(self, task: Dict[str, Any]) -> Any:
        """执行系统诊断 - 调用真实 push_actor_filter"""
        scan_type = task.get("type", "quick")
        
        if scan_type in ("full_scan", "scan"):
            # 调用真实 SDS 脚本
            result = run_push_actor_filter()
            issues = []
            
            if result.get("ok"):
                report = result["result"].get("report", "")
                # 解析报告中的问题
                if "失败" in report or "❌" in report:
                    issues.append({"type": "failed_tasks", 
                                   "detail": "存在失败任务需修复"})
                if "需人工" in report or "问扮演者" in report:
                    issues.append({"type": "needs_human",
                                   "detail": "存在需人工介入的任务"})
            
            return {
                "scan_type": scan_type,
                "diagnosis": "扫描完成" if len(issues) == 0 
                             else f"发现{len(issues)}个问题",
                "issues": issues,
                "raw_report": result.get("result", {}).get("report", ""),
                "healthy": len(issues) == 0,
                "timestamp": datetime.now().isoformat(),
            }
        
        return {
            "scan_type": scan_type,
            "diagnosis": "系统正常",
            "issues": [],
            "healthy": True,
            "timestamp": datetime.now().isoformat(),
        }


class AnalysisAgent(SDSAgent):
    """
    分析 Agent - 计然 📊
    
    职责：分析诊断结果，评估影响范围和优先级
    工具：impact_assessment, cost_benefit
    """
    def __init__(self):
        super().__init__(
            role="analyst",
            name="计然",
            tools=["impact_assessment", "priority_eval"],
            prompt="你是计然后人，深谙商道。"
                   "分析问题影响，评估优先级。"
        )
    
    async def _do_execute(self, task: Dict[str, Any]) -> Any:
        """分析诊断结果"""
        diag = task.get("result", {})
        issues = diag.get("issues", [])
        healthy = diag.get("healthy", True)
        
        if healthy:
            return {
                "impact": "none",
                "priority": "low",
                "recommendation": "系统正常，无需干预",
                "requires_action": False,
            }
        
        # 分析问题严重性
        failed_count = sum(1 for i in issues if i["type"] == "failed_tasks")
        human_count = sum(1 for i in issues if i["type"] == "needs_human")
        
        if human_count > 0:
            impact = "high"
            priority = "critical"
        elif failed_count > 0:
            impact = "medium"
            priority = "high"
        else:
            impact = "low"
            priority = "normal"
        
        return {
            "impact": impact,
            "priority": priority,
            "recommendation": f"发现{failed_count}个失败任务和{human_count}个需人工任务",
            "requires_action": failed_count > 0 or human_count > 0,
            "assessment": {
                "failed_tasks": failed_count,
                "needs_human": human_count,
            }
        }


class StrategyAgent(SDSAgent):
    """
    策略 Agent - 卧龙 🧠
    
    职责：制定修复策略和行动计划
    工具：project_db, kanban_status
    """
    def __init__(self):
        super().__init__(
            role="strategist",
            name="卧龙",
            tools=["project_db", "kanban_status", "plan_generator"],
            prompt="你如诸葛孔明般洞悉全局。"
                   "制定最优的修复策略和行动计划。"
        )
    
    async def _do_execute(self, task: Dict[str, Any]) -> Any:
        """制定修复策略"""
        analysis = task.get("result", {})
        requires_action = analysis.get("requires_action", False)
        
        if not requires_action:
            return {
                "strategy": "无操作",
                "steps": [],
                "action_plan": "系统健康，无需修复",
            }
        
        impact = analysis.get("impact", "low")
        priority = analysis.get("priority", "normal")
        
        steps = []
        if priority in ("critical", "high"):
            steps.append({"step": 1, "action": "run_push_actor_filter", 
                         "description": "重试失败任务"})
            steps.append({"step": 2, "action": "run_llm_auditor",
                         "description": "检查代码健康"})
            steps.append({"step": 3, "action": "run_actor_db_fix",
                         "description": "修复数据库问题"})
        else:
            steps.append({"step": 1, "action": "run_actor_db_fix",
                         "description": "执行数据库维护"})
        
        return {
            "strategy": f"按优先级{priority}执行{len(steps)}步修复",
            "steps": steps,
            "action_plan": json.dumps(steps, ensure_ascii=False),
        }


class ExecutorAgent(SDSAgent):
    """
    执行 Agent - 执行者 🔧
    
    职责：实际执行修复操作
    工具：push_actor_filter, llm_auditor, actor_db_fix
    """
    def __init__(self):
        super().__init__(
            role="executor",
            name="执行者",
            tools=["push_actor_filter", "llm_auditor", "actor_db_fix"],
            prompt="你是精准高效的执行者。"
                   "执行修复操作并记录结果。"
        )
    
    async def _do_execute(self, task: Dict[str, Any]) -> Any:
        """执行修复"""
        strategy = task.get("result", {})
        steps = strategy.get("steps", [])
        executed = []
        errors = []
        
        for step in steps:
            action = step.get("action", "")
            try:
                if action == "run_push_actor_filter":
                    result = run_push_actor_filter()
                    executed.append({"action": action, "status": "ok",
                                     "detail": result.get("result", {})})
                elif action == "run_llm_auditor":
                    result = run_llm_auditor()
                    executed.append({"action": action, "status": "ok",
                                     "detail": result.get("result", {})})
                elif action == "run_actor_db_fix":
                    result = run_actor_db_fix()
                    executed.append({"action": action, "status": "ok",
                                     "detail": result.get("result", {})})
                else:
                    executed.append({"action": action, "status": "skipped",
                                     "detail": "未知操作"})
            except Exception as e:
                errors.append({"action": action, "error": str(e)})
                executed.append({"action": action, "status": "failed",
                                 "error": str(e)})
        
        return {
            "executed": executed,
            "errors": errors,
            "success": len(errors) == 0,
            "total": len(steps),
            "completed": len(executed),
            "timestamp": datetime.now().isoformat(),
        }


class ReporterAgent(SDSAgent):
    """
    报告 Agent - 记录员 📝
    
    职责：生成自愈流程报告
    """
    def __init__(self):
        super().__init__(
            role="reporter",
            name="记录员",
            tools=["report_generator"],
            prompt="你是严谨的记录员。"
                   "生成清晰的自愈报告。"
        )
    
    async def _do_execute(self, task: Dict[str, Any]) -> Any:
        """生成报告"""
        results = task.get("result", {})
        
        summary_lines = [
            "## 🤖 SDS 自愈周期报告",
            f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "### 各阶段结果",
        ]
        
        for stage, result in results.items():
            ok = result.get("ok", False)
            agent = result.get("agent", stage)
            emoji = "✅" if ok else "❌"
            summary_lines.append(f"\n#### {stage} {emoji}")
            summary_lines.append(f"- Agent: {agent}")
            
            if ok:
                res = result.get("result", {})
                if isinstance(res, dict):
                    for k, v in res.items():
                        if not isinstance(v, (dict, list)):
                            summary_lines.append(f"- {k}: {v}")
            else:
                summary_lines.append(f"- 错误: {result.get('error', '未知')}")
                guidance = result.get("guidance", "")
                if guidance:
                    summary_lines.append(f"- 扮演者建议: {guidance[:200]}")
        
        summary = "\n".join(summary_lines)
        
        # 写入日志文件
        log_path = f"/tmp/sds_crew_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        try:
            with open(log_path, "w") as f:
                f.write(summary)
        except Exception:
            pass
        
        return {
            "report": summary,
            "log_path": log_path if 'log_path' in dir() else "",
            "stages": list(results.keys()),
            "all_ok": all(r.get("ok", False) for r in results.values()),
        }


class SupervisorAgent(SDSAgent):
    """
    监督 Agent - 监督者 👁️
    
    职责：监控整个流程，异常时介入
    """
    def __init__(self):
        super().__init__(
            role="supervisor",
            name="监督者",
            tools=["health_check", "monitor", "alert"],
            prompt="你是警觉的监督者。"
                   "监控系统健康，发现异常及时介入。"
        )
    
    async def _do_execute(self, task: Dict[str, Any]) -> Any:
        """监督流程执行"""
        results = task.get("result", {})
        errors = []
        
        for stage, result in results.items():
            if not result.get("ok", False):
                errors.append({
                    "stage": stage,
                    "agent": result.get("agent", "unknown"),
                    "error": result.get("error", "未知错误"),
                })
        
        return {
            "healthy": len(errors) == 0,
            "errors": errors,
            "error_count": len(errors),
            "summary": f"流程完成，发现{len(errors)}个错误" if errors else "流程顺利",
            "timestamp": datetime.now().isoformat(),
        }


# ─── 工厂函数 ──────────────────────────────────────────────────

def create_all_agents() -> Dict[str, SDSAgent]:
    """创建所有 Agent 实例"""
    return {
        "diagnostic": DiagnosticAgent(),
        "analysis": AnalysisAgent(),
        "strategy": StrategyAgent(),
        "executor": ExecutorAgent(),
        "reporter": ReporterAgent(),
        "supervisor": SupervisorAgent(),
    }

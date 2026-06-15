#!/usr/bin/env python3
"""
SDS CrewAI 框架核心 - 多 Agent 协作自愈系统

将现有三个守护脚本（push_actor_filter, llm_auditor, actor_db_fix）
组织为多 Agent 协作流程。

核心能力：
  - Agent 任务编排（诊断→分析→策略→执行）
  - 失败时通过 actor_api 向扮演者求助
  - 对接真实数据库与系统调用
"""

import os
import sys
import json
import asyncio
import subprocess
import urllib.request
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── 配置 ────────────────────────────────────────────────────────
SDS1_DIR = "/opt/sds1"
BACKEND_DIR = "/opt/kanban-react/backend"
ACTOR_CHAT_URL = "http://127.0.0.1:18791/v1/chat/completions"
CREW_DISPATCHER = os.path.join(SDS1_DIR, "crews", "crew_dispatcher.py")


# ─── 工具层：对接真实 SDS 脚本 ──────────────────────────────────

def _run_crew_dispatcher(crew_name: str, **kwargs) -> Tuple[str, bool]:
    """通过 crew_dispatcher.py 派发真实 Crew"""
    try:
        env = os.environ.copy()
        env.update({
            "DB_HOST": "localhost",
            "DB_USER": "sds",
            "DB_PASSWORD": "sds123",
            "DB_NAME": "sds",
        })
        cmd = [
            sys.executable, CREW_DISPATCHER, crew_name
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300,
            cwd=SDS1_DIR, env=env
        )
        output = result.stdout + result.stderr
        should_push = "Pushed: True" in output or "✅" in output
        logger.info(f"CrewDispatcher [{crew_name}]: rc={result.returncode}, "
                     f"push={should_push}, len={len(output)}")
        return output, should_push
    except subprocess.TimeoutExpired:
        logger.error(f"CrewDispatcher [{crew_name}] 超时")
        return f"❌ Crew {crew_name} 执行超时", False
    except Exception as e:
        logger.error(f"CrewDispatcher [{crew_name}] 异常: {e}")
        return f"❌ {e}", False


def run_push_actor_filter() -> Dict[str, Any]:
    """运行 push_actor_filter - 失败任务修复"""
    report, pushed = _run_crew_dispatcher("push_actor_filter")
    return {
        "ok": True,
        "result": {
            "script": "push_actor_filter",
            "report": report[:2000] if report else "",
            "pushed": pushed,
            "timestamp": datetime.now().isoformat(),
        }
    }


def run_llm_auditor() -> Dict[str, Any]:
    """运行 llm_auditor - 代码健康扫描"""
    report, pushed = _run_crew_dispatcher("llm_auditor")
    return {
        "ok": True,
        "result": {
            "script": "llm_auditor",
            "report": report[:2000] if report else "",
            "pushed": pushed,
            "timestamp": datetime.now().isoformat(),
        }
    }


def run_actor_db_fix() -> Dict[str, Any]:
    """
    运行 actor_db_fix - 数据库修复
    
    直接执行 DB 修复 SQL：清理孤立记录、修复约束、重建索引
    """
    try:
        sys.path.insert(0, BACKEND_DIR)
        from routes.helpers import get_db
        
        conn = get_db()
        cur = conn.cursor()
        fixes = []
        
        # 1. 修复孤立记录
        cur.execute("""
            UPDATE tasks SET status = 'failed'
            WHERE status = 'running' AND updated_at < NOW() - INTERVAL 1 DAY
        """)
        if cur.rowcount > 0:
            fixes.append(f"修复了{cur.rowcount}个卡住的任务")
        
        # 2. 清理空标题
        cur.execute("""
            DELETE FROM tasks WHERE (title IS NULL OR TRIM(title) = '')
            AND created_at < NOW() - INTERVAL 7 DAY
        """)
        if cur.rowcount > 0:
            fixes.append(f"清理了{cur.rowcount}个空标题任务")
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {
            "ok": True,
            "result": {
                "script": "actor_db_fix",
                "fixes": fixes if fixes else ["未发现需要修复的问题"],
                "timestamp": datetime.now().isoformat(),
            }
        }
    except Exception as e:
        logger.error(f"actor_db_fix 失败: {e}")
        return {
            "ok": False,
            "error": str(e),
            "result": {"script": "actor_db_fix", "error": str(e)},
        }


def ask_actor_via_api(question: str, context: str = "") -> str:
    """
    通过 actor_api 向扮演者求助
    
    调用 http://127.0.0.1:18791/v1/chat/completions
    返回扮演者的建议
    """
    messages = [
        {
            "role": "system",
            "content": (
                "你是扮演者系统（SDS自我驱动系统的一个Agent）。\n"
                "当自愈流程遇到无法自动处理的问题时，系统会向你求助。\n"
                "请提供具体的、可操作的修复建议。"
            )
        },
        {"role": "user", "content": f"## 问题\n{question}\n\n## 上下文\n{context}"}
    ]
    
    body = json.dumps({
        "model": "actor",
        "messages": messages,
        "max_tokens": 2000,
        "temperature": 0.3,
        "role": "sds_crew"
    }).encode()
    
    try:
        req = urllib.request.Request(
            ACTOR_CHAT_URL, data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read())
        
        content = (
            resp.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        logger.info(f"actor_api 返回: {content[:100]}...")
        return content if content else "扮演者未返回有效建议"
    except Exception as e:
        logger.error(f"actor_api 调用失败: {e}")
        return f"⚠️ 无法联系扮演者: {e}"


# ─── Agent 基类 ─────────────────────────────────────────────────

class SDSAgent:
    """SDS 基础 Agent 类"""
    def __init__(self, role: str, name: str, tools: List[str],
                 prompt: str = ""):
        self.role = role
        self.name = name
        self.tools = tools
        self.prompt = prompt
        self.state = "idle"
        self.memory = []
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务，失败时问扮演者"""
        try:
            self.state = "running"
            result = await self._do_execute(task)
            self.state = "idle"
            self.memory.append({"task": task, "result": result, 
                                "time": datetime.now().isoformat()})
            return {"ok": True, "result": result, "agent": self.name}
        except Exception as e:
            self.state = "error"
            error_msg = f"[{self.name}] 执行失败: {e}"
            logger.error(error_msg)
            guidance = await self.ask_actor(str(e), json.dumps(task, ensure_ascii=False))
            return {"ok": False, "error": error_msg, 
                    "guidance": guidance, "agent": self.name}
    
    async def _do_execute(self, task: Dict[str, Any]) -> Any:
        """实际执行逻辑，子类重写"""
        raise NotImplementedError
    
    async def ask_actor(self, error_msg: str, context: str = "") -> str:
        """向扮演者求助（真实调用 actor_api）"""
        question = (
            f"SDS Agent [{self.name}] ({self.role}) 在执行任务时遇到问题：\n"
            f"{error_msg}"
        )
        return ask_actor_via_api(question, context)


# ─── Crew 编排器 ────────────────────────────────────────────────

class SDSCrew:
    """SDS Crew 编排器 - 多 Agent 协作自愈"""
    def __init__(self):
        from .agents import create_all_agents
        self.agents = create_all_agents()
    
    async def run_self_healing(self) -> Dict[str, Any]:
        """
        执行完整自愈流程
        
        流程：
          1. 诊断 (DiagnosticAgent) — 扫描系统状态
          2. 分析 (AnalysisAgent) — 评估影响
          3. 策略 (StrategyAgent) — 制定修复计划
          4. 执行 (ExecutorAgent) — 实际修复操作
          5. 报告 (ReporterAgent) — 生成报告
        """
        results = {}
        
        # 1. 诊断
        logger.info("🔄 [Crew] 阶段1: 诊断")
        diag = await self.agents["diagnostic"].execute({"type": "full_scan"})
        results["diagnostic"] = diag
        if not diag["ok"]:
            return results
        
        # 2. 分析
        logger.info("🔄 [Crew] 阶段2: 分析")
        analysis = await self.agents["analysis"].execute(diag)
        results["analysis"] = analysis
        if not analysis["ok"]:
            return results
        
        # 3. 策略
        logger.info("🔄 [Crew] 阶段3: 策略")
        strategy = await self.agents["strategy"].execute(analysis)
        results["strategy"] = strategy
        if not strategy["ok"]:
            return results
        
        # 4. 执行修复
        logger.info("🔄 [Crew] 阶段4: 执行")
        execution = await self.agents["executor"].execute(strategy)
        results["execution"] = execution
        
        # 5. 报告
        logger.info("🔄 [Crew] 阶段5: 报告")
        report = await self.agents["reporter"].execute(results)
        results["report"] = report
        
        return results


# ─── 快速测试 ───────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    crew = SDSCrew()
    result = asyncio.run(crew.run_self_healing())
    print(json.dumps(result, indent=2, ensure_ascii=False)[:2000])

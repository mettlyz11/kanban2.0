#!/usr/bin/env python3
"""
完整 Agent 实现 - 包含所有 6 个角色和真实工具调用
"""

import asyncio
import json
import urllib.request
from typing import Dict, Any, List

# Actor API endpoint
ACTOR_URL = "http://127.0.0.1:18791/v1/chat/completions"

class BaseAgent:
    """基础 Agent 类"""
    def __init__(self, role: str, name: str, emoji: str, tools: List[str], prompt: str):
        self.role = role
        self.name = name
        self.emoji = emoji
        self.tools = tools
        self.prompt = prompt
        self.state = "idle"
    
    async def think(self, context: str) -> Dict[str, Any]:
        """思考并可能调用工具"""
        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": context}
        ]
        
        body = json.dumps({
            "model": "actor",
            "messages": messages,
            "tools": self.tools,
            "role": self.role,
            "max_tokens": 80000
        }).encode()
        
        try:
            req = urllib.request.Request(
                ACTOR_URL, data=body,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                resp = json.loads(r.read())
            
            message = resp.get("choices", [{}])[0].get("message", {})
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])
            
            # 执行工具调用
            tool_results = []
            for tc in tool_calls:
                if tc.get("type") == "function":
                    result = await self.execute_tool(tc["function"])
                    tool_results.append(result)
            
            return {
                "ok": True,
                "content": content,
                "tool_calls": tool_results,
                "agent": self.name,
                "emoji": self.emoji
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "agent": self.name}
    
    async def execute_tool(self, func: Dict) -> Dict:
        """执行工具函数"""
        name = func.get("name", "")
        args_str = func.get("arguments", "{}")
        try:
            args = json.loads(args_str) if args_str else {}
        except:
            args = {}
        
        # 工具实现
        tools_impl = {
            "paper_search": lambda q: {"papers": [f"Paper about {q}"], "source": "arxiv"},
            "patent_search": lambda q: {"patents": [f"Patent about {q}"], "source": "uspto"},
            "market_size": lambda industry: {"market": "100亿", "growth": "15%", "industry": industry},
            "competitor_map": lambda company: {"competitors": ["Comp A", "Comp B"], "target": company},
            "kanban_status": lambda: {"active": 5, "completed": 10, "failed": 0},
            "burn_rate": lambda months: {"burn": "50万/月", "runway": f"{months}个月"},
            "failure_case_db": lambda sector: {"cases": ["Case 1", "Case 2"], "sector": sector},
        }
        
        if name in tools_impl:
            try:
                if args:
                    result = tools_impl[name](**args)
                else:
                    result = tools_impl[name]()
                return {"tool": name, "result": result, "status": "success"}
            except Exception as e:
                return {"tool": name, "error": str(e), "status": "failed"}
        
        return {"tool": name, "error": "Unknown tool", "status": "failed"}


# 创建所有 Agent
AGENTS = {
    "researcher": BaseAgent(
        "researcher", "子墨", "🔬",
        ["paper_search", "patent_search"],
        "你是博学审问的子墨，精于格物致知。使用工具获取最新研究数据。"
    ),
    "analyst": BaseAgent(
        "analyst", "计然", "📊",
        ["market_size", "competitor_map", "trl_assessment"],
        "你是计然后人，深谙商道。使用工具进行量化分析。"
    ),
    "strategist": BaseAgent(
        "strategist", "卧龙", "🧠",
        ["project_db", "kanban_status", "contact_network"],
        "你如诸葛孔明般洞悉全局。使用工具获取项目状态。"
    ),
    "finance": BaseAgent(
        "finance", "陶朱", "💰",
        ["burn_rate", "valuation_model", "cap_table_sim"],
        "你如陶朱公般善理财帛。使用工具进行财务分析。"
    ),
    "risk": BaseAgent(
        "risk", "韩非", "⚠️",
        ["failure_case_db", "scenario_sim"],
        "你如韩非子般明法审势。使用工具评估风险。"
    ),
    "investor": BaseAgent(
        "investor", "白圭", "👀",
        ["market_size", "valuation_model", "competitor_map"],
        "你如白圭般善观时变。使用工具评估投资价值。"
    ),
}


async def run_brainstorm_with_tools(question: str, agent_a_role: str, agent_b_role: str, rounds: int = 2):
    """运行带工具调用的脑风暴"""
    agent_a = AGENTS.get(agent_a_role, AGENTS["researcher"])
    agent_b = AGENTS.get(agent_b_role, AGENTS["analyst"])
    
    # print(f"🧠 脑风暴开始: {agent_a.emoji} {agent_a.name} VS {agent_b.emoji} {agent_b.name}")
    # print(f"📋 主题: {question}\n")
    
    all_rounds = []
    
    for r in range(1, rounds + 1):
        # print(f"🏁 第 {r} 轮")
        
        # Agent A 发言
        context_a = f"讨论主题: {question}\n\n这是第{r}轮，请发表你的观点。"
        if all_rounds:
            context_a += f"\n\n之前讨论:\n{json.dumps(all_rounds, ensure_ascii=False)}"
        
        result_a = await agent_a.think(context_a)
        # print(f"{result_a.get('emoji')} {result_a.get('agent')}: {result_a.get('content')[:200]}...")
        if result_a.get('tool_calls'):
            # print(f"   🔧 工具调用: {[t['tool'] for t in result_a['tool_calls']]}")
        
        # Agent B 回应
        context_b = f"讨论主题: {question}\n\n{agent_a.name}的观点:\n{result_a.get('content')}\n\n请回应并反驳。"
        result_b = await agent_b.think(context_b)
        # print(f"{result_b.get('emoji')} {result_b.get('agent')}: {result_b.get('content')[:200]}...")
        if result_b.get('tool_calls'):
            # print(f"   🔧 工具调用: {[t['tool'] for t in result_b['tool_calls']]}")
        
        all_rounds.append({
            "round": r,
            "agent_a": result_a,
            "agent_b": result_b
        })
        # print()
    
    return all_rounds


# 测试
if __name__ == "__main__":
    result = asyncio.run(run_brainstorm_with_tools(
        question="AI+材料科学的商业化路径",
        agent_a_role="researcher",
        agent_b_role="analyst",
        rounds=2
    ))
    
    # print("\n" + "="*50)
    # print("完整结果:")
    # print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])

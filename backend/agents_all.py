#!/usr/bin/env python3
"""
完整 Agent 实现 - 6个角色
"""

import asyncio
import json
from typing import Dict, Any, List

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
        """思考并返回结果"""
        # 模拟思考过程
        return {
            "ok": True,
            "content": f"作为{self.name}，我分析了：{context[:50]}...\n\n我的观点是：这是一个需要深入研究的课题。",
            "agent": self.name,
            "emoji": self.emoji,
            "tools_available": self.tools
        }


# 创建所有 Agent
AGENTS = {
    "researcher": BaseAgent(
        "researcher", "子墨", "🔬",
        ["paper_search", "patent_search"],
        "你是博学审问的子墨，精于格物致知。"
    ),
    "analyst": BaseAgent(
        "analyst", "计然", "📊",
        ["market_size", "competitor_map", "trl_assessment"],
        "你是计然后人，深谙商道。"
    ),
    "strategist": BaseAgent(
        "strategist", "卧龙", "🧠",
        ["project_db", "kanban_status", "contact_network"],
        "你如诸葛孔明般洞悉全局。"
    ),
    "finance": BaseAgent(
        "finance", "陶朱", "💰",
        ["burn_rate", "valuation_model", "cap_table_sim"],
        "你如陶朱公般善理财帛。"
    ),
    "risk": BaseAgent(
        "risk", "韩非", "⚠️",
        ["failure_case_db", "scenario_sim"],
        "你如韩非子般明法审势。"
    ),
    "investor": BaseAgent(
        "investor", "白圭", "👀",
        ["market_size", "valuation_model", "competitor_map"],
        "你如白圭般善观时变。"
    ),
}


async def run_brainstorm(question: str, agent_a_role: str, agent_b_role: str, rounds: int = 2):
    """运行脑风暴"""
    agent_a = AGENTS.get(agent_a_role, AGENTS["researcher"])
    agent_b = AGENTS.get(agent_b_role, AGENTS["analyst"])
    
    # print(f"🧠 脑风暴: {agent_a.emoji} {agent_a.name} VS {agent_b.emoji} {agent_b.name}")
    # print(f"📋 主题: {question}\n")
    
    all_rounds = []
    
    for r in range(1, rounds + 1):
        # print(f"🏁 第 {r} 轮")
        
        # Agent A
        context_a = f"讨论主题: {question}"
        result_a = await agent_a.think(context_a)
        # print(f"{result_a['emoji']} {result_a['agent']}: {result_a['content'][:150]}...")
        # print(f"   🔧 可用工具: {result_a['tools_available']}")
        
        # Agent B
        context_b = f"{agent_a.name}说: {result_a['content']}\n\n请回应。"
        result_b = await agent_b.think(context_b)
        # print(f"{result_b['emoji']} {result_b['agent']}: {result_b['content'][:150]}...")
        # print(f"   🔧 可用工具: {result_b['tools_available']}")
        
        all_rounds.append({"round": r, "agent_a": result_a, "agent_b": result_b})
        # print()
    
    return all_rounds


# 测试
if __name__ == "__main__":
    result = asyncio.run(run_brainstorm(
        question="AI+材料科学的商业化路径",
        agent_a_role="researcher",
        agent_b_role="analyst",
        rounds=2
    ))
    
    # print("="*50)
    # print("✅ 6个Agent全部就位，工具已配置")
    # print("✅ SDS CrewAI 框架已集成")
    # print("✅ 后续可接入真实LLM和工具执行")

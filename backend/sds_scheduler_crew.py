#!/usr/bin/env python3
"""
SDS CrewAI 集成 - 将自愈功能改造为多 Agent 协作
"""

import sys
sys.path.insert(0, '/opt/kanban-react/backend')

from sds_crew_framework import SDSCrew, DiagnosticAgent, AnalysisAgent, StrategyAgent
import asyncio
import json

class SDSScheduler:
    """SDS 调度器 - 使用 CrewAI 多 Agent"""
    
    def __init__(self):
        self.crew = SDSCrew()
        self.running = False
    
    async def run_self_healing_cycle(self):
        """运行一次自愈周期"""
        # print("🔄 SDS 自愈周期开始...")
        
        # 1. 诊断阶段 - 子墨
        # print("🔬 子墨诊断中...")
        diag_result = await self.crew.agents["diagnostic"].execute({
            "type": "scan",
            "check_items": ["failed_tasks", "code_health", "db_status"]
        })
        
        if not diag_result["ok"]:
            # print(f"⚠️ 诊断失败，已求助扮演者: {diag_result.get('guidance')}")
            return {"status": "failed", "stage": "diagnostic", "result": diag_result}
        
        # print(f"✅ 诊断完成: {diag_result['result']}")
        
        # 2. 分析阶段 - 计然
        # print("📊 计然分析中...")
        analysis_result = await self.crew.agents["analysis"].execute({
            "diagnosis": diag_result["result"],
            "assess": "impact_priority"
        })
        
        if not analysis_result["ok"]:
            # print(f"⚠️ 分析失败，已求助扮演者: {analysis_result.get('guidance')}")
            return {"status": "failed", "stage": "analysis", "result": analysis_result}
        
        # print(f"✅ 分析完成: {analysis_result['result']}")
        
        # 3. 策略阶段 - 卧龙
        # print("🧠 卧龙制定策略...")
        strategy_result = await self.crew.agents["strategy"].execute({
            "analysis": analysis_result["result"],
            "action": "generate_fix_plan"
        })
        
        if not strategy_result["ok"]:
            # print(f"⚠️ 策略失败，已求助扮演者: {strategy_result.get('guidance')}")
            return {"status": "failed", "stage": "strategy", "result": strategy_result}
        
        # print(f"✅ 策略完成: {strategy_result['result']}")
        
        # 4. 执行修复（简化版）
        # print("🔧 执行修复...")
        fix_result = await self.execute_fix(strategy_result["result"])
        
        # print("✅ SDS 自愈周期完成")
        return {
            "status": "success",
            "diagnostic": diag_result["result"],
            "analysis": analysis_result["result"],
            "strategy": strategy_result["result"],
            "fix": fix_result
        }
    
    async def execute_fix(self, strategy):
        """执行修复策略"""
        # 这里集成现有的修复逻辑
        return {"executed": True, "strategy": strategy}
    
    async def run_continuous(self, interval=1800):
        """持续运行，每30分钟一次"""
        self.running = True
        while self.running:
            try:
                result = await self.run_self_healing_cycle()
                # print(f"📊 周期结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
            except Exception as e:
                # print(f"❌ 周期异常: {e}")
            
            if self.running:
                await asyncio.sleep(interval)
    
    def stop(self):
        """停止调度器"""
        self.running = False


# 测试运行
if __name__ == "__main__":
    scheduler = SDSScheduler()
    
    # 运行一次测试
    result = asyncio.run(scheduler.run_self_healing_cycle())
    # print("\n" + "="*50)
    # print("最终报告:")
    # print(json.dumps(result, ensure_ascii=False, indent=2))

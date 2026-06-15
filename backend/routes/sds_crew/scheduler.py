#!/usr/bin/env python3
"""
SDS CrewAI 调度器 - 周期性自愈调度

配置为每30分钟执行一次完整自愈周期（与现有 cron 并行工作）
可通过 systemd 管理或作为现有调度的补充
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional

# 确保能找到 routes 包
sys.path.insert(0, "/opt/kanban-react/backend")

from .framework import SDSCrew

logger = logging.getLogger(__name__)


class SDSScheduler:
    """
    SDS 调度器 - 使用 CrewAI 多 Agent 编排自愈流程
    
    与现有调度关系：
      - 现有 cron: ~/opt/sds1/crews/crew_dispatcher.run_all() (每30分钟)
      - 本调度器: 作为补充，提供更完善的多 Agent 流程（诊断→分析→策略→执行→报告）
      - `execute_fix` 直接调用真实 SDS 脚本（非 mock）
      - `ask_actor` 调用 actor_api 聊天端点
    """
    
    def __init__(self):
        self.crew = SDSCrew()
        self.running = False
        self.last_result = None
        self.cycle_count = 0
    
    async def run_self_healing_cycle(self) -> dict:
        """
        运行一次完整自愈周期
        
        返回详细结果报告
        """
        self.cycle_count += 1
        logger.info(f"🔄 [SDS-Crew] 第{self.cycle_count}次自愈周期开始")
        
        start = datetime.now()
        result = await self.crew.run_self_healing()
        elapsed = (datetime.now() - start).total_seconds()
        
        self.last_result = result
        
        # 提取概要
        summary = {
            "cycle": self.cycle_count,
            "elapsed_seconds": round(elapsed, 1),
            "timestamp": datetime.now().isoformat(),
            "stages": {},
        }
        
        for stage, stage_result in result.items():
            summary["stages"][stage] = {
                "ok": stage_result.get("ok", False),
                "agent": stage_result.get("agent", "unknown"),
            }
        
        # 如果报告阶段有内容，包含完整报告
        if "report" in result and result["report"].get("ok"):
            report_result = result["report"].get("result", {})
            summary["report_preview"] = report_result.get("report", "")[:500]
        
        logger.info(f"✅ [SDS-Crew] 周期完成: {elapsed:.1f}s, "
                     f"{sum(1 for s in summary['stages'].values() if s['ok'])}/"
                     f"{len(summary['stages'])} 阶段成功")
        
        return summary
    
    async def run_continuous(self, interval: int = 1800):
        """
        持续运行，每 interval 秒执行一次
        
        Args:
            interval: 间隔秒数 (默认 1800 = 30分钟)
        """
        self.running = True
        logger.info(f"🚀 [SDS-Crew] 持续调度启动，间隔={interval}s")
        
        while self.running:
            try:
                summary = await self.run_self_healing_cycle()
                print(json.dumps(summary, ensure_ascii=False, indent=2))
            except Exception as e:
                logger.error(f"❌ [SDS-Crew] 周期异常: {e}")
            
            # 等待期间检查停止标志
            for _ in range(interval):
                if not self.running:
                    break
                await asyncio.sleep(1)
        
        logger.info("🛑 [SDS-Crew] 调度器已停止")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        logger.info("🛑 [SDS-Crew] 停止请求已发送")
    
    def get_status(self) -> dict:
        """获取调度器状态"""
        return {
            "running": self.running,
            "cycle_count": self.cycle_count,
            "last_run": self.last_result,
            "timestamp": datetime.now().isoformat(),
        }


# ─── 快速测试 ───────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    
    scheduler = SDSScheduler()
    
    # 运行一次测试
    summary = asyncio.run(scheduler.run_self_healing_cycle())
    print("\n" + "="*60)
    print("📊 SDS CrewAI 自愈周期测试结果:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

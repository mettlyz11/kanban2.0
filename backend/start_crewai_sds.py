#!/usr/bin/env python3
"""
SDS CrewAI 启动入口 - 作为现有调度的补充

使用方法：
  # 运行一次自愈周期
  python3 start_crewai_sds.py
  
  # 持续运行（每30分钟一次）
  python3 start_crewai_sds.py --continuous

  # 持续运行并指定间隔（秒）
  python3 start_crewai_sds.py --continuous --interval 900

  # 运行特定阶段
  python3 start_crewai_sds.py --stage diagnostic

集成说明：
  - execute_fix → 调用真实 SDS 脚本（push_actor_filter, llm_auditor, actor_db_fix）
  - ask_actor → 调用 http://127.0.0.1:18791/v1/chat/completions
  - 无硬编码 mock 数据，全部基于真实数据库和系统调用
"""

import os
import sys
import json
import asyncio
import logging
import argparse

# 添加 backend 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from routes.sds_crew.scheduler import SDSScheduler
from routes.sds_crew.framework import SDSCrew

logger = logging.getLogger(__name__)


def run_once():
    """运行一次自愈周期"""
    scheduler = SDSScheduler()
    summary = asyncio.run(scheduler.run_self_healing_cycle())
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def run_continuous(interval: int = 1800):
    """持续运行"""
    scheduler = SDSScheduler()
    try:
        asyncio.run(scheduler.run_continuous(interval=interval))
    except KeyboardInterrupt:
        scheduler.stop()
        print("\n🛑 调度器已停止")


def run_stage(stage: str):
    """运行单阶段测试"""
    crew = SDSCrew()
    if stage not in crew.agents:
        print(f"❌ 未知阶段: {stage}")
        print(f"可用阶段: {list(crew.agents.keys())}")
        return
    
    result = asyncio.run(crew.agents[stage].execute({"type": "test"}))
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="SDS CrewAI 调度器 - 多 Agent 自愈系统"
    )
    parser.add_argument("--continuous", action="store_true",
                       help="持续运行（每30分钟）")
    parser.add_argument("--interval", type=int, default=1800,
                       help="执行间隔（秒，默认1800）")
    parser.add_argument("--stage", type=str, default=None,
                       help="只运行单个阶段 (diagnostic/analysis/strategy/executor/reporter/supervisor)")
    parser.add_argument("--status", action="store_true",
                       help="查看调度器状态")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    
    if args.status:
        scheduler = SDSScheduler()
        print(json.dumps(scheduler.get_status(), ensure_ascii=False, indent=2))
    elif args.stage:
        run_stage(args.stage)
    elif args.continuous:
        run_continuous(interval=args.interval)
    else:
        run_once()


if __name__ == "__main__":
    main()

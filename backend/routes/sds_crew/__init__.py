"""
SDS CrewAI 框架包
自我驱动系统 (Self-Driven System) 多 Agent 协作框架

集成现有三个守护脚本：
  - push_actor_filter: 失败任务修复
  - llm_auditor: 代码健康扫描
  - actor_db_fix: 数据库修复

通过 actor_api (SSH隧道→:18791) 向扮演者求助
"""

from .framework import SDSCrew, SDSAgent
from .agents import create_all_agents
from .scheduler import SDSScheduler

__version__ = "1.0.0"
__all__ = ["SDSCrew", "SDSAgent", "SDSScheduler", "create_all_agents"]

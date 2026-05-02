"""
Orchestrator - 总指挥层调度器
v5.0 多智能体协作框架核心组件
"""
import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from shared_memory import SharedMemory, MemoryType
from specialists import BaseSpecialist, Researcher, Developer, Documenter, QAAgent

class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class Task:
    id: str
    type: str
    description: str
    priority: int = 5  # 1-10，10最高
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None
    result: Optional[Any] = None
    created_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    timeout: float = 300  # 5分钟超时
    retry_count: int = 0
    max_retries: int = 3

class Orchestrator:
    def __init__(self):
        self.shared_memory = SharedMemory()
        self.agents: Dict[str, BaseSpecialist] = {}
        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []
        self.failed_tasks: List[Task] = []
        
        # 注册默认代理
        self._register_default_agents()
        
    def _register_default_agents(self):
        """注册默认专业代理"""
        self.register_agent(Researcher("researcher_1", self.shared_memory))
        self.register_agent(Developer("developer_1", self.shared_memory))
        self.register_agent(Documenter("documenter_1", self.shared_memory))
        self.register_agent(QAAgent("qa_1", self.shared_memory))
        
    def register_agent(self, agent: BaseSpecialist):
        """注册代理到调度器"""
        self.agents[agent.agent_id] = agent
        # 注册信息写入共享记忆
        self.shared_memory.add(
            content={"role": agent.role, "capabilities": "registered"},
            mem_type=MemoryType.CONTEXT,
            source="orchestrator"
        )
        
    def decompose_task(self, complex_task: Dict[str, Any]) -> List[Task]:
        """复杂任务分解：将大任务拆分为多个子任务"""
        subtasks = []
        task_type = complex_task.get("type", "")
        description = complex_task.get("description", "")
        
        # 任务分解规则（生产环境可基于LLM动态分解）
        if "系统设计" in description or "升级" in description or "架构" in description:
            # 典型技术升级任务分解为：调研 -> 设计 -> 实现 -> 文档 -> 测试
            subtasks.append(Task(
                id=f"task_{int(time.time())}_1",
                type="research",
                description=f"调研{description}相关技术趋势和最佳实践",
                priority=8
            ))
            subtasks.append(Task(
                id=f"task_{int(time.time())}_2",
                type="develop",
                description=f"实现{description}的核心功能代码",
                priority=9
            ))
            subtasks.append(Task(
                id=f"task_{int(time.time())}_3",
                type="document",
                description=f"编写{description}的技术文档和升级方案",
                priority=7
            ))
            subtasks.append(Task(
                id=f"task_{int(time.time())}_4",
                type="qa",
                description=f"验证{description}的实现质量和安全性",
                priority=8
            ))
        else:
            # 默认分解：调研 -> 实现 -> 验证
            subtasks.append(Task(
                id=f"task_{int(time.time())}_1",
                type="research",
                description=f"调研{description}相关信息",
                priority=5
            ))
            subtasks.append(Task(
                id=f"task_{int(time.time())}_2",
                type="develop",
                description=f"实现{description}",
                priority=5
            ))
            subtasks.append(Task(
                id=f"task_{int(time.time())}_3",
                type="qa",
                description=f"验证{description}结果",
                priority=5
            ))
            
        return subtasks
    
    def assign_task(self, task: Task) -> Tuple[Optional[str], float]:
        """任务分配：基于能力匹配+负载均衡"""
        best_agent = None
        best_score = 0.0
        
        for agent_id, agent in self.agents.items():
            # 能力得分
            capability_score = agent.can_handle(task.type)
            
            # 负载得分：任务历史越少得分越高（负载均衡）
            load_score = 1.0 / (1 + len(agent.task_history))
            
            # 综合得分 = 能力得分 * 0.7 + 负载得分 * 0.3
            total_score = capability_score * 0.7 + load_score * 0.3
            
            if total_score > best_score and capability_score > 0.3:
                best_score = total_score
                best_agent = agent_id
                
        return best_agent, best_score
    
    async def execute_task(self, task: Task) -> Task:
        """执行单个任务"""
        agent_id, score = self.assign_task(task)
        
        if not agent_id:
            task.status = TaskStatus.FAILED
            task.result = {"error": "没有找到合适的代理处理该任务"}
            return task
            
        task.assigned_to = agent_id
        task.status = TaskStatus.ASSIGNED
        task.started_at = time.time()
        
        agent = self.agents[agent_id]
        
        try:
            # 超时控制
            result = await asyncio.wait_for(
                asyncio.to_thread(agent.execute, {
                    "type": task.type,
                    "description": task.description,
                    **task.__dict__
                }),
                timeout=task.timeout
            )
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            self.completed_tasks.append(task)
            
        except asyncio.TimeoutError:
            task.status = TaskStatus.TIMEOUT
            task.retry_count += 1
            if task.retry_count < task.max_retries:
                # 重试
                return await self.execute_task(task)
            else:
                task.result = {"error": "任务执行超时，已达最大重试次数"}
                self.failed_tasks.append(task)
                
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.retry_count += 1
            if task.retry_count < task.max_retries:
                return await self.execute_task(task)
            else:
                task.result = {"error": f"任务执行失败: {str(e)}"}
                self.failed_tasks.append(task)
                
        return task
    
    async def run_complex_task(self, complex_task: Dict[str, Any]) -> Dict[str, Any]:
        """执行复杂任务：分解 -> 并行执行 -> 结果聚合"""
        start_time = time.time()
        
        # 1. 任务分解
        subtasks = self.decompose_task(complex_task)
        print(f"[Orchestrator: 任务已分解为 {len(subtasks)} 个子任务")
        
        # 2. 写入共享记忆
        self.shared_memory.add(
            content={"original_task": complex_task, "subtasks": len(subtasks)},
            mem_type=MemoryType.CONTEXT,
            source="orchestrator"
        )
        
        # 3. 并行执行所有子任务
        tasks = [self.execute_task(subtask) for subtask in subtasks]
        results = await asyncio.gather(*tasks)
        
        # 4. 结果聚合
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r.status == TaskStatus.COMPLETED)
        
        final_result = {
            "status": "success" if success_count == len(results) else "partial_success",
            "original_task": complex_task,
            "subtasks_count": len(subtasks),
            "success_count": success_count,
            "failed_count": len(subtasks) - success_count,
            "total_duration": total_time,
            "subtask_results": [
                {
                    "task_id": t.id,
                    "type": t.type,
                    "status": t.status.value,
                    "assigned_to": t.assigned_to,
                    "duration": t.completed_at - t.started_at if t.completed_at > 0 else 0,
                    "result": t.result
                } for t in results
            ],
            "memory_stats": self.shared_memory.get_stats()
        }
        
        return final_result
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        total_tasks = len(self.completed_tasks) + len(self.failed_tasks)
        if total_tasks == 0:
            return {}
            
        success_rate = len(self.completed_tasks) / total_tasks * 100
        avg_duration = sum(
            t.completed_at - t.started_at 
            for t in self.completed_tasks
        ) / len(self.completed_tasks) if self.completed_tasks else 0
        total_tokens = sum(
            t.result.get("tokens_used", 0) 
            for t in self.completed_tasks 
            if t.result
        )
        
        return {
            "total_tasks_executed": total_tasks,
            "success_rate": round(success_rate, 2),
            "avg_task_duration": round(avg_duration, 2),
            "total_tokens_used": total_tokens,
            "avg_tokens_per_task": round(total_tokens / len(self.completed_tasks), 2) if self.completed_tasks else 0,
            "agent_utilization": {
                agent_id: len(agent.task_history)
                for agent_id, agent in self.agents.items()
            }
        }

# 示例运行
if __name__ == "__main__":
    async def main():
        orch = Orchestrator()
        
        # 测试复杂任务执行
        result = await orch.run_complex_task({
            "type": "架构升级",
            "description": "多智能体协作框架从v4.3升级到v5.0"
        })
        
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("\n性能指标:")
        print(json.dumps(orch.get_performance_metrics(), ensure_ascii=False, indent=2))
        
    asyncio.run(main())

#!/usr/bin/env python3
"""
OpenClaw ACP v2026 - Long Running Task Example
Date: 2026-04-25
Task: #1931

This example demonstrates:
1. Checkpoint-based durability for long-running tasks
2. Memory compaction for extended context windows
3. Subagent orchestration patterns (Fan-out/Fan-in)
4. Circuit breakers and guardrails
5. Progress tracking and resumability
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict, field

from agents import (
    Agent, Runner, SandboxAgent,
    function_tool, handoff,
    RunConfig, TaskEndEvent
)

# ============================================
# Section 1: Task State Management (Checkpoint)
# ============================================

@dataclass
class TaskProgress:
    """Track progress within a long-running task"""
    stage: str
    percent_complete: float
    message: str
    started_at: str
    updated_at: str
    
    def to_dict(self):
        return asdict(self)


@dataclass
class CheckpointData:
    """Data structure for task checkpoints"""
    checkpoint_id: str
    task_id: str
    step: int
    message_history_length: int
    tokens_used: int
    progress: TaskProgress
    completed_subtasks: List[str]
    failed_subtasks: List[str]
    current_subtask: Optional[str]
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self):
        return asdict(self)


class CheckpointManager:
    """
    Manages checkpoint creation, storage, and recovery
    for long-running tasks
    """
    
    def __init__(self, storage_dir: Path = None):
        self.storage_dir = storage_dir or Path("/var/openclaw/checkpoints")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints: Dict[str, List[CheckpointData]] = {}
    
    async def create_checkpoint(
        self,
        task_id: str,
        step: int,
        tokens_used: int,
        progress: TaskProgress,
        completed_subtasks: List[str],
        failed_subtasks: List[str],
        current_subtask: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> CheckpointData:
        """Create a new checkpoint"""
        checkpoint = CheckpointData(
            checkpoint_id=f"cp-{task_id}-{int(time.time())}",
            task_id=task_id,
            step=step,
            message_history_length=step * 10,  # Approximate
            tokens_used=tokens_used,
            progress=progress,
            completed_subtasks=completed_subtasks.copy(),
            failed_subtasks=failed_subtasks.copy(),
            current_subtask=current_subtask,
            created_at=datetime.utcnow().isoformat(),
            metadata=metadata or {}
        )
        
        if task_id not in self.checkpoints:
            self.checkpoints[task_id] = []
        self.checkpoints[task_id].append(checkpoint)
        
        # Persist to disk
        await self._persist_checkpoint(checkpoint)
        
        return checkpoint
    
    async def _persist_checkpoint(self, checkpoint: CheckpointData):
        """Persist checkpoint to durable storage"""
        checkpoint_file = self.storage_dir / f"{checkpoint.checkpoint_id}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint.to_dict(), f, indent=2)
    
    async def get_latest_checkpoint(self, task_id: str) -> Optional[CheckpointData]:
        """Get the most recent checkpoint for a task"""
        if task_id not in self.checkpoints or not self.checkpoints[task_id]:
            # Try to load from disk
            await self._load_checkpoints_from_disk(task_id)
        
        if task_id in self.checkpoints and self.checkpoints[task_id]:
            return self.checkpoints[task_id][-1]
        return None
    
    async def _load_checkpoints_from_disk(self, task_id: str):
        """Load checkpoints from disk for a task"""
        pattern = f"cp-{task_id}-*.json"
        checkpoints = []
        
        for cp_file in self.storage_dir.glob(pattern):
            try:
                with open(cp_file) as f:
                    data = json.load(f)
                    # Reconstruct CheckpointData from dict
                    progress_data = data.pop('progress')
                    progress = TaskProgress(**progress_data)
                    checkpoint = CheckpointData(progress=progress, **data)
                    checkpoints.append(checkpoint)
            except Exception:
                continue
        
        checkpoints.sort(key=lambda x: x.created_at)
        self.checkpoints[task_id] = checkpoints
    
    async def restore_from_checkpoint(
        self,
        checkpoint_id: str
    ) -> Optional[CheckpointData]:
        """Restore task state from a specific checkpoint"""
        # In real implementation:
        # 1. Load checkpoint data
        # 2. Reconstruct message history
        # 3. Restore tool output cache
        # 4. Re-initialize agent state
        
        # Return checkpoint data for the caller to handle
        checkpoint_file = self.storage_dir / f"{checkpoint_id}.json"
        if checkpoint_file.exists():
            with open(checkpoint_file) as f:
                data = json.load(f)
                progress = TaskProgress(**data.pop('progress'))
                return CheckpointData(progress=progress, **data)
        return None


# ============================================
# Section 2: Memory Compaction Strategies
# ============================================

class MemoryCompactor:
    """
    Implements memory compaction for long context windows
    Supports multiple compaction strategies
    """
    
    def __init__(self, threshold_tokens: int = 80000):
        self.threshold_tokens = threshold_tokens
        self.compaction_ratio = 0.1  # Target 10:1 compression
    
    def should_compact(self, token_count: int) -> bool:
        """Determine if compaction is needed"""
        return token_count >= self.threshold_tokens
    
    def compact_messages(
        self,
        messages: List[Dict[str, Any]],
        strategy: str = "hybrid"
    ) -> List[Dict[str, Any]]:
        """
        Compact message history using selected strategy
        
        Strategies:
        - summary: Generate AI summary of older messages
        - extractive: Keep only critical information
        - hybrid: Summary + key points (recommended)
        - sliding_window: Keep only recent N messages
        """
        if len(messages) < 20:  # Don't compact small histories
            return messages
        
        if strategy == "sliding_window":
            return self._sliding_window_compact(messages)
        elif strategy == "extractive":
            return self._extractive_compact(messages)
        elif strategy == "hybrid":
            return self._hybrid_compact(messages)
        else:
            return self._summary_compact(messages)
    
    def _sliding_window_compact(
        self,
        messages: List[Dict[str, Any]],
        keep_last: int = 50
    ) -> List[Dict[str, Any]]:
        """Simple sliding window - keep only recent messages"""
        kept = messages[-keep_last:]
        
        if len(messages) > keep_last:
            # Add a note about what was removed
            compaction_note = {
                "role": "system",
                "content": f"[Note: {len(messages) - keep_last} earlier messages were "
                          f"compacted to stay within context window. "
                          f"Key information from earlier messages has been preserved.]"
            }
            kept.insert(0, compaction_note)
        
        return kept
    
    def _extractive_compact(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract and keep only critical information"""
        critical_messages = []
        other_messages = []
        
        for msg in messages:
            # Identify critical message types
            content = str(msg.get("content", ""))
            is_critical = any(marker in content.lower() for marker in [
                "decision", "conclusion", "result", "error", "failure",
                "key insight", "important", "critical", "must", "requirement",
                "bug", "fix", "solution", "answer"
            ])
            
            if is_critical:
                critical_messages.append(msg)
            else:
                other_messages.append(msg)
        
        # Keep all critical + last N non-critical
        kept = critical_messages + other_messages[-30:]
        
        if len(kept) < len(messages):
            kept.insert(0, {
                "role": "system",
                "content": f"[Memory compaction: preserved {len(critical_messages)} "
                          f"critical messages and {len(other_messages[-30:])} recent messages]"
            })
        
        return kept
    
    def _hybrid_compact(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Hybrid: extract critical points + generate summary"""
        # Split into old (compactable) and new (keep)
        split_point = len(messages) // 2
        old_messages = messages[:split_point]
        new_messages = messages[split_point:]
        
        # Extract critical from old
        old_critical = [
            m for m in old_messages
            if any(marker in str(m.get("content", "")).lower() for marker in [
                "decision", "conclusion", "result", "key insight", "requirement"
            ])
        ]
        
        # Generate summary of old messages (in real impl, use LLM)
        summary_point = {
            "role": "system",
            "content": f"[Context summary from earlier conversation: "
                      f"This task has been running for multiple steps. "
                      f"Progress: intermediate results have been obtained. "
                      f"{len(old_critical)} key decision points preserved. "
                      f"Continue the task from current state.]"
        }
        
        return [summary_point] + old_critical[-10:] + new_messages
    
    def _summary_compact(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate AI summary of older messages"""
        # In real implementation:
        # 1. Send older messages to a lightweight LLM
        # 2. Generate a concise summary
        # 3. Replace old messages with the summary
        # 4. Keep very recent messages intact
        
        split_point = max(10, len(messages) - 30)
        old_messages = messages[:split_point]
        recent_messages = messages[split_point:]
        
        # Placeholder: would generate actual summary
        summary = {
            "role": "system",
            "content": f"[Compressed context: {len(old_messages)} messages summarized. "
                      f"Task is progressing normally. Key decisions and findings "
                      f"have been integrated into the current context.]"
        }
        
        return [summary] + recent_messages


# ============================================
# Section 3: Subagent Orchestration
# ============================================

@dataclass
class Subtask:
    """Definition of a subtask to be executed"""
    subtask_id: str
    description: str
    agent_type: str
    input_data: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)
    timeout_seconds: int = 1800


class SubagentOrchestrator:
    """
    Implements Fan-out/Fan-in and other orchestration patterns
    Manages subtask distribution, dependencies, and aggregation
    """
    
    def __init__(self, max_parallel: int = 10):
        self.max_parallel = max_parallel
        self.subtask_results: Dict[str, Any] = {}
        self.subtask_status: Dict[str, str] = {}  # pending/running/complete/failed
    
    async def run_fan_out_fan_in(
        self,
        main_task_id: str,
        subtasks: List[Subtask],
        result_aggregator: Callable[[List[Any]], Any]
    ) -> Dict[str, Any]:
        """
        Execute Fan-out/Fan-in pattern:
        1. Fan out: Execute independent subtasks in parallel
        2. Fan in: Aggregate results from all subtasks
        """
        # print(f"Starting Fan-out/Fan-in for task {main_task_id}")
        # print(f"Subtasks: {len(subtasks)}, Max parallel: {self.max_parallel}")
        
        # Group by dependencies
        pending = subtasks.copy()
        running: List[Subtask] = []
        completed: List[Subtask] = []
        
        while pending or running:
            # Check completed subtasks
            completed_batch = [t for t in running if self.subtask_status.get(t.subtask_id) == "complete"]
            for t in completed_batch:
                running.remove(t)
                completed.append(t)
                # print(f"  ✓ Completed: {t.subtask_id}")
            
            # Check failed subtasks
            failed_batch = [t for t in running if self.subtask_status.get(t.subtask_id) == "failed"]
            for t in failed_batch:
                running.remove(t)
                # print(f"  ✗ Failed: {t.subtask_id}")
            
            # Start new subtasks that have dependencies met
            ready_to_start = [
                t for t in pending
                if all(dep in self.subtask_results for dep in t.depends_on)
            ]
            
            available_slots = self.max_parallel - len(running)
            to_start = ready_to_start[:available_slots]
            
            for subtask in to_start:
                pending.remove(subtask)
                running.append(subtask)
                self.subtask_status[subtask.subtask_id] = "running"
                
                # Actually run the subtask
                asyncio.create_task(self._run_subtask(subtask))
                # print(f"  → Started: {subtask.subtask_id}")
            
            await asyncio.sleep(1)
        
        # Fan in: aggregate results
        all_results = [
            self.subtask_results[st.subtask_id]
            for st in subtasks
            if st.subtask_id in self.subtask_results
        ]
        
        aggregated_result = await result_aggregator(all_results)
        
        return {
            "main_task_id": main_task_id,
            "subtasks_completed": len(completed),
            "subtasks_failed": len(subtasks) - len(completed),
            "aggregated_result": aggregated_result
        }
    
    async def _run_subtask(self, subtask: Subtask):
        """Execute a single subtask in its own sandbox"""
        try:
            # Simulate work
            await asyncio.sleep(min(5, subtask.timeout_seconds / 100))
            
            # In real implementation:
            # 1. Create sandbox
            # 2. Deploy appropriate agent type
            # 3. Execute subtask
            # 4. Collect result
            # 5. Destroy sandbox
            
            result = {
                "subtask_id": subtask.subtask_id,
                "status": "success",
                "result": f"Result for {subtask.description}",
                "output_files": [],
                "tokens_used": 1000
            }
            
            self.subtask_results[subtask.subtask_id] = result
            self.subtask_status[subtask.subtask_id] = "complete"
            
        except Exception as e:
            self.subtask_status[subtask.subtask_id] = "failed"
            self.subtask_results[subtask.subtask_id] = {
                "subtask_id": subtask.subtask_id,
                "status": "failed",
                "error": str(e)
            }


# ============================================
# Section 4: Circuit Breakers and Guardrails
# ============================================

class CircuitBreaker:
    """
    Implements circuit breaker pattern for long-running tasks
    Prevents infinite loops, excessive resource consumption, and errors
    """
    
    def __init__(self):
        self.error_count = 0
        self.consecutive_errors = 0
        self.tokens_used = 0
        self.step_count = 0
        self.last_actions: List[str] = []
        self.tripped = False
        self.trip_reason = None
    
    def record_action(self, action: str):
        """Record an action for loop detection"""
        self.last_actions.append(action)
        if len(self.last_actions) > 20:
            self.last_actions.pop(0)
        self.step_count += 1
    
    def record_error(self, error: str):
        """Record an error occurrence"""
        self.error_count += 1
        self.consecutive_errors += 1
    
    def record_success(self):
        """Record successful step - reset consecutive error counter"""
        self.consecutive_errors = 0
    
    def record_tokens(self, tokens: int):
        """Record token usage"""
        self.tokens_used += tokens
    
    def check_limits(self) -> tuple[bool, Optional[str]]:
        """
        Check if circuit breaker should trip
        Returns (should_trip, reason)
        """
        # 1. Consecutive errors threshold
        if self.consecutive_errors >= 5:
            return True, f"Too many consecutive errors ({self.consecutive_errors})"
        
        # 2. Total errors threshold
        if self.error_count >= 20:
            return True, f"Too many total errors ({self.error_count})"
        
        # 3. Loop detection
        if self._detect_loop():
            return True, "Detected possible infinite loop pattern"
        
        # 4. Step count limit (prevent infinite steps)
        if self.step_count >= 1000:
            return True, f"Maximum steps exceeded ({self.step_count})"
        
        return False, None
    
    def _detect_loop(self, similarity_threshold: float = 0.8) -> bool:
        """Detect repetitive action patterns indicating a loop"""
        if len(self.last_actions) < 10:
            return False
        
        # Check for repeating sequences
        recent = self.last_actions[-10:]
        
        # Simple repetition detection
        for window_size in range(2, 6):
            for i in range(len(recent) - window_size * 2 + 1):
                seq1 = recent[i:i + window_size]
                seq2 = recent[i + window_size:i + window_size * 2]
                
                # Calculate similarity
                matches = sum(1 for a, b in zip(seq1, seq2) if a == b)
                similarity = matches / window_size if window_size > 0 else 0
                
                if similarity >= similarity_threshold:
                    return True
        
        return False
    
    def trip(self, reason: str):
        """Manually trip the circuit breaker"""
        self.tripped = True
        self.trip_reason = reason
    
    def reset(self):
        """Reset circuit breaker for recovery"""
        self.tripped = False
        self.trip_reason = None
        self.consecutive_errors = 0
        self.last_actions = []


# ============================================
# Section 5: Long Running Task Controller
# ============================================

class LongRunningTaskController:
    """
    Main controller for long-running tasks
    Integrates checkpointing, memory compaction, and guardrails
    """
    
    def __init__(
        self,
        task_id: str,
        description: str,
        checkpoint_manager: CheckpointManager = None,
        memory_compactor: MemoryCompactor = None,
        circuit_breaker: CircuitBreaker = None
    ):
        self.task_id = task_id
        self.description = description
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()
        self.memory_compactor = memory_compactor or MemoryCompactor()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        
        self.start_time = datetime.utcnow()
        self.current_step = 0
        self.tokens_used = 0
        self.completed_subtasks: List[str] = []
        self.failed_subtasks: List[str] = []
        self.messages: List[Dict[str, Any]] = []
        
        self.progress = TaskProgress(
            stage="initializing",
            percent_complete=0.0,
            message="Task starting...",
            started_at=self.start_time.isoformat(),
            updated_at=self.start_time.isoformat()
        )
    
    async def run(
        self,
        max_duration_hours: float = 24.0,
        auto_checkpoint: bool = True
    ) -> Dict[str, Any]:
        """Run the long-running task"""
        # print(f"\n{'='*60}")
        # print(f"Starting Long-Running Task: {self.task_id}")
        # print(f"Description: {self.description}")
        # print(f"Max duration: {max_duration_hours} hours")
        # print(f"{'='*60}\n")
        
        # Check for existing checkpoint
        existing_checkpoint = await self.checkpoint_manager.get_latest_checkpoint(self.task_id)
        if existing_checkpoint:
            # print(f"Found existing checkpoint: {existing_checkpoint.checkpoint_id}")
            # print(f"Resuming from step {existing_checkpoint.step}")
            await self._restore_from_checkpoint(existing_checkpoint)
        else:
            # print("No existing checkpoint found - starting fresh")
        
        # Main execution loop
        max_end_time = self.start_time + timedelta(hours=max_duration_hours)
        
        try:
            while datetime.utcnow() < max_end_time:
                # Check circuit breaker
                should_trip, reason = self.circuit_breaker.check_limits()
                if should_trip:
                    # print(f"\n⚠️  Circuit breaker tripped: {reason}")
                    self.progress.stage = "paused"
                    self.progress.message = f"Circuit breaker: {reason}"
                    break
                
                # Execute a step (in real implementation, this would call Agent)
                await self._execute_step()
                
                # Check if memory compaction is needed
                estimated_tokens = self.current_step * 1000  # Approximate
                if self.memory_compactor.should_compact(estimated_tokens):
                    # print(f"\n📦 Memory compaction triggered at ~{estimated_tokens} tokens")
                    self.messages = self.memory_compactor.compact_messages(self.messages)
                    # print(f"Compaction complete. Message count: {len(self.messages)}")
                
                # Create checkpoint if enabled
                if auto_checkpoint and self.current_step % 10 == 0:
                    await self._create_checkpoint()
                
                # Check if task is complete
                if self.progress.percent_complete >= 100.0:
                    # print(f"\n✅ Task completed successfully!")
                    break
                
                await asyncio.sleep(0.1)
            
            else:
                # Timeout reached
                # print(f"\n⏰ Task reached maximum duration ({max_duration_hours}h)")
                self.progress.stage = "timeout"
                self.progress.message = "Maximum duration reached"
        
        except Exception as e:
            # print(f"\n❌ Task error: {e}")
            self.progress.stage = "failed"
            self.progress.message = str(e)
            self.circuit_breaker.record_error(str(e))
            # Create final checkpoint before exit
            await self._create_checkpoint()
        
        # Final checkpoint
        await self._create_checkpoint()
        
        return self._get_result()
    
    async def _execute_step(self):
        """Execute one step of the task"""
        self.current_step += 1
        
        # Simulate work
        self.progress.stage = "executing"
        self.progress.percent_complete = min(
            100.0,
            self.progress.percent_complete + 2.0  # ~50 steps to complete
        )
        self.progress.message = f"Executing step {self.current_step}"
        self.progress.updated_at = datetime.utcnow().isoformat()
        
        # Record step for circuit breaker
        self.circuit_breaker.record_action(f"step_{self.current_step}")
        self.circuit_breaker.record_success()
        
        # Record token usage
        step_tokens = 1000 + (self.current_step * 100)  # Increasing token usage
        self.tokens_used += step_tokens
        self.circuit_breaker.record_tokens(step_tokens)
        
        # Add message to history
        self.messages.append({
            "role": "assistant",
            "content": f"Step {self.current_step}: Completed processing",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        if self.current_step % 5 == 0:
            # print(f"  Step {self.current_step}: {self.progress.percent_complete:.1f}% complete "
                  f"({self.tokens_used:,} tokens used)")
    
    async def _create_checkpoint(self):
        """Create checkpoint of current state"""
        checkpoint = await self.checkpoint_manager.create_checkpoint(
            task_id=self.task_id,
            step=self.current_step,
            tokens_used=self.tokens_used,
            progress=self.progress,
            completed_subtasks=self.completed_subtasks,
            failed_subtasks=self.failed_subtasks,
            current_subtask=None,
            metadata={
                "runtime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
                "message_count": len(self.messages)
            }
        )
        # print(f"  💾 Created checkpoint: {checkpoint.checkpoint_id}")
    
    async def _restore_from_checkpoint(self, checkpoint: CheckpointData):
        """Restore task state from checkpoint"""
        self.current_step = checkpoint.step
        self.tokens_used = checkpoint.tokens_used
        self.completed_subtasks = checkpoint.completed_subtasks
        self.failed_subtasks = checkpoint.failed_subtasks
        self.progress = checkpoint.progress
        
        # print(f"  Restored: step={checkpoint.step}, tokens={checkpoint.tokens_used:,}")
    
    def _get_result(self) -> Dict[str, Any]:
        """Get final task result"""
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "task_id": self.task_id,
            "description": self.description,
            "status": self.progress.stage,
            "success": self.progress.percent_complete >= 100.0,
            "progress": self.progress.to_dict(),
            "total_steps": self.current_step,
            "total_tokens": self.tokens_used,
            "duration_seconds": duration,
            "checkpoints_created": len(self.checkpoint_manager.checkpoints.get(self.task_id, [])),
            "subtasks_completed": len(self.completed_subtasks),
            "subtasks_failed": len(self.failed_subtasks),
            "circuit_breaker_tripped": self.circuit_breaker.tripped,
            "circuit_breaker_reason": self.circuit_breaker.trip_reason
        }


# ============================================
# Section 6: Example Usage
# ============================================

async def example_long_running_task():
    """Example: Run a long-running task with all features"""
    # print("OpenClaw ACP v2026 - Long Running Task Demo")
    # print(f"Started at: {datetime.now().isoformat()}")
    # print()
    
    # Create task controller
    controller = LongRunningTaskController(
        task_id="ACP-LRT-DEMO-001",
        description="72-hour automated scientific experiment execution"
    )
    
    # Run task with 1-minute max duration for demo
    result = await controller.run(max_duration_hours=0.016)  # ~1 minute
    
    # print(f"\n{'='*60}")
    # print("Task Result Summary")
    # print(f"{'='*60}")
    # print(f"Task ID: {result['task_id']}")
    # print(f"Status: {result['status']}")
    # print(f"Success: {result['success']}")
    # print(f"Progress: {result['progress']['percent_complete']:.1f}%")
    # print(f"Total Steps: {result['total_steps']}")
    # print(f"Total Tokens: {result['total_tokens']:,}")
    # print(f"Duration: {result['duration_seconds']:.1f}s")
    # print(f"Checkpoints: {result['checkpoints_created']}")
    # print(f"Circuit Breaker Tripped: {result['circuit_breaker_tripped']}")


async def example_fan_out_fan_in():
    """Example: Fan-out/Fan-in orchestration pattern"""
    # print(f"\n{'='*60}")
    # print("Subagent Orchestration: Fan-out/Fan-in Pattern")
    # print(f"{'='*60}\n")
    
    orchestrator = SubagentOrchestrator(max_parallel=5)
    
    # Create 10 independent subtasks
    subtasks = [
        Subtask(
            subtask_id=f"experiment-{i:03d}",
            description=f"Run experimental condition {i}",
            agent_type="research_agent",
            input_data={"condition": i, "iterations": 100},
            timeout_seconds=600
        )
        for i in range(10)
    ]
    
    # Result aggregator
    async def aggregate_results(results: List[Any]) -> Dict[str, Any]:
        return {
            "total_subtasks": len(results),
            "summary": "All experiments completed successfully",
            "findings": f"Found interesting patterns across {len(results)} conditions"
        }
    
    result = await orchestrator.run_fan_out_fan_in(
        main_task_id="FANOUT-DEMO-001",
        subtasks=subtasks,
        result_aggregator=aggregate_results
    )
    
    # print(f"\nFan-out/Fan-in Complete:")
    # print(f"  Subtasks Completed: {result['subtasks_completed']}")
    # print(f"  Subtasks Failed: {result['subtasks_failed']}")
    # print(f"  Aggregated Result: {result['aggregated_result']['summary']}")


async def example_checkpoint_recovery():
    """Example: Checkpoint creation and recovery"""
    # print(f"\n{'='*60}")
    # print("Checkpoint and Recovery Demo")
    # print(f"{'='*60}\n")
    
    checkpoint_manager = CheckpointManager()
    
    # Simulate a task that creates checkpoints
    task_id = "RECOVERY-DEMO-001"
    progress = TaskProgress(
        stage="running",
        percent_complete=45.0,
        message="Processing experimental data...",
        started_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat()
    )
    
    # Create checkpoints
    cp1 = await checkpoint_manager.create_checkpoint(
        task_id=task_id,
        step=25,
        tokens_used=25000,
        progress=progress,
        completed_subtasks=["data-load", "data-clean"],
        failed_subtasks=[]
    )
    
    # print(f"Created checkpoint: {cp1.checkpoint_id}")
    # print(f"  Step: {cp1.step}, Tokens: {cp1.tokens_used}")
    # print(f"  Progress: {cp1.progress.percent_complete}%")
    # print(f"  Completed: {cp1.completed_subtasks}")
    
    # Later recovery
    # print(f"\nSimulating recovery after interruption...")
    recovered = await checkpoint_manager.get_latest_checkpoint(task_id)
    if recovered:
        # print(f"Recovered checkpoint: {recovered.checkpoint_id}")
        # print(f"Resuming from step {recovered.step} at {recovered.progress.percent_complete}%")


# ============================================
# Section 7: Main Execution
# ============================================

async def main():
    """Run all long running task examples"""
    # print("OpenClaw ACP v2026 - Long Running Task Examples")
    # print(f"Date: {datetime.now().isoformat()}")
    
    await example_checkpoint_recovery()
    await example_fan_out_fan_in()
    await example_long_running_task()
    
    # print(f"\n{'='*60}")
    # print("All examples completed successfully!")
    # print(f"{'='*60}")
    # print("\nKey Features Demonstrated:")
    # print("  ✓ Checkpoint-based durability and recovery")
    # print("  ✓ Memory compaction for extended context windows")
    # print("  ✓ Fan-out/Fan-in subagent orchestration")
    # print("  ✓ Circuit breakers and guardrails")
    # print("  ✓ Progress tracking and monitoring")
    # print("\nProduction Deployment:")
    # print("  - Checkpoints saved to replicated storage")
    # print("  - Memory compaction uses LLM-based summarization")
    # print("  - Subagents run in isolated sandboxes")
    # print("  - Metrics exported to Prometheus/Grafana")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
from __future__ import annotations
import json
import random
import statistics
import time
from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parent
proto_path = ROOT / 'openclaw_agentic_scheduler_prototype_2026-04-25.py'
spec = importlib.util.spec_from_file_location('agentic_proto', proto_path)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

TaskContext = mod.TaskContext
AgenticScheduler = mod.AgenticScheduler
TaskState = mod.TaskState


def run_baseline(tasks):
    success = 0
    durations = []
    errors = 0
    for t in tasks:
        started = time.perf_counter()
        desc_len = len(t.description)
        complex_task = desc_len > 300 or t.priority >= 7 or t.task_type in {'strategic', 'breakthrough'}
        ok = random.random() < (0.62 if complex_task else 0.86)
        durations.append(((0.18 if complex_task else 0.08) + desc_len / 8000.0) * 1000)
        success += int(ok)
        errors += int(not ok)
    return {
        'completion_rate': round(success / len(tasks), 3),
        'avg_time_ms': round(statistics.mean(durations), 2),
        'error_rate': round(errors / len(tasks), 3),
    }


def run_agentic(tasks):
    scheduler = AgenticScheduler()
    success = 0
    durations = []
    errors = 0
    for t in tasks:
        started = time.perf_counter()
        out = scheduler.run_task(t)
        durations.append((time.perf_counter() - started) * 1000 + out.execution_time_ms)
        ok = out.state == TaskState.COMPLETED
        success += int(ok)
        errors += int(not ok)
    return {
        'completion_rate': round(success / len(tasks), 3),
        'avg_time_ms': round(statistics.mean(durations), 2),
        'error_rate': round(errors / len(tasks), 3),
    }


def main():
    random.seed(1965)
    tasks = []
    for i in range(30):
        tasks.append(TaskContext(
            task_id=2000+i,
            title=f'Test Task {i}',
            description='研究 架构 设计 实现 测试 验证 ' * (12 if i % 2 == 0 else 4),
            priority=8 if i % 3 == 0 else 5,
            task_type='strategic' if i % 5 == 0 else 'general',
        ))
    baseline = run_baseline(tasks)
    tasks2 = []
    for i in range(30):
        tasks2.append(TaskContext(
            task_id=3000+i,
            title=f'Test Task {i}',
            description='研究 架构 设计 实现 测试 验证 ' * (12 if i % 2 == 0 else 4),
            priority=8 if i % 3 == 0 else 5,
            task_type='strategic' if i % 5 == 0 else 'general',
        ))
    agentic = run_agentic(tasks2)
    report = {
        'baseline': baseline,
        'agentic': agentic,
        'delta': {
            'completion_rate': round(agentic['completion_rate'] - baseline['completion_rate'], 3),
            'avg_time_ms': round(agentic['avg_time_ms'] - baseline['avg_time_ms'], 2),
            'error_rate': round(agentic['error_rate'] - baseline['error_rate'], 3),
        }
    }
    # print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()

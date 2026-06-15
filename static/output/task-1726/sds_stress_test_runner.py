#!/usr/bin/env python3
import json, sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/sds')
from subagent_scheduler import SubagentScheduler, ResultCollector

BASE = Path('/Users/mettlyz/.openclaw/workspace/output/task-1726')
BASE.mkdir(parents=True, exist_ok=True)

class TestScheduler(SubagentScheduler):
    def __init__(self, max_concurrent=5, running_count=0):
        super().__init__()
        self.max_concurrent = max_concurrent
        self._running_count = running_count
        self.retry_interval = 60
        self.queue_file = BASE / 'stress_queue.jsonl'
        self.state_file = BASE / 'stress_state.json'
        self.marked = []
        self.pending_fixture = []

    def connect(self):
        self.conn = object()
        return True

    def close(self):
        return True

    def get_running_tasks_count(self):
        return self._running_count

    def mark_task_in_progress(self, task_id: int) -> bool:
        self.marked.append(task_id)
        self._running_count += 1
        return True

    def get_pending_tasks(self, limit: int = 10):
        return self.pending_fixture[:limit]

class TestCollector(ResultCollector):
    def __init__(self):
        super().__init__()
        self.marked_verified = []
        self.marked_retry = []

    def connect(self):
        self.conn = object()
        return True

    def close(self):
        return True

    def mark_task_verified(self, task_id: int, issues=None) -> bool:
        self.marked_verified.append((task_id, issues or []))
        return True

    def mark_for_retry(self, task_id: int, issues):
        self.marked_retry.append((task_id, list(issues)))
        return True


def read_jsonl(path: Path):
    rows = []
    if not path.exists():
        return rows
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def run():
    report = {'generated_at': datetime.now().isoformat(), 'tests': [], 'summary': {}}
    for fp in [BASE / 'stress_queue.jsonl', BASE / 'stress_state.json']:
        if fp.exists():
            fp.unlink()

    sched = TestScheduler(max_concurrent=5, running_count=0)
    sched.connect()
    sched.pending_fixture = [
        {'id': i, 'title': f'concurrent-task-{i}', 'priority': 2, 'description': f'desc-{i}'}
        for i in range(1, 8)
    ]
    dispatched = sched.dispatch_tasks()
    queue_rows = read_jsonl(sched.queue_file)
    report['tests'].append({
        'name': 'concurrency_max_5',
        'dispatched': dispatched,
        'marked_count': len(sched.marked),
        'queue_rows': len(queue_rows),
        'task_ids': sched.marked,
        'pass': dispatched == 5 and len(queue_rows) == 5 and sched.marked == [1, 2, 3, 4, 5]
    })

    sched2 = TestScheduler(max_concurrent=5, running_count=0)
    sched2.connect()
    sched2.pending_fixture = [
        {'id': i, 'title': f'backlog-task-{i}', 'priority': 10 if i <= 102 else 1, 'description': 'x'}
        for i in range(100, 112)
    ]
    dispatched2 = sched2.dispatch_tasks()
    queue_rows2 = read_jsonl(sched2.queue_file)
    report['tests'].append({
        'name': 'backlog_12_tasks',
        'input_tasks': 12,
        'dispatched': dispatched2,
        'remaining_not_dispatched': 12 - dispatched2,
        'queue_rows_total_after_case': len(queue_rows2),
        'pass': dispatched2 == 5 and (12 - dispatched2) == 7
    })

    sched3 = TestScheduler(max_concurrent=5, running_count=5)
    sched3.connect()
    sched3.pending_fixture = [{'id': 999, 'title': 'should-not-run', 'priority': 1, 'description': 'x'}]
    dispatched3 = sched3.dispatch_tasks()
    report['tests'].append({'name': 'no_available_slot', 'dispatched': dispatched3, 'pass': dispatched3 == 0})

    sched4 = TestScheduler()
    sched4.connect()
    empty_prompt = sched4.build_subagent_command({'id': 2001, 'title': '', 'description': ''})
    huge_desc = 'A' * 50000
    huge_prompt = sched4.build_subagent_command({'id': 2002, 'title': 'huge', 'description': huge_desc})
    report['tests'].append({
        'name': 'boundary_prompt_building',
        'empty_prompt_len': len(empty_prompt),
        'huge_prompt_len': len(huge_prompt),
        'pass': len(empty_prompt) > 0 and len(huge_prompt) > 50000
    })

    collector = TestCollector()
    collector.connect()
    bad_task = {'id': 3001, 'task_summary': 'too short', 'execution_log': 'x' * 20, 'task_type': 'normal'}
    good_task = {'id': 3002, 'task_summary': '摘要' * 30, 'execution_log': '日志' * 150, 'task_type': 'normal'}
    v1 = collector.verify_task_completion(bad_task)
    v2 = collector.verify_task_completion(good_task)
    collector.mark_for_retry(3001, v1[1])
    collector.mark_task_verified(3002)
    report['tests'].append({
        'name': 'retry_validation_gate',
        'bad_valid': v1[0],
        'bad_issues': v1[1],
        'good_valid': v2[0],
        'retry_marked': collector.marked_retry,
        'verified_marked': collector.marked_verified,
        'pass': (not v1[0]) and len(v1[1]) >= 2 and v2[0]
    })

    report['tests'].append({
        'name': 'timeout_policy_gap',
        'observed': {
            'scheduler_retry_interval_sec': sched.retry_interval,
            'collector_has_timeout_kill': False,
            'scheduler_has_heartbeat_timeout_logic': False
        },
        'pass': False,
        'note': '当前 subagent_scheduler.py 未实现 >1小时任务终止逻辑，仅在其他报告中描述心跳超时策略。'
    })

    iso_a = TestScheduler(); iso_b = TestScheduler()
    iso_a.connect(); iso_b.connect()
    iso_a.pending_fixture = [{'id': 4001, 'title': 'A', 'priority': 1, 'description': 'A'}]
    iso_b.pending_fixture = [{'id': 5001, 'title': 'B', 'priority': 1, 'description': 'B'}]
    da = iso_a.dispatch_tasks(); db = iso_b.dispatch_tasks()
    rows = read_jsonl(BASE / 'stress_queue.jsonl')
    report['tests'].append({
        'name': 'resource_isolation_basic',
        'dispatch_a': da,
        'dispatch_b': db,
        'combined_queue_rows': len(rows),
        'last_two_ids': [rows[-2]['task_id'], rows[-1]['task_id']] if len(rows) >= 2 else [],
        'pass': da == 1 and db == 1 and rows[-2]['task_id'] == 4001 and rows[-1]['task_id'] == 5001
    })

    passed = sum(1 for t in report['tests'] if t['pass'])
    total = len(report['tests'])
    report['summary'] = {'passed': passed, 'total': total, 'failed_tests': [t['name'] for t in report['tests'] if not t['pass']]}

    out = BASE / 'sds_stress_test_results.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    run()

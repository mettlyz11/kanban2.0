#!/usr/bin/env python3
"""
Latency Monitor - 延迟监控模块
监控工具调用、子代理启动、模型响应等各维度延迟
输出到 ~/.openclaw/observability/metrics.db

看板任务: #1545
创建时间: 2026-04-20
"""

import sqlite3
import os
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional

DB_PATH = os.path.expanduser("~/.openclaw/observability/metrics.db")

# 告警阈值
THRESHOLDS = {
    "tool_call_p95_ms": 5000,
    "subagent_cold_start_ms": 15000,
    "subagent_hot_start_ms": 5000,
    "model_response_toks_per_sec": 20,
    "file_op_ms": 500,
    "network_request_ms": 10000,
}

def init_schema(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS latency_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            operation TEXT NOT NULL,
            duration_ms REAL NOT NULL,
            status TEXT DEFAULT 'success',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT,
            model TEXT,
            session_key TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_latency_category ON latency_records(category);
        CREATE INDEX IF NOT EXISTS idx_latency_operation ON latency_records(operation);
        CREATE INDEX IF NOT EXISTS idx_latency_timestamp ON latency_records(timestamp);
    """)
    conn.commit()

def record(category: str, operation: str, duration_ms: float, 
           status: str = "success", model: str = None, session_key: str = None, metadata: Dict = None):
    """记录一次延迟测量"""
    conn = sqlite3.connect(DB_PATH)
    init_schema(conn)
    conn.execute("""
        INSERT INTO latency_records (category, operation, duration_ms, status, model, session_key, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (category, operation, duration_ms, status, model, session_key, json.dumps(metadata) if metadata else None))
    conn.commit()
    conn.close()
    
    # 检查是否触发告警
    alert = check_threshold(category, duration_ms)
    return {"recorded": True, "alert": alert}

def check_threshold(category: str, duration_ms: float) -> Optional[str]:
    """检查是否超过告警阈值"""
    key = f"{category}_p95_ms"
    if key in THRESHOLDS and duration_ms > THRESHOLDS[key]:
        return f"⚠️ {category}延迟 {duration_ms:.0f}ms 超过阈值 {THRESHOLDS[key]}ms"
    return None

def get_stats(category: str = None, operation: str = None, hours: int = 24) -> Dict:
    """获取延迟统计"""
    conn = sqlite3.connect(DB_PATH)
    init_schema(conn)
    
    since = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    where = "WHERE timestamp >= ?"
    params = [since]
    
    if category:
        where += " AND category = ?"
        params.append(category)
    if operation:
        where += " AND operation = ?"
        params.append(operation)
    
    rows = conn.execute(f"SELECT duration_ms FROM latency_records {where} ORDER BY duration_ms", params).fetchall()
    conn.close()
    
    if not rows:
        return {"count": 0, "message": "No data available"}
    
    values = [r[0] for r in rows]
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    
    return {
        "count": n,
        "min": round(sorted_vals[0], 2),
        "max": round(sorted_vals[-1], 2),
        "avg": round(statistics.mean(values), 2),
        "median": round(statistics.median(values), 2),
        "p50": round(sorted_vals[n // 2], 2),
        "p95": round(sorted_vals[int(n * 0.95)], 2),
        "p99": round(sorted_vals[int(n * 0.99)], 2),
        "stdev": round(statistics.stdev(values), 2) if n > 1 else 0
    }

def get_all_category_stats(hours: int = 24) -> Dict:
    """获取所有类别的延迟统计"""
    conn = sqlite3.connect(DB_PATH)
    init_schema(conn)
    
    since = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    rows = conn.execute("""
        SELECT category, COUNT(*) as count, 
               AVG(duration_ms) as avg_ms,
               MIN(duration_ms) as min_ms,
               MAX(duration_ms) as max_ms
        FROM latency_records 
        WHERE timestamp >= ?
        GROUP BY category
        ORDER BY avg_ms DESC
    """, (since,)).fetchall()
    
    conn.close()
    
    return {r[0]: {"count": r[1], "avg_ms": round(r[2], 2), "min_ms": round(r[3], 2), "max_ms": round(r[4], 2)} for r in rows}

def report(hours: int = 24) -> str:
    """生成延迟报告"""
    stats = get_all_category_stats(hours)
    
    lines = [
        f"=== 延迟监控报告 (过去{hours}小时) ===",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "-" * 50
    ]
    
    for cat, s in stats.items():
        alert = ""
        threshold_key = f"{cat}_p95_ms"
        if threshold_key in THRESHOLDS and s["avg_ms"] > THRESHOLDS[threshold_key] * 0.5:
            alert = f" ⚠️ (阈值: {THRESHOLDS[threshold_key]}ms)"
        lines.append(f"  {cat:25s} | 调用: {s['count']:>5} | 平均: {s['avg_ms']:>8.1f}ms | 最小: {s['min_ms']:>6.1f}ms | 最大: {s['max_ms']:>8.1f}ms{alert}")
    
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    
    conn = sqlite3.connect(DB_PATH)
    init_schema(conn)
    
    if len(sys.argv) < 2:
        print("Usage: latency_monitor.py <init|record|stats|report>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "init":
        print(f"Schema initialized at {DB_PATH}")
    
    elif cmd == "record":
        cat = sys.argv[2] if len(sys.argv) > 2 else "tool_call"
        op = sys.argv[3] if len(sys.argv) > 3 else "test"
        dur = float(sys.argv[4]) if len(sys.argv) > 4 else 100
        result = record(cat, op, dur)
        print(json.dumps(result, ensure_ascii=False))
    
    elif cmd == "stats":
        cat = sys.argv[2] if len(sys.argv) > 2 else None
        hours = int(sys.argv[3]) if len(sys.argv) > 3 else 24
        data = get_stats(cat, hours=hours)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    
    elif cmd == "report":
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        print(report(hours))
    
    conn.close()

#!/usr/bin/env python3
"""
Trace Collector - MCP调用链路追踪
采集OpenClaw Gateway的tool call、subagent spawn、memory search等操作的完整链路
输出到 ~/.openclaw/observability/metrics.db

看板任务: #1545
创建时间: 2026-04-20
"""

import sqlite3
import os
import json
import uuid
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

DB_PATH = os.path.expanduser("~/.openclaw/observability/metrics.db")

def init_schema(conn: sqlite3.Connection):
    """初始化追踪相关表结构"""
    conn.executescript("""
        -- 调用链路主表
        CREATE TABLE IF NOT EXISTS traces (
            trace_id TEXT PRIMARY KEY,
            session_key TEXT,
            task_id INTEGER,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            duration_ms INTEGER,
            status TEXT DEFAULT 'running',
            root_span_id TEXT,
            model TEXT,
            total_tokens INTEGER DEFAULT 0,
            total_cost REAL DEFAULT 0.0
        );

        -- Span详情表
        CREATE TABLE IF NOT EXISTS spans (
            span_id TEXT PRIMARY KEY,
            trace_id TEXT,
            parent_span_id TEXT,
            span_name TEXT NOT NULL,
            span_type TEXT NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            duration_ms INTEGER,
            status TEXT DEFAULT 'running',
            input_size INTEGER DEFAULT 0,
            output_size INTEGER DEFAULT 0,
            error_message TEXT,
            metadata TEXT,
            FOREIGN KEY (trace_id) REFERENCES traces(trace_id)
        );

        -- 工具调用索引
        CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans(trace_id);
        CREATE INDEX IF NOT EXISTS idx_spans_type ON spans(span_type);
        CREATE INDEX IF NOT EXISTS idx_spans_duration ON spans(duration_ms);
        CREATE INDEX IF NOT EXISTS idx_traces_session ON traces(session_key);
        CREATE INDEX IF NOT EXISTS idx_traces_status ON traces(status);
    """)
    conn.commit()

def start_trace(session_key: str = None, task_id: int = None, model: str = None) -> str:
    """开始一个新的调用链路"""
    trace_id = str(uuid.uuid4())[:12]
    conn = sqlite3.connect(DB_PATH)
    init_schema(conn)
    conn.execute(
        "INSERT INTO traces (trace_id, session_key, task_id, model) VALUES (?, ?, ?, ?)",
        (trace_id, session_key, task_id, model)
    )
    conn.commit()
    conn.close()
    return trace_id

def start_span(trace_id: str, span_name: str, span_type: str, parent_span_id: str = None) -> str:
    """开始一个span"""
    span_id = f"{trace_id}_{span_name[:8]}_{int(time.time()*1000) % 100000}"
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO spans (span_id, trace_id, parent_span_id, span_name, span_type) VALUES (?, ?, ?, ?, ?)",
        (span_id, trace_id, parent_span_id, span_name, span_type)
    )
    conn.commit()
    conn.close()
    return span_id

def end_span(span_id: str, status: str = "success", error_message: str = None, metadata: Dict = None,
             input_size: int = 0, output_size: int = 0):
    """结束一个span"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        UPDATE spans SET 
            end_time = CURRENT_TIMESTAMP,
            duration_ms = CAST((julianday('now') - julianday(start_time)) * 86400000 AS INTEGER),
            status = ?,
            error_message = ?,
            metadata = ?,
            input_size = ?,
            output_size = ?
        WHERE span_id = ?
    """, (status, error_message, json.dumps(metadata) if metadata else None, input_size, output_size, span_id))
    conn.commit()
    conn.close()

def end_trace(trace_id: str, status: str = "success", total_tokens: int = 0, total_cost: float = 0.0):
    """结束一个调用链路"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        UPDATE traces SET 
            end_time = CURRENT_TIMESTAMP,
            duration_ms = CAST((julianday('now') - julianday(start_time)) * 86400000 AS INTEGER),
            status = ?,
            total_tokens = ?,
            total_cost = ?
        WHERE trace_id = ?
    """, (status, total_tokens, total_cost, trace_id))
    conn.commit()
    conn.close()

def get_trace(trace_id: str) -> Optional[Dict]:
    """获取完整调用链路"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    trace = conn.execute("SELECT * FROM traces WHERE trace_id = ?", (trace_id,)).fetchone()
    if not trace:
        conn.close()
        return None
    
    spans = conn.execute(
        "SELECT * FROM spans WHERE trace_id = ? ORDER BY start_time",
        (trace_id,)
    ).fetchall()
    conn.close()
    
    return {
        "trace": dict(trace),
        "spans": [dict(s) for s in spans]
    }

def format_trace_tree(trace_id: str) -> str:
    """格式化输出调用链路树"""
    data = get_trace(trace_id)
    if not data:
        return f"Trace {trace_id} not found"
    
    trace = data["trace"]
    spans = data["spans"]
    
    lines = [
        f"Trace: {trace_id}",
        f"Session: {trace['session_key'] or 'N/A'}",
        f"Model: {trace['model'] or 'N/A'}",
        f"Duration: {trace['duration_ms']}ms",
        f"Status: {trace['status']}",
        f"Tokens: {trace['total_tokens']}, Cost: ¥{trace['total_cost']:.4f}",
        f"Spans: {len(spans)}",
        "-" * 60
    ]
    
    span_map = {s["span_id"]: s for s in spans}
    root_spans = [s for s in spans if not s["parent_span_id"] or s["parent_span_id"] not in span_map]
    
    def render_span(span, indent=0):
        prefix = "  " * indent
        status_icon = "✅" if span["status"] == "success" else "❌" if span["status"] == "error" else "⏳"
        duration = f"{span['duration_ms']}ms" if span['duration_ms'] else "running"
        lines.append(f"{prefix}{status_icon} {span['span_name']} ({span['span_type']}) [{duration}]")
        children = [s for s in spans if s["parent_span_id"] == span["span_id"]]
        for child in children:
            render_span(child, indent + 1)
    
    for root in root_spans:
        render_span(root)
    
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: trace_collector.py <init|start|end|get|tree>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "init":
        conn = sqlite3.connect(DB_PATH)
        init_schema(conn)
        print(f"Schema initialized at {DB_PATH}")
        conn.close()
    
    elif cmd == "start":
        trace_id = start_trace(session_key=sys.argv[2] if len(sys.argv) > 2 else None)
        print(f"Trace started: {trace_id}")
    
    elif cmd == "tree":
        if len(sys.argv) < 3:
            print("Usage: trace_collector.py tree <trace_id>")
            sys.exit(1)
        print(format_trace_tree(sys.argv[2]))
    
    elif cmd == "get":
        if len(sys.argv) < 3:
            print("Usage: trace_collector.py get <trace_id>")
            sys.exit(1)
        data = get_trace(sys.argv[2])
        if data:
            print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

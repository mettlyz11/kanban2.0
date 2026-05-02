#!/usr/bin/env python3
"""
Cost Accounting - MCP成本核算模块
追踪各模型/任务的token消耗和成本，支持告警
输出到 ~/.openclaw/observability/metrics.db

看板任务: #1545
创建时间: 2026-04-20
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

DB_PATH = os.path.expanduser("~/.openclaw/observability/metrics.db")

# 模型价格表 (USD per 1M tokens)
MODEL_PRICES = {
    "qwen3.6-plus": {"input": 0.40, "output": 1.20},
    "qwen-max": {"input": 0.80, "output": 2.40},
    "kimi-k2.5": {"input": 0.50, "output": 1.50},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "claude-opus-4": {"input": 15.00, "output": 75.00},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "default": {"input": 1.00, "output": 3.00},
}

# 汇率
USD_TO_CNY = 7.25

# 告警阈值
DAILY_BUDGET_CNY = 50.0
TASK_BUDGET_CNY = 0.5

def init_schema(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT,
            session_key TEXT,
            task_id INTEGER,
            model TEXT NOT NULL,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0.0,
            cost_cny REAL DEFAULT 0.0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            category TEXT DEFAULT 'model_call'
        );

        CREATE INDEX IF NOT EXISTS idx_costs_model ON costs(model);
        CREATE INDEX IF NOT EXISTS idx_costs_date ON costs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_costs_task ON costs(task_id);
        CREATE INDEX IF NOT EXISTS idx_costs_session ON costs(session_key);

        CREATE VIEW IF NOT EXISTS daily_costs AS
        SELECT 
            date(timestamp) as date,
            model,
            category,
            SUM(input_tokens) as total_input_tokens,
            SUM(output_tokens) as total_output_tokens,
            SUM(cost_usd) as total_cost_usd,
            SUM(cost_cny) as total_cost_cny,
            COUNT(*) as total_calls
        FROM costs
        GROUP BY date(timestamp), model, category;
    """)
    conn.commit()

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> Dict:
    """计算单次调用的成本"""
    prices = MODEL_PRICES.get(model, MODEL_PRICES["default"])
    cost_usd = (input_tokens / 1_000_000) * prices["input"] + (output_tokens / 1_000_000) * prices["output"]
    cost_cny = cost_usd * USD_TO_CNY
    return {
        "cost_usd": round(cost_usd, 6),
        "cost_cny": round(cost_cny, 4)
    }

def record_cost(model: str, input_tokens: int, output_tokens: int, 
                trace_id: str = None, session_key: str = None, 
                task_id: int = None, category: str = "model_call"):
    """记录一次调用的成本"""
    conn = sqlite3.connect(DB_PATH)
    init_schema(conn)
    
    costs = calculate_cost(model, input_tokens, output_tokens)
    
    conn.execute("""
        INSERT INTO costs (trace_id, session_key, task_id, model, input_tokens, output_tokens, cost_usd, cost_cny, category)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (trace_id, session_key, task_id, model, input_tokens, output_tokens, costs["cost_usd"], costs["cost_cny"], category))
    conn.commit()
    
    # 检查日预算
    daily_total = get_daily_cost(conn)
    conn.close()
    
    alert = None
    if daily_total > DAILY_BUDGET_CNY:
        alert = f"⚠️ 日成本超标: ¥{daily_total:.2f} / ¥{DAILY_BUDGET_CNY:.2f}"
    
    return {**costs, "daily_total_cny": daily_total, "alert": alert}

def get_daily_cost(conn: sqlite3.Connection = None, date: str = None) -> float:
    """获取当日总成本"""
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close = True
    else:
        close = False
    
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    row = conn.execute(
        "SELECT COALESCE(SUM(cost_cny), 0) FROM costs WHERE date(timestamp) = ?",
        (date,)
    ).fetchone()
    
    if close:
        conn.close()
    
    return row[0]

def get_cost_breakdown(days: int = 7) -> List[Dict]:
    """获取成本分解（按模型+日期）"""
    conn = sqlite3.connect(DB_PATH)
    init_schema(conn)
    
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    rows = conn.execute("""
        SELECT date(timestamp) as date, model, 
               SUM(input_tokens) as input_tokens,
               SUM(output_tokens) as output_tokens,
               SUM(cost_cny) as cost_cny,
               COUNT(*) as calls
        FROM costs 
        WHERE timestamp >= ?
        GROUP BY date(timestamp), model
        ORDER BY date DESC, cost_cny DESC
    """, (since,)).fetchall()
    
    conn.close()
    return [{"date": r[0], "model": r[1], "input_tokens": r[2], "output_tokens": r[3], "cost_cny": r[4], "calls": r[5]} for r in rows]

def get_task_costs(task_id: int) -> Dict:
    """获取特定任务的累计成本"""
    conn = sqlite3.connect(DB_PATH)
    init_schema(conn)
    
    row = conn.execute("""
        SELECT SUM(input_tokens), SUM(output_tokens), SUM(cost_cny), COUNT(*)
        FROM costs WHERE task_id = ?
    """, (task_id,)).fetchone()
    
    conn.close()
    return {
        "task_id": task_id,
        "input_tokens": row[0] or 0,
        "output_tokens": row[1] or 0,
        "total_cost_cny": row[2] or 0.0,
        "total_calls": row[3] or 0
    }

if __name__ == "__main__":
    import sys
    
    conn = sqlite3.connect(DB_PATH)
    init_schema(conn)
    
    if len(sys.argv) < 2:
        print("Usage: cost_accounting.py <init|record|daily|breakdown|task>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "init":
        print(f"Schema initialized at {DB_PATH}")
    
    elif cmd == "record":
        model = sys.argv[2] if len(sys.argv) > 2 else "qwen3.6-plus"
        input_tok = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
        output_tok = int(sys.argv[4]) if len(sys.argv) > 4 else 500
        result = record_cost(model, input_tok, output_tok)
        print(f"Cost recorded: {json.dumps(result, ensure_ascii=False)}")
    
    elif cmd == "daily":
        total = get_daily_cost(conn)
        print(f"Today's cost: ¥{total:.4f} (budget: ¥{DAILY_BUDGET_CNY:.2f})")
    
    elif cmd == "breakdown":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        data = get_cost_breakdown(days)
        for row in data:
            print(f"  {row['date']} | {row['model']:20s} | ¥{row['cost_cny']:.4f} | {row['calls']} calls | {row['input_tokens'] + row['output_tokens']} tokens")
    
    elif cmd == "task":
        task_id = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        data = get_task_costs(task_id)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    
    conn.close()

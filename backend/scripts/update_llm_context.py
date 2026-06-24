#!/usr/bin/env python3
"""LLM 全局上下文自动更新脚本
只追加动态数据，不覆盖原始手动内容"""
import os, pymysql
from datetime import datetime

DB_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', 'rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com'),
    'port': 3306,
    'user': 'kanban',
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': 'kanban',
    'charset': 'utf8mb4',
}

def get_db():
    return pymysql.connect(**DB_CONFIG)

def build_context():
    """读取原始手动内容 + 追加数据库动态数据"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    conn = get_db()
    cur = conn.cursor()
    dynamic = []

    try:
        cur.execute("SELECT title, status FROM goals ORDER BY id LIMIT 7")
        goals = cur.fetchall()
        dynamic.append("## \u6218\u7565\u76ee\u6807")
        for g in goals:
            icon = '\u2705' if g[1]=='completed' else '\U0001f504' if g[1]=='active' else '\u23f3'
            dynamic.append(f"- {icon} {g[0][:60]}")
        dynamic.append("")

        cur.execute("""
            SELECT title, status, created_at FROM tasks
            WHERE task_type NOT LIKE "%crew%" AND title NOT LIKE "crew:%" AND created_at >= DATE_SUB(NOW(), INTERVAL 3 DAY)
            ORDER BY created_at DESC LIMIT 10
        """)
        recent = cur.fetchall()
        dynamic.append("## \u6700\u8fd1\u4efb\u52a1")
        for t in recent:
            icon = {'completed':'\u2705','in_progress':'\U0001f504','pending':'\u23f3','failed':'\u274c'}.get(t[1], '\u23f3')
            dynamic.append(f"- {icon} {t[0][:50]} ({str(t[2])[:10]})")
        dynamic.append("")

        cur.execute("SELECT name FROM projects WHERE status='active' LIMIT 5")
        projects = cur.fetchall()
        dynamic.append("## \u6d3b\u8dc3\u9879\u76ee")
        for p in projects:
            dynamic.append(f"- {p[0][:50]}")
        dynamic.append("")
    finally:
        cur.close()
        conn.close()

    dynamic.append("## \u7cfb\u7edf\u67b6\u6784")
    dynamic.append("### \u770b\u677f\u7cfb\u7edf")
    dynamic.append("- URL: https://kanbanyun.com")
    dynamic.append("- \u90e8\u7f72\u5728\u963f\u91cc\u4e91 ECS")
    dynamic.append("- \u7aef\u53e3\uff1a8085/8086/8087")
    dynamic.append("")
    dynamic.append("### \u955c\u50cf\u8fdb\u5316\u7cfb\u7edf")
    dynamic.append("- \u8def\u5f84\uff1a~/.openclaw/workspace/sds_evolution/")
    dynamic.append("- \u5f53\u524d\u72b6\u6001\uff1aSTD-EVAL \u7a33\u5b9a\u8fd0\u884c")
    dynamic.append("")

    # 读取原始手动内容
    ORIGIN_PATH = "/opt/kanban-react/frontend/public/llm_global_context.txt"
    if os.path.exists(ORIGIN_PATH):
        with open(ORIGIN_PATH) as f:
            base = f.read().strip()
    else:
        base = '# LLM \u5168\u5c40\u4e0a\u4e0b\u6587'

    return base + "\n\n---\n\n" + f"*LLM \u5168\u5c40\u4e0a\u4e0b\u6587\u52a8\u6001\u90e8\u5206 (\u66f4\u65b0\u4e8e {now})*" + "\n\n" + "\n".join(dynamic)

def update_files(content):
    paths = [
        "/opt/kanban-react/backend/dist/llm_global_context.txt",
        "/opt/kanban-react/dist/llm_global_context.txt",
    ]
    for p in paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w') as f:
            f.write(content)
        print(f"Done: {p}")

if __name__ == "__main__":
    print("Generating LLM global context...")
    content = build_context()
    update_files(content)
    print(f"Done ({len(content)} bytes)")

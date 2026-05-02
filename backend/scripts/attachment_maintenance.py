#!/usr/bin/env python3
import sys
sys.path.insert(0, "/opt/kanban-react/backend")

from db_config import get_connection
import os
from datetime import datetime

UPLOAD_DIR = "/opt/kanban-react/backend/uploads"
LOG_FILE = "/var/log/kanban_attachment_maintenance.log"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def check_attachments():
    db = get_connection()
    cursor = db.cursor()
    
    cursor.execute("SELECT id, filename, url, size FROM attachments WHERE url IS NOT NULL")
    attachments = cursor.fetchall()
    
    missing = 0
    valid = 0
    zero_size = 0
    
    for row in attachments:
        att_id = row["id"]
        filename = row["filename"]
        url = row["url"]
        size = row["size"]
        
        if size == 0:
            zero_size += 1
            continue
        
        relative = os.path.basename(url) if "/" in url else filename
        filepath = os.path.join(UPLOAD_DIR, relative)
        
        if os.path.exists(filepath):
            valid += 1
        else:
            missing += 1
    
    log(f"附件检查: 总数={len(attachments)}, 有效={valid}, 缺失={missing}, 大小为0={zero_size}")
    
    db.close()
    return {"total": len(attachments), "valid": valid, "missing": missing, "zero_size": zero_size}

def cleanup_orphan():
    db = get_connection()
    cursor = db.cursor()
    
    cursor.execute("""
        DELETE a FROM attachments a
        LEFT JOIN tasks t ON a.entity_id = t.id AND a.entity_type = "task"
        WHERE a.entity_type = "task" AND t.id IS NULL
    """)
    deleted = cursor.rowcount
    db.commit()
    
    log(f"清理孤儿附件: {deleted} 条")
    db.close()
    return deleted

def cleanup_zero_size():
    db = get_connection()
    cursor = db.cursor()
    
    cursor.execute("DELETE FROM attachments WHERE size = 0 OR size IS NULL")
    deleted = cursor.rowcount
    db.commit()
    
    log(f"清理大小为0: {deleted} 条")
    db.close()
    return deleted

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    
    log("=" * 60)
    log("附件维护开始")
    
    if args.check:
        result = check_attachments()
        print(f"\n结果: {result}")
    
    if args.cleanup:
        cleanup_orphan()
        cleanup_zero_size()
    
    log("附件维护完成")
    log("=" * 60)

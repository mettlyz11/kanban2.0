#!/usr/bin/env python3
import pymysql
from lib.db_connector import get_db_connection
import os

def insert_attachment():
    conn = get_db_connection()
    c = conn.cursor()
    
    # 插入社情民意信息文件
    filename = "关于推动AI赋能材料科学加速新质生产力发展的建议_社情民意信息_20260422.md"
    url = "output/task-1584/关于推动AI赋能材料科学加速新质生产力发展的建议_社情民意信息_20260422.md"
    size = 7983
    file_type = "md"
    
    c.execute('''INSERT INTO attachments 
        (entity_type, entity_id, filename, url, size, file_type) 
        VALUES (%s, %s, %s, %s, %s, %s)''',
        ('task', 1584, filename, url, size, file_type))
    
    # 插入执行日志文件
    log_filename = "execution_log.md"
    log_url = "output/task-1584/execution_log.md"
    log_size = os.path.getsize("/Users/mettlyz/.openclaw/workspace/output/task-1584/execution_log.md")
    c.execute('''INSERT INTO attachments 
        (entity_type, entity_id, filename, url, size, file_type) 
        VALUES (%s, %s, %s, %s, %s, %s)''',
        ('task', 1584, log_filename, log_url, log_size, 'md'))
    
    # 插入成果总结文件
    summary_filename = "result_summary.md"
    summary_url = "output/task-1584/result_summary.md"
    summary_size = os.path.getsize("/Users/mettlyz/.openclaw/workspace/output/task-1584/result_summary.md")
    c.execute('''INSERT INTO attachments 
        (entity_type, entity_id, filename, url, size, file_type) 
        VALUES (%s, %s, %s, %s, %s, %s)''',
        ('task', 1584, summary_filename, summary_url, summary_size, 'md'))
    
    # 插入任务摘要文件
    task_summary_filename = "task_summary.md"
    task_summary_url = "output/task-1584/task_summary.md"
    task_summary_size = os.path.getsize("/Users/mettlyz/.openclaw/workspace/output/task-1584/task_summary.md")
    c.execute('''INSERT INTO attachments 
        (entity_type, entity_id, filename, url, size, file_type) 
        VALUES (%s, %s, %s, %s, %s, %s)''',
        ('task', 1584, task_summary_filename, task_summary_url, task_summary_size, 'md'))
    
    conn.commit()
    conn.close()
    # print("附件插入完成：4个文件已插入数据库")

if __name__ == "__main__":
    insert_attachment()
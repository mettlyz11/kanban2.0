#!/usr/bin/env python3
"""
更新看板任务数据库
任务ID: 1544
"""

import pymysql
import sys

# 读取文件内容
def read_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        # print(f"读取文件失败: {e}")
        return ""

# 主函数
def main():
    # 读取文件内容
    execution_log_text = read_file('/Users/mettlyz/.openclaw/workspace/output/task-1544/execution_log_20260421.md')
    result_summary_text = read_file('/Users/mettlyz/.openclaw/workspace/output/task-1544/result_summary_20260421.md')
    task_summary_text = read_file('/Users/mettlyz/.openclaw/workspace/output/task-1544/task_summary_20260421.md')
    
    # 检查内容长度
    if len(execution_log_text) < 200:
        # print(f"错误: execution_log长度不足200字，实际长度: {len(execution_log_text)}")
        sys.exit(1)
    
    if len(result_summary_text) < 50:
        # print(f"错误: result_summary长度不足50字，实际长度: {len(result_summary_text)}")
        sys.exit(1)
    
    if len(task_summary_text) < 50:
        # print(f"错误: task_summary长度不足50字，实际长度: {len(task_summary_text)}")
        sys.exit(1)
    
    # print(f"文件长度检查通过:")
    # print(f"  execution_log: {len(execution_log_text)} 字")
    # print(f"  result_summary: {len(result_summary_text)} 字")
    # print(f"  task_summary: {len(task_summary_text)} 字")
    
    # 连接数据库
    try:
        conn = pymysql.connect(
            host='rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
            user='kanban',
            password='Irc210Irc210!',
            database='kanban',
            charset='utf8mb4'
        )
        
        c = conn.cursor()
        
        # 更新数据库
        sql = """
        UPDATE tasks 
        SET status = %s, 
            execution_log = %s, 
            result_summary = %s, 
            task_summary = %s, 
            updated_at = NOW() 
        WHERE id = %s
        """
        
        c.execute(sql, (
            'completed',
            execution_log_text,
            result_summary_text,
            task_summary_text,
            1544
        ))
        
        conn.commit()
        
        # 检查更新是否成功
        c.execute("SELECT status, updated_at FROM tasks WHERE id = %s", (1544,))
        result = c.fetchone()
        
        if result:
            # print(f"数据库更新成功!")
            # print(f"任务状态: {result[0]}")
            # print(f"更新时间: {result[1]}")
        else:
            # print("警告: 未找到任务ID 1544")
        
        conn.close()
        
    except pymysql.Error as e:
        # print(f"数据库连接或更新失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
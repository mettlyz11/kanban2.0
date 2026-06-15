#!/usr/bin/env python3
"""
更新看板任务数据库脚本
任务ID: 1277
"""

import pymysql
import os

# 读取文件内容
def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

# 主函数
def main():
    # 文件路径
    base_dir = "/Users/mettlyz/.openclaw/workspace/output/task-1277"
    execution_log_file = os.path.join(base_dir, "execution_log_20260422.md")
    result_summary_file = os.path.join(base_dir, "result_summary_20260422.md")
    task_summary_file = os.path.join(base_dir, "task_summary_20260422.md")
    
    # 读取文件内容
    execution_log_text = read_file(execution_log_file)
    result_summary_text = read_file(result_summary_file)
    task_summary_text = read_file(task_summary_file)
    
    # 检查内容长度
    # print(f"执行日志长度: {len(execution_log_text)} 字符")
    # print(f"结果摘要长度: {len(result_summary_text)} 字符")
    # print(f"任务摘要长度: {len(task_summary_text)} 字符")
    
    # 验证长度要求
    if len(execution_log_text) < 200:
        # print("❌ 错误: execution_log 长度不足200字")
        return False
    
    if len(result_summary_text) < 50:
        # print("❌ 错误: result_summary 长度不足50字")
        return False
    
    # print("✅ 内容长度验证通过")
    
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
        
        # 更新任务状态
        sql = '''
        UPDATE tasks 
        SET status = %s, 
            execution_log = %s, 
            result_summary = %s, 
            task_summary = %s, 
            updated_at = NOW() 
        WHERE id = %s
        '''
        
        c.execute(sql, (
            'completed',
            execution_log_text,
            result_summary_text,
            task_summary_text,
            1277
        ))
        
        conn.commit()
        # print(f"✅ 数据库更新成功，影响行数: {c.rowcount}")
        
        # 插入附件记录
        files = [
            {
                'filename': 'T3_4_国家级基金申请策略_2026-2027_20260422.md',
                'url': 'output/task-1277/T3_4_国家级基金申请策略_2026-2027_20260422.md',
                'size': os.path.getsize(os.path.join(base_dir, 'T3_4_国家级基金申请策略_2026-2027_20260422.md')),
                'file_type': 'md'
            },
            {
                'filename': 'execution_log_20260422.md',
                'url': 'output/task-1277/execution_log_20260422.md',
                'size': os.path.getsize(os.path.join(base_dir, 'execution_log_20260422.md')),
                'file_type': 'md'
            },
            {
                'filename': 'result_summary_20260422.md',
                'url': 'output/task-1277/result_summary_20260422.md',
                'size': os.path.getsize(os.path.join(base_dir, 'result_summary_20260422.md')),
                'file_type': 'md'
            },
            {
                'filename': 'task_summary_20260422.md',
                'url': 'output/task-1277/task_summary_20260422.md',
                'size': os.path.getsize(os.path.join(base_dir, 'task_summary_20260422.md')),
                'file_type': 'md'
            }
        ]
        
        for file_info in files:
            insert_sql = '''
            INSERT INTO attachments 
                (entity_type, entity_id, filename, url, size, file_type) 
            VALUES (%s, %s, %s, %s, %s, %s)
            '''
            
            c.execute(insert_sql, (
                'task',
                1277,
                file_info['filename'],
                file_info['url'],
                file_info['size'],
                file_info['file_type']
            ))
            # print(f"✅ 附件插入成功: {file_info['filename']}")
        
        conn.commit()
        conn.close()
        # print("✅ 所有数据库操作完成")
        return True
        
    except Exception as e:
        # print(f"❌ 数据库操作失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务#2120数据库更新脚本
更新任务状态为completed，插入execution_log、result_summary、task_summary
"""

import sys
import os

# 添加工作目录到路径
sys.path.insert(0, 'os.path.expanduser("~/.openclaw/workspace")')

try:
    from lib.db_connector import get_db_connection
    # print("✅ 成功导入数据库连接器")
except ImportError as e:
    # print(f"⚠️  导入数据库连接器失败: {e}")
    # print("尝试直接使用pymysql...")
    import pymysql

    def get_db_connection():
        # 从环境变量或.env文件读取密码
        env_path = '/Users/mettlyz/.openclaw/.env'
        password = ''
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if 'DB_PASSWORD' in line or 'MYSQL_PASSWORD' in line:
                        password = line.split('=')[1].strip().strip('"').strip("'")
                        break
        
        return pymysql.connect(
            host='rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
            user='kanban',
            password=password,
            database='kanban',
            charset='utf8mb4'
        )

def read_file_content(filepath):
    """读取文件内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        # print(f"读取文件失败 {filepath}: {e}")
        return ""

def main():
    # print("=" * 60)
    # print("开始更新任务#2120数据库...")
    # print("=" * 60)
    
    # 读取文件内容
    base_dir = 'os.path.expanduser("~/.openclaw/workspace")/output/task-2120'
    
    execution_log = read_file_content(f'{base_dir}/execution_log_20260426.md')
    result_summary = read_file_content(f'{base_dir}/result_summary_20260426.md')
    task_summary = read_file_content(f'{base_dir}/task_summary_20260426.md')
    
    # print(f"execution_log 长度: {len(execution_log)} 字符")
    # print(f"result_summary 长度: {len(result_summary)} 字符")
    # print(f"task_summary 长度: {len(task_summary)} 字符")
    
    # 验证长度要求
    if len(execution_log) < 200:
        # print("❌ execution_log 不足200字符！")
        return False
    if len(result_summary) < 50:
        # print("❌ result_summary 不足50字符！")
        return False
    if len(task_summary) < 50:
        # print("❌ task_summary 不足50字符！")
        return False
    
    # print("✅ 所有内容长度符合验收标准")
    
    # 更新数据库
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 更新任务状态
        update_sql = """
        UPDATE tasks 
        SET status = %s, 
            execution_log = %s, 
            result_summary = %s, 
            task_summary = %s, 
            updated_at = NOW()
        WHERE id = %s
        """
        
        cursor.execute(update_sql, ('completed', execution_log, result_summary, task_summary, 2120))
        conn.commit()
        
        # print(f"✅ 任务#2120状态已更新为completed")
        # print(f"✅ 执行SQL影响行数: {cursor.rowcount}")
        
        # 插入附件记录
        attachments = [
            ('task', 2120, 'AI半导体材料标的财报分析报告_2026Q2_20260426.md', 
             'output/task-2120/AI半导体材料标的财报分析报告_2026Q2_20260426.md', 15153, 'md'),
            ('task', 2120, 'AI半导体材料多因子评级矩阵_2026Q2_20260426.md', 
             'output/task-2120/AI半导体材料多因子评级矩阵_2026Q2_20260426.md', 7941, 'md'),
            ('task', 2120, 'AI半导体材料Q2持仓优化建议书_2026Q2_20260426.md', 
             'output/task-2120/AI半导体材料Q2持仓优化建议书_2026Q2_20260426.md', 7939, 'md'),
            ('task', 2120, 'AI半导体材料个股交易时机建议_2026Q2_20260426.md', 
             'output/task-2120/AI半导体材料个股交易时机建议_2026Q2_20260426.md', 10612, 'md'),
        ]
        
        insert_sql = """
        INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """
        
        for att in attachments:
            try:
                cursor.execute(insert_sql, att)
                # print(f"✅ 已插入附件: {att[2]}")
            except Exception as e:
                if "Duplicate entry" in str(e):
                    # print(f"⚠️  附件已存在: {att[2]}")
                else:
                    # print(f"❌ 插入附件失败: {att[2]}, 错误: {e}")
        
        conn.commit()
        
        # 验证更新结果
        cursor.execute("SELECT id, status, LENGTH(execution_log), LENGTH(result_summary), LENGTH(task_summary) FROM tasks WHERE id = 2120")
        result = cursor.fetchone()
        
        # print("\n" + "=" * 60)
        # print("数据库更新验证结果:")
        # print("=" * 60)
        # print(f"任务ID: {result[0]}")
        # print(f"任务状态: {result[1]}")
        # print(f"execution_log 长度: {result[2]} 字符")
        # print(f"result_summary 长度: {result[3]} 字符")
        # print(f"task_summary 长度: {result[4]} 字符")
        
        cursor.close()
        conn.close()
        
        # print("\n" + "=" * 60)
        # print("🎉 任务#2120数据库更新完成！所有验收标准已满足")
        # print("=" * 60)
        
        return True
        
    except Exception as e:
        # print(f"❌ 数据库操作失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

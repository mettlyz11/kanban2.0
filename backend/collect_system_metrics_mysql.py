#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
收集系统指标并写入MySQL RDS数据库
修复：原来只写入SQLite，现在需要同步写入MySQL供前端显示
"""

import mysql.connector
import psutil
import datetime
import os

# MySQL配置从环境变量读取
config = {
    'host': os.environ.get('MYSQL_HOST', 'rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com'),
    'port': int(os.environ.get('MYSQL_PORT', '3306')),
    'user': os.environ.get('MYSQL_USER', 'kanban'),
    'password': os.environ.get('MYSQL_PASSWORD', 'Irc210Irc210!'),
    'database': os.environ.get('MYSQL_DATABASE', 'kanban'),
    'charset': 'utf8mb4'
}

def collect_metrics():
    """收集系统指标并写入MySQL"""
    
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        # 收集指标
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 获取CPU核心数和运行进程数
        cpu_count = psutil.cpu_count()
        running_processes = len(list(psutil.process_iter()))
        
        # 转换单位为GB
        memory_used_gb = memory.used / (1024**3)
        memory_total_gb = memory.total / (1024**3)
        disk_percent = disk.percent
        print(f"✅ 收集成功:")
        print(f"   CPU: {cpu_percent:5.1f}% ({cpu_count} 核心)")
        print(f"   内存: {memory.percent:5.1f}% ({memory_used_gb:.1f}/{memory_total_gb:.1f} GB)")
        print(f"   磁盘: {disk_percent:5.1f}%")
        print(f"   运行进程: {running_processes}")
        
        # 插入数据库
        sql = """
            INSERT INTO system_metrics 
            (cpu_percent, memory_percent, memory_used_gb, memory_total_gb, 
             disk_percent, running_projects, pending_projects, completed_projects, failed_projects)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # 进程统计暂时放running_processes，timestamp列有默认值NOW()
        data = (
            cpu_percent,
            memory.percent,
            memory_used_gb,
            memory_total_gb,
            disk_percent,
            running_processes,
            0, 0, 0
        )
        
        cursor.execute(sql, data)
        conn.commit()
        
        print(f"✅ 已写入MySQL system_metrics 表")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 收集失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    collect_metrics()

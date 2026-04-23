#!/bin/bash
# 系统监控数据收集脚本
# 用途：手动触发或定时执行系统指标收集
# 频率：每 5 分钟执行一次

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================"
echo "系统指标收集 - $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================"

python3 << 'EOF'
import sqlite3
import time
import psutil
import datetime

DB_PATH = 'kanban_v5.db'

def collect_metrics():
    """收集系统指标并写入数据库"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 确保表存在
        c.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                cpu_percent REAL,
                memory_percent REAL,
                memory_used_gb REAL,
                memory_total_gb REAL,
                disk_percent REAL,
                disk_used_gb REAL,
                disk_total_gb REAL,
                load_avg_1m REAL,
                load_avg_5m REAL,
                load_avg_15m REAL,
                network_sent_mb REAL,
                network_recv_mb REAL
            )
        ''')
        
        # 收集指标
        timestamp = time.time()
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # macOS 可能没有网络统计
        try:
            net = psutil.net_io_counters()
            network_sent_mb = net.bytes_sent / (1024**2)
            network_recv_mb = net.bytes_recv / (1024**2)
        except:
            network_sent_mb = 0
            network_recv_mb = 0
        
        # macOS 可能没有 load avg
        try:
            load_avg = psutil.getloadavg()
            load_1m, load_5m, load_15m = load_avg
        except:
            load_1m, load_5m, load_15m = 0, 0, 0
        
        # 插入数据库
        c.execute('''
            INSERT INTO monitoring_system_metrics 
            (timestamp, cpu_percent, memory_percent, disk_percent,
             memory_used_gb, memory_total_gb, disk_used_gb, disk_total_gb,
             load_avg_1m, load_avg_5m, load_avg_15m,
             network_sent_mb, network_recv_mb)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp,
            cpu_percent,
            memory.percent,
            disk.percent,
            memory.used / (1024**3),
            memory.total / (1024**3),
            disk.used / (1024**3),
            disk.total / (1024**3),
            load_1m, load_5m, load_15m,
            network_sent_mb, network_recv_mb
        ))
        
        conn.commit()
        conn.close()
        
        # 输出结果
        now = datetime.datetime.fromtimestamp(timestamp)
        print(f"✅ [{now.strftime('%Y-%m-%d %H:%M:%S')}] 数据收集成功")
        print(f"   CPU: {cpu_percent:5.1f}% | 内存：{memory.percent:5.1f}% | 磁盘：{disk.percent:5.1f}%")
        
    except Exception as e:
        print(f"❌ 数据收集失败：{e}")
        raise

if __name__ == '__main__':
    collect_metrics()
EOF

echo "======================================"

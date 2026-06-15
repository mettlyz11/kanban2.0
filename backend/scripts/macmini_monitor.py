#!/usr/bin/env python3
"""
Mac mini 系统监控采集脚本
每5秒采集系统指标，推送到看板服务器
"""

import psutil
import requests
import time
import json
import os
import socket
from datetime import datetime

# ============================================
# 配置
# ============================================
SERVER_URL = "https://47.93.184.128/api/macmini/sync/push-monitor"
PUSH_INTERVAL = 5  # 秒
VERIFY_SSL = False  # 自签证书设为 False

# ============================================
# 采集函数
# ============================================
def collect_metrics():
    """采集系统指标"""
    
    # CPU
    cpu_percent = psutil.cpu_percent(interval=0.5)  # 0.5秒取样
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()
    
    # 内存
    mem = psutil.virtual_memory()
    
    # 磁盘
    disk = psutil.disk_usage('/')
    
    # 网络（累计值，需算差值得到速率）
    net = psutil.net_io_counters()
    
    # 进程数
    process_count = len(psutil.pids())
    
    # 运行时间
    uptime = time.time() - psutil.boot_time()
    
    # 电池（笔记本）
    battery = psutil.sensors_battery()
    
    return {
        'cpu': cpu_percent,
        'memory': mem.percent,
        'disk': disk.percent,
        'processes': process_count,
        'uptime': int(uptime),
        'network_sent_mb': net.bytes_sent / 1024 / 1024,
        'network_recv_mb': net.bytes_recv / 1024 / 1024,
        'battery_percent': battery.percent if battery else None,
        'battery_power_plugged': battery.power_plugged if battery else None,
        'hostname': socket.gethostname(),
        'timestamp': datetime.now().isoformat()
    }


def push_metrics(metrics):
    """推送指标到服务器"""
    payload = {
        'type': 'monitor',
        'data': metrics,
        'timestamp': metrics['timestamp']
    }
    
    try:
        resp = requests.post(
            SERVER_URL,
            json=payload,
            verify=VERIFY_SSL,
            timeout=10
        )
        if resp.status_code == 200:
            return True
        else:
            # print(f"[{datetime.now().strftime('%H:%M:%S')}] 推送失败: {resp.status_code} {resp.text[:100]}")
            return False
    except requests.exceptions.ConnectionError:
        return False  # 网络断开时静默
    except Exception as e:
        # print(f"[{datetime.now().strftime('%H:%M:%S')}] 推送异常: {e}")
        return False


# ============================================
# 主循环
# ============================================
def main():
    # print(f"📡 Mac mini 监控采集启动")
    # print(f"  服务器: {SERVER_URL}")
    # print(f"  间隔: {PUSH_INTERVAL}s")
    # print(f"  PID: {os.getpid()}")
    # print()
    
    fail_count = 0
    
    while True:
        try:
            metrics = collect_metrics()
            ok = push_metrics(metrics)
            
            if ok:
                fail_count = 0
                cpu = metrics['cpu']
                mem = metrics['memory']
                disk = metrics['disk']
                # print(f"[{datetime.now().strftime('%H:%M:%S')}] CPU:{cpu:5.1f}%  MEM:{mem:5.1f}%  DISK:{disk:5.1f}%  ✓")
            else:
                fail_count += 1
                if fail_count >= 12:  # 连续失败1分钟
                    # print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ 连续 {fail_count} 次推送失败，等30秒重试")
                    time.sleep(30)
                    continue
                    
        except KeyboardInterrupt:
            # print("\n👋 采集已停止")
            break
        except Exception as e:
            # print(f"[ERROR] {e}")
        
        time.sleep(PUSH_INTERVAL)


if __name__ == '__main__':
    main()

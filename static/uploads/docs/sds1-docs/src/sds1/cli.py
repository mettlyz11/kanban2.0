#!/usr/bin/env python3
"""SDS1 命令行入口"""

import argparse
import sys
import os
import subprocess
from pathlib import Path

# 确保能导入 sds1 模块
SDS_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SDS_DIR))

def get_pid_file():
    return Path("/tmp/sds1.pid")

def get_sds_dir():
    return SDS_DIR

def start():
    """启动 SDS"""
    script = get_sds_dir() / "scripts" / "start_sds.sh"
    if script.exists():
        subprocess.run(["bash", str(script)], check=True)
    else:
        # 直接启动
        main_py = get_sds_dir() / "sds_main.py"
        subprocess.Popen(
            [sys.executable, str(main_py), "--continuous"],
            cwd=str(get_sds_dir()),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        # print("✅ SDS1 已启动")

def stop():
    """停止 SDS"""
    script = get_sds_dir() / "scripts" / "stop_sds.sh"
    if script.exists():
        subprocess.run(["bash", str(script)], check=True)
    else:
        pid_file = get_pid_file()
        if pid_file.exists():
            pid = pid_file.read_text().strip()
            subprocess.run(["kill", pid], check=False)
            pid_file.unlink()
            # print("✅ SDS1 已停止")
        else:
            # print("⚠️ SDS1 未运行")

def status():
    """查看 SDS 状态"""
    pid_file = get_pid_file()
    if pid_file.exists():
        pid = pid_file.read_text().strip()
        result = subprocess.run(["ps", "-p", pid], capture_output=True, text=True)
        if result.returncode == 0:
            # print(f"✅ SDS1 运行中 (PID: {pid})")
        else:
            # print(f"⚠️ PID 文件存在但进程未运行 ({pid})")
    else:
        # print("❌ SDS1 未运行")

def main():
    parser = argparse.ArgumentParser(description="SDS1 命令行工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # start
    start_parser = subparsers.add_parser("start", help="启动 SDS")
    
    # stop
    stop_parser = subparsers.add_parser("stop", help="停止 SDS")
    
    # status
    status_parser = subparsers.add_parser("status", help="查看状态")
    
    # restart
    restart_parser = subparsers.add_parser("restart", help="重启 SDS")
    
    args = parser.parse_args()
    
    if args.command == "start":
        start()
    elif args.command == "stop":
        stop()
    elif args.command == "status":
        status()
    elif args.command == "restart":
        stop()
        start()
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()

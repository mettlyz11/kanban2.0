#!/usr/bin/env python3
import subprocess
import sys

result = subprocess.run(
    [sys.executable, 'AppleWatch睡眠数据分析脚本_2026-04-25.py'],
    capture_output=True,
    text=True,
    cwd='/Users/mettlyz/.openclaw/workspace/output/task-1964'
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)

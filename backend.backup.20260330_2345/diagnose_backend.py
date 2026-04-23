#!/usr/bin/env python3
"""
完整诊断脚本
"""

import subprocess
import sys

def run_cmd(cmd, desc):
    print(f"\n{'='*60}")
    print(f"📋 {desc}")
    print(f"命令：{cmd}")
    print('='*60)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout[:2000])
    if result.stderr:
        print("STDERR:", result.stderr[:1000])
    return result.returncode == 0

print("🔍 开始诊断看板后端服务...")

# 1. 检查进程
run_cmd("ps aux | grep -E 'python.*app|kanban' | grep -v grep", "检查 Python 进程")

# 2. 检查端口
run_cmd("netstat -tlnp 2>/dev/null | grep -E '8086|80' || ss -tlnp | grep -E '8086|80'", "检查端口监听")

# 3. 测试后端直连
run_cmd("curl -s --connect-timeout 5 http://localhost:8086/api/meetings/ | head -c 500", "测试后端 API 直连")

# 4. 测试 Nginx
run_cmd("curl -s --connect-timeout 5 http://localhost/api/meetings/ | head -c 500", "测试 Nginx 代理")

# 5. 检查 systemd 服务
run_cmd("systemctl status kanban-backend 2>&1 | head -30", "检查 systemd 服务状态")

# 6. 检查日志
run_cmd("tail -50 /var/log/kanban-backend.log", "检查后端日志")

# 7. 检查 Nginx 错误
run_cmd("tail -30 /var/log/nginx/error.log", "检查 Nginx 错误日志")

# 8. 检查 app.py 完整性
run_cmd("wc -l /opt/kanban-react/backend/app.py && grep -n 'app.run\\|if __name__' /opt/kanban-react/backend/app.py", "检查 app.py 完整性")

# 9. 测试 Python 导入
run_cmd("cd /opt/kanban-react/backend && python3 -c 'from app import app; print(\"✅ 导入成功\")'", "测试 Flask 应用导入")

# 10. 检查 Nginx 配置
run_cmd("nginx -T 2>&1 | grep -A 10 'location /api/'", "检查 Nginx API 配置")

print("\n" + "="*60)
print("✅ 诊断完成！")
print("="*60)

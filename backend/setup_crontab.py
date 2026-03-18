#!/usr/bin/env python3
"""
更新 crontab - 添加系统监控数据收集任务
"""
import subprocess
import sys

NEW_ENTRY = "*/5 * * * * cd /Users/mettlyz/.openclaw/workspace/kanban-react/backend && ./collect_metrics.sh >> /tmp/metrics_collect.log 2>&1"
COMMENT = "# 系统监控数据收集（每 5 分钟）"

def get_current_crontab():
    """获取当前 crontab"""
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return result.stdout
    except Exception as e:
        print(f"获取 crontab 失败：{e}")
    return ""

def update_crontab():
    """更新 crontab"""
    current = get_current_crontab()
    
    # 如果已经存在，跳过
    if 'collect_metrics.sh' in current:
        print("⚠️  系统监控任务已存在，无需添加")
        return
    
    # 添加新条目
    lines = current.strip().split('\n') if current.strip() else []
    lines.append('')
    lines.append(COMMENT)
    lines.append(NEW_ENTRY)
    
    new_crontab = '\n'.join(lines)
    
    # 写入临时文件
    with open('/tmp/new_crontab.txt', 'w') as f:
        f.write(new_crontab)
    
    # 安装 crontab
    try:
        with open('/tmp/new_crontab.txt', 'r') as f:
            result = subprocess.run(['crontab'], stdin=f, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Crontab 更新成功")
            print(f"\n新增任务：{NEW_ENTRY}")
            return True
        else:
            print(f"❌ 更新失败：{result.stderr}")
    except Exception as e:
        print(f"❌ 更新失败：{e}")
    
    return False

if __name__ == '__main__':
    success = update_crontab()
    sys.exit(0 if success else 1)

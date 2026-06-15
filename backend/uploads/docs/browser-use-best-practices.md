# Browser-Use 内存管理最佳实践

## 问题根源

Browser-use 在子代理中使用时，会启动 `skill_cli.daemon` 进程，但子代理结束后这些进程不会自动清理，导致内存累积。

## 解决方案

### 方案1: 子代理退出时自动清理 (推荐)

在子代理任务结束时，添加清理代码：

```python
import atexit
import os
import subprocess

def cleanup_browser_use():
    """清理browser-use残留进程"""
    subprocess.run([
        "pkill", "-f", 
        "browser_use.skill_cli.daemon"
    ], capture_output=True)
    
# 注册退出时清理
atexit.register(cleanup_browser_use)
```

### 方案2: 使用上下文管理器

```python
from contextlib import contextmanager
import subprocess

@contextmanager
def browser_use_session():
    """browser-use会话上下文管理器"""
    try:
        yield
    finally:
        # 清理所有browser-use进程
        subprocess.run([
            "pkill", "-9", "-f", 
            "browser-use-user-data-dir"
        ], capture_output=True)
        subprocess.run([
            "pkill", "-9", "-f", 
            "browser_use.skill_cli.daemon"
        ], capture_output=True)

# 使用示例
with browser_use_session():
    # 执行browser-use操作
    pass
```

### 方案3: 定期清理脚本

创建定时任务，定期清理残留进程：

```bash
#!/bin/bash
# cleanup-browser-use.sh

# 清理超过1小时的browser-use进程
ps aux | grep "browser_use.skill_cli.daemon" | awk '{if ($10 ~ /[0-9]+:[0-9]+/) print $2}' | xargs -I {} kill -9 {} 2>/dev/null

# 清理browser-use临时目录
rm -rf /var/folders/*/_0y_3qbd5k97n_htrrqxkmh40000gn/T/browser-use-user-data-dir-*
```

添加到crontab：
```
*/30 * * * * /Users/mettlyz/.openclaw/workspace/scripts/cleanup-browser-use.sh
```

### 方案4: 限制并发浏览器实例

在子代理中限制同时运行的浏览器数量：

```python
import semaphore

# 全局信号量，限制最多2个浏览器实例
browser_semaphore = semaphore.Semaphore(2)

def download_with_browser():
    with browser_semaphore:
        # 执行browser操作
        pass
```

### 方案5: 使用无头模式 + 快速退出

配置browser-use使用无头模式，并设置超时：

```python
from browser_use import Agent

agent = Agent(
    headless=True,  # 无头模式节省内存
    timeout=30,     # 30秒超时
    auto_close=True # 自动关闭浏览器
)
```

## 实施建议

### 立即实施
1. ✅ 在子代理模板中添加清理代码
2. ✅ 创建定期清理脚本
3. ✅ 设置内存监控告警

### 长期优化
1. 修改browser-use skill，添加自动清理功能
2. 使用容器化运行，隔离资源
3. 实现进程池管理，复用浏览器实例

## 监控命令

```bash
# 监控browser-use进程数
watch -n 5 'ps aux | grep browser_use | grep -v grep | wc -l'

# 监控内存使用
watch -n 5 'vm_stat | grep "Pages free"'

# 一键清理
pkill -f "browser_use.skill_cli.daemon"
pkill -f "browser-use-user-data-dir"
```

## 检查清单

- [ ] 子代理任务是否包含清理代码
- [ ] 定期清理脚本是否已部署
- [ ] 内存监控是否启用
- [ ] 浏览器实例是否有限制
- [ ] 是否使用无头模式

---

**记住**: 预防胜于治疗，在子代理设计阶段就考虑资源清理！

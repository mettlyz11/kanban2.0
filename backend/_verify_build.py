# 验证 TypeScript 编译
import subprocess, os
os.chdir('/opt/kanban-react/frontend')
r = subprocess.run(['npx', 'tsc', '--noEmit'], capture_output=True, text=True, timeout=30)
if r.returncode == 0:
    # print('OK: TypeScript 编译通过')
else:
    # 只输出错误行
    for line in r.stdout.split('\n'):
        if 'error' in line.lower():
            # print(line)
    for line in r.stderr.split('\n'):
        if 'error' in line.lower():
            # print(line)
    # print(f'exit: {r.returncode}')

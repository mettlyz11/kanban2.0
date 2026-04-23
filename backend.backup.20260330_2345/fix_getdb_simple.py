#!/usr/bin/env python3
"""
完全重写 get_db 函数 - 使用最简单的方案
"""

with open('/opt/kanban-react/backend/app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到并替换 get_db 函数
new_lines = []
in_get_db = False
skip_until_next_def = False

for i, line in enumerate(lines):
    if 'def get_db():' in line:
        # 开始替换
        in_get_db = True
        indent = '    '
        new_lines.append(f"{indent}def get_db():\n")
        new_lines.append(f"{indent}    \"\"\"获取数据库连接（简单版本）\"\"\"\n")
        new_lines.append(f"{indent}    import pymysql\n")
        new_lines.append(f"{indent}    conn = pymysql.connect(\n")
        new_lines.append(f"{indent}        host='rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',\n")
        new_lines.append(f"{indent}        port=3306,\n")
        new_lines.append(f"{indent}        user='kanban',\n")
        new_lines.append(f"{indent}        password='Irc210Irc210!',\n")
        new_lines.append(f"{indent}        database='kanban',\n")
        new_lines.append(f"{indent}        charset='utf8mb4'\n")
        new_lines.append(f"{indent}    )\n")
        new_lines.append(f"{indent}    return conn\n")
        skip_until_next_def = True
        continue
    
    if skip_until_next_def:
        if line.startswith('def ') or (line.strip() and not line.startswith(' ') and not line.startswith('#')):
            skip_until_next_def = False
        else:
            continue
    
    new_lines.append(line)

with open('/opt/kanban-react/backend/app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ get_db 函数已重写为最简单版本")

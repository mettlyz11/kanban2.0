# 这段代码用于在 app.py 中添加文献调研记录路由注册
# 手动执行以下命令：
# python3 app_route_addition.py

import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 在管理员后台路由后添加文献调研记录路由
insert_text = '''
# ============================================
# 导入文献调研记录路由
# ============================================
try:
    from research_logs_routes import research_logs_bp
    app.register_blueprint(research_logs_bp)
    logger.info("✅ 文献调研记录路由已注册")
except ImportError as e:
    logger.warning(f"⚠️ 文献调研记录路由导入失败：{e}")
'''

# 找到管理员后台路由导入后的位置
pattern = r'(from admin_routes import admin_bp\n.*?logger\.warning\(f"⚠️ 管理员后台路由导入失败：\{e\}"\))'
match = re.search(pattern, content, re.DOTALL)

if match:
    insert_pos = match.end()
    content = content[:insert_pos] + insert_text + content[insert_pos:]
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 文献调研记录路由注册已添加到 app.py")
else:
    print("❌ 未找到管理员后台路由导入代码")

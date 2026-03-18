#!/usr/bin/env python3
"""
任务审核系统安装和配置脚本

功能:
1. 升级数据库
2. 配置审核系统
3. 注册到主应用
"""

import os
import sys
import shutil

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_status(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.END} {msg}")

def print_success(msg):
    print(f"{Colors.GREEN}[OK]{Colors.END} {msg}")

def print_warning(msg):
    print(f"{Colors.YELLOW}[WARN]{Colors.END} {msg}")

def print_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.END} {msg}")


def check_files():
    """检查必要的文件是否存在"""
    print_status("检查必要文件...")
    
    files = [
        'task_audit_system.py',
        'gear_system_enhanced.py',
        'supervisor_system_enhanced.py',
        'long_thinking_enhanced.py',
        'perception_agent_enhanced.py',
        'audit_routes.py',
        'upgrade_db_audit.py'
    ]
    
    backend_dir = '/Users/mettlyz/.openclaw/workspace/kanban-react/backend'
    
    for f in files:
        filepath = os.path.join(backend_dir, f)
        if os.path.exists(filepath):
            print_success(f"  ✓ {f}")
        else:
            print_error(f"  ✗ {f} 不存在")
            return False
    
    return True


def upgrade_database():
    """升级数据库"""
    print_status("升级数据库...")
    
    backend_dir = '/Users/mettlyz/.openclaw/workspace/kanban-react/backend'
    
    # 运行数据库升级脚本
    result = os.system(f'cd {backend_dir} && python3 upgrade_db_audit.py')
    
    if result == 0:
        print_success("数据库升级完成")
        return True
    else:
        print_error("数据库升级失败")
        return False


def backup_original_files():
    """备份原始文件"""
    print_status("备份原始文件...")
    
    backend_dir = '/Users/mettlyz/.openclaw/workspace/kanban-react/backend'
    backup_dir = os.path.join(backend_dir, 'backup_original')
    
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        'long_thinking.py',
        'perception_agent.py'
    ]
    
    for f in files_to_backup:
        src = os.path.join(backend_dir, f)
        dst = os.path.join(backup_dir, f)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            print_success(f"  备份 {f}")


def print_next_steps():
    """打印下一步操作"""
    print("\n" + "=" * 60)
    print("安装完成！下一步操作")
    print("=" * 60)
    
    print("""
1. 【修改app.py】添加审核路由:
   
   在 app.py 中添加:
   ```python
   from audit_routes import register_audit_routes
   register_audit_routes(app)
   ```

2. 【运行测试】验证系统:
   ```bash
   cd kanban-react/backend
   python3 task_audit_system.py
   python3 gear_system_enhanced.py
   python3 supervisor_system_enhanced.py
   ```

3. 【启用新系统】使用增强版:
   
   - 长思考系统: 使用 long_thinking_enhanced.py
   - 感知Agent: 使用 perception_agent_enhanced.py
   - 齿轮系统: 使用 gear_system_enhanced.py

4. 【API端点】查看审核API:
   
   GET  /api/audit/tasks/pending       - 待审核任务
   POST /api/audit/tasks/<id>/approve  - 批准任务
   POST /api/audit/tasks/<id>/reject   - 拒绝任务
   GET  /api/audit/dashboard           - 审核仪表板

5. 【数据库字段】已添加:
   
   - tasks.requires_audit (默认1)
   - tasks.audit_status (pending/approved/rejected)

""")


def main():
    """主函数"""
    print("=" * 60)
    print("任务审核系统安装脚本")
    print("=" * 60)
    print()
    
    # 1. 检查文件
    if not check_files():
        print_error("缺少必要文件，安装中止")
        return False
    
    print()
    
    # 2. 备份原始文件
    backup_original_files()
    
    print()
    
    # 3. 升级数据库
    if not upgrade_database():
        print_warning("数据库升级可能部分失败，请检查日志")
    
    print()
    
    # 4. 打印下一步
    print_next_steps()
    
    return True


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n安装已取消")
        sys.exit(1)
    except Exception as e:
        print_error(f"安装失败: {e}")
        sys.exit(1)

import os
import json
from datetime import datetime

def scan_workspace(workspace_path='~/.openclaw/workspace'):
    """扫描workspace目录，生成文件索引"""
    workspace_path = os.path.expanduser(workspace_path)
    
    # 文件类型映射
    type_mapping = {
        '.md': 'document',
        '.py': 'code',
        '.js': 'code',
        '.tsx': 'code',
        '.ts': 'code',
        '.json': 'config',
        '.html': 'web',
        '.css': 'style',
        '.sql': 'database',
        '.sh': 'script',
        '.yml': 'config',
        '.yaml': 'config',
        '.txt': 'text',
    }
    
    # 重要文件/目录模式
    important_patterns = [
        ('SOUL.md', '身份定义'),
        ('USER.md', '用户档案'),
        ('AGENTS.md', '执行准则'),
        ('MEMORY.md', '长期记忆'),
        ('standards.md', '标准规范'),
        ('HEARTBEAT.md', '定时检查'),
        ('IDENTITY.md', '身份配置'),
        ('BOOTSTRAP.md', '启动配置'),
        ('USER_PROFILE.md', '用户配置'),
        ('RESOURCES.md', '资源配置'),
        ('API_DOCUMENTATION.md', 'API文档'),
        ('BACKEND_API_REPORT.md', '后端API报告'),
        ('README.md', '项目说明'),
        ('app.py', 'Flask主程序'),
        ('models.py', '数据模型'),
        ('database.py', '数据库模块'),
        ('index.html', '入口页面'),
        ('package.json', 'Node配置'),
        ('tsconfig.json', 'TypeScript配置'),
    ]
    
    files = []
    categories = {}
    
    for root, dirs, filenames in os.walk(workspace_path):
        # 跳过隐藏目录和node_modules等
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'dist', 'build', '.git']]
        
        for filename in filenames:
            if filename.startswith('.'):
                continue
                
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, workspace_path)
            
            # 确定文件类型
            ext = os.path.splitext(filename)[1].lower()
            file_type = type_mapping.get(ext, 'file')
            
            # 确定分类
            dir_name = os.path.dirname(rel_path)
            if dir_name:
                # 根据目录名分类
                if 'kanban' in dir_name.lower():
                    category = '看板系统'
                elif 't109' in dir_name.lower():
                    category = 'T109平台'
                elif 'database' in dir_name.lower():
                    category = '数据库'
                elif 'memory' in dir_name.lower():
                    category = '记忆文件'
                elif 'docs' in dir_name.lower():
                    category = '文档'
                elif 'frontend' in dir_name.lower():
                    category = '前端代码'
                elif 'backend' in dir_name.lower():
                    category = '后端代码'
                elif 'skills' in dir_name.lower():
                    category = '技能'
                elif 'tools' in dir_name.lower():
                    category = '工具'
                else:
                    category = dir_name.split('/')[0] if '/' in dir_name else '其他'
            else:
                category = '根目录'
            
            # 查找描述
            desc = f'{ext[1:].upper() if ext else "文件"}文件'
            for pattern, pattern_desc in important_patterns:
                if filename == pattern:
                    desc = pattern_desc
                    break
            
            # 获取文件信息
            try:
                stat = os.stat(full_path)
                size = stat.st_size
                mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
            except:
                size = 0
                mtime = ''
            
            files.append({
                'name': filename,
                'type': file_type,
                'path': rel_path,
                'category': category,
                'desc': desc,
                'size': size,
                'modified': mtime
            })
            
            # 统计分类
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
    
    return {
        'files': files,
        'categories': categories,
        'total': len(files)
    }

if __name__ == '__main__':
    result = scan_workspace()
    print(json.dumps(result, indent=2, ensure_ascii=False))

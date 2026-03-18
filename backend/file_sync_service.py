"""
文件同步服务
监听工作空间文件变化，自动更新架构图节点信息
"""

import os
import time
import threading
import sqlite3
import json
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kanban_v5.db')
WORKSPACE_PATH = '/Users/mettlyz/.openclaw/workspace'

# 需要监听的文件
WATCHED_FILES = [
    'SOUL.md', 'USER.md', 'AGENTS.md', 'standards.md',
    'MEMORY.md', 'HEARTBEAT.md', 'CHECKLIST.md', 'TOOLS.md'
]

class WorkspaceEventHandler(FileSystemEventHandler):
    """工作空间文件变化处理器"""
    
    def __init__(self):
        super().__init__()
        self.last_modified = {}
    
    def on_modified(self, event):
        """文件修改事件"""
        if isinstance(event, FileModifiedEvent):
            filepath = event.src_path
            filename = os.path.basename(filepath)
            
            # 只处理关注的文件
            if filename in WATCHED_FILES:
                # 防止重复触发（某些编辑器会触发多次）
                now = time.time()
                if filename in self.last_modified and (now - self.last_modified[filename]) < 1.0:
                    return
                
                self.last_modified[filename] = now
                
                print(f"📝 检测到文件变化：{filename}")
                self.update_architecture_node(filename, filepath)
    
    def update_architecture_node(self, filename: str, filepath: str):
        """更新架构图中的节点信息"""
        try:
            # 读取文件内容
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取描述信息（第一行或第二行）
            lines = content.split('\n')
            description = ''
            
            for line in lines[:5]:  # 在前 5 行查找描述
                line = line.strip()
                if line and not line.startswith('#'):
                    description = line[:100]  # 限制长度
                    break
            
            # 更新数据库
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            c.execute('''
                UPDATE workflow_architecture 
                SET description=?, updated_at=CURRENT_TIMESTAMP
                WHERE file_path=?
            ''', (description, filename))
            
            if c.rowcount > 0:
                print(f"✅ 已更新节点：{filename} -> {description[:50]}...")
                
                # 创建新版本记录
                self.save_version(f"自动更新：{filename}")
            else:
                print(f"⚠️ 未找到对应节点：{filename}")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ 更新节点失败：{e}")
    
    def save_version(self, description: str = "自动保存"):
        """保存版本历史"""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # 获取当前节点和连接
            c.execute('SELECT * FROM workflow_architecture')
            nodes = []
            for row in c.fetchall():
                nodes.append({
                    'id': row[0],
                    'name': row[1],
                    'type': row[2],
                    'x': row[3],
                    'y': row[4],
                    'color': row[5],
                    'file_path': row[6],
                    'description': row[7]
                })
            
            c.execute('SELECT * FROM workflow_connections')
            connections = []
            for row in c.fetchall():
                connections.append({
                    'id': row[0],
                    'from_node': row[1],
                    'to_node': row[2]
                })
            
            # 获取当前最大版本号
            c.execute('SELECT MAX(version) FROM workflow_architecture_versions')
            max_version = c.fetchone()[0] or 0
            new_version = max_version + 1
            
            # 保存新版本
            c.execute('''
                INSERT INTO workflow_architecture_versions (version, nodes_json, connections_json, description)
                VALUES (?, ?, ?, ?)
            ''', (new_version, json.dumps(nodes, ensure_ascii=False), json.dumps(connections, ensure_ascii=False), description))
            
            conn.commit()
            conn.close()
            
            print(f"💾 已保存版本 {new_version}: {description}")
            
        except Exception as e:
            print(f"❌ 保存版本失败：{e}")


def start_file_sync_service():
    """启动文件同步服务"""
    event_handler = WorkspaceEventHandler()
    
    observer = Observer()
    observer.schedule(event_handler, path=WORKSPACE_PATH, recursive=False)
    observer.start()
    
    print(f"🚀 文件同步服务已启动")
    print(f"📂 监听目录：{WORKSPACE_PATH}")
    print(f"📄 监听文件：{', '.join(WATCHED_FILES)}")
    print(f"💡 按 Ctrl+C 停止服务\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n⏹️ 文件同步服务已停止")
    
    observer.join()


if __name__ == '__main__':
    start_file_sync_service()

#!/usr/bin/env python3
"""
看板任务管理器 - 标准化模块
用于自我驱动系统与看板系统 RDS 数据库交互
"""

import sys
from config_loader import get_config
import os

# 添加 scripts 目录到路径，以便导入 lib.db_connector
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import mysql.connector
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from lib.db_connector import get_db_connection, execute_query, execute_update

# 数据库配置
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3307,
    'user': 'kanban',
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': 'kanban',
    'ssl_disabled': True,
    'connect_timeout': 10
}

# 附件上传路径
# 本地开发环境
LOCAL_OUTPUT_BASE = Path(get_config("paths.output"))
# 远程服务器配置
REMOTE_SERVER = "47.93.184.128"
REMOTE_UPLOAD_DIR = "/opt/kanban-react/backend/uploads"
SSH_KEY = "/Users/mettlyz/.openclaw/workspace/Files/Info/aliserver1.pem"


class KanbanTaskManager:
    """看板任务管理器"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """连接数据库"""
        try:
            self.conn = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor(dictionary=True)
            return True
        except Exception as e:
            print(f"[ERROR] 数据库连接失败: {e}")
            return False
    
    def close(self):
        """关闭连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def get_pending_tasks(self, limit: int = 10) -> List[Dict]:
        """获取待执行的任务"""
        try:
            self.cursor.execute("""
                SELECT id, title, status, details, priority, category_id
                FROM tasks
                WHERE status = 'pending'
                  AND (task_summary IS NULL OR task_summary = '')
                  AND requires_audit = 0
                ORDER BY priority DESC, id ASC
                LIMIT %s
            """, (limit,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"[ERROR] 获取任务失败: {e}")
            return []
    
    def update_task_status(self, task_id: int, status: str, 
                          task_summary: str = None,
                          execution_log: str = None,
                          remaining_issues: str = None,
                          improvement_suggestions: str = None) -> bool:
        """更新任务状态"""
        try:
            # 构建更新字段
            updates = ["status = %s", "updated_at = NOW()"]
            params = [status]
            
            if task_summary:
                updates.append("task_summary = %s")
                params.append(task_summary)
            
            if execution_log:
                updates.append("execution_log = %s")
                params.append(execution_log)
            
            if remaining_issues:
                updates.append("remaining_issues = %s")
                params.append(remaining_issues)
            
            if improvement_suggestions:
                updates.append("improvement_suggestions = %s")
                params.append(improvement_suggestions)
            

            
            params.append(task_id)
            
            sql = f"UPDATE tasks SET {', '.join(updates)} WHERE id = %s"
            self.cursor.execute(sql, tuple(params))
            self.conn.commit()
            
            print(f"[OK] 任务 #{task_id} 状态已更新为 {status}")
            return True
            
        except Exception as e:
            print(f"[ERROR] 更新任务状态失败: {e}")
            self.conn.rollback()
            return False
    
    def add_execution_log(self, task_id: int, log_entry: str) -> bool:
        """添加执行日志（追加模式）"""
        try:
            # 先读取现有日志
            self.cursor.execute(
                "SELECT execution_log FROM tasks WHERE id = %s", 
                (task_id,)
            )
            result = self.cursor.fetchone()
            
            existing_log = result['execution_log'] if result and result['execution_log'] else ""
            
            # 追加新日志
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            new_log = f"{existing_log}\n[{timestamp}] {log_entry}".strip()
            
            # 更新
            self.cursor.execute(
                "UPDATE tasks SET execution_log = %s WHERE id = %s",
                (new_log, task_id)
            )
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"[ERROR] 添加执行日志失败: {e}")
            self.conn.rollback()
            return False
    
    def get_task_attachment_path(self, task_id: int) -> Path:
        """获取任务附件目录"""
        path = ATTACHMENTS_BASE / f"task{task_id}"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def sync_task_files_to_server(self, task_id: int) -> List[str]:
        """同步本地任务文件到远程服务器，并更新attachments表"""
        import subprocess
        import os
        
        local_dir = LOCAL_OUTPUT_BASE / f"task-{task_id}"
        if not local_dir.exists():
            print(f"[INFO] 本地目录不存在: {local_dir}")
            return []
        
        synced_files = []
        
        try:
            # 1. SCP同步文件到服务器
            for file_path in local_dir.iterdir():
                if file_path.is_file():
                    filename = file_path.name
                    
                    # SCP上传
                    scp_cmd = [
                        "scp", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
                        str(file_path),
                        f"root@{REMOTE_SERVER}:{REMOTE_UPLOAD_DIR}/{filename}"
                    ]
                    result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        # 2. 插入attachments表（使用正确的URL格式）
                        url = f"/uploads/docs/{filename}"
                        self._insert_attachment_record(task_id, filename, url, file_path.stat().st_size)
                        synced_files.append(filename)
                        print(f"[OK] 已同步: {filename} -> {url}")
                    else:
                        print(f"[ERROR] SCP失败: {filename} - {result.stderr}")
            
            return synced_files
            
        except Exception as e:
            print(f"[ERROR] 同步失败: {e}")
            return []
    
    def _insert_attachment_record(self, task_id: int, filename: str, url: str, size: int):
        """插入附件记录到数据库"""
        try:
            self.cursor.execute("""
                INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type, created_at)
                VALUES ('task', %s, %s, %s, %s, 'document', NOW())
                ON DUPLICATE KEY UPDATE url = VALUES(url), size = VALUES(size), updated_at = NOW()
            """, (task_id, filename, url, size))
            self.conn.commit()
        except Exception as e:
            print(f"[ERROR] 插入附件记录失败: {e}")
            self.conn.rollback()
    
    def upload_task_file(self, task_id: int, local_file: Path, 
                         filename: str = None) -> Optional[str]:
        """上传文件到任务附件目录（本地+远程同步）"""
        try:
            # 确定文件名
            if filename is None:
                filename = local_file.name
            
            # 本地路径
            local_dir = LOCAL_OUTPUT_BASE / f"task-{task_id}"
            local_dir.mkdir(parents=True, exist_ok=True)
            local_path = local_dir / filename
            
            # 复制到本地
            import shutil
            shutil.copy2(local_file, local_path)
            
            # 远程URL格式
            relative_path = f"/uploads/docs/{filename}"
            
            # SCP到服务器
            import subprocess
            scp_cmd = [
                "scp", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
                str(local_path),
                f"root@{REMOTE_SERVER}:{REMOTE_UPLOAD_DIR}/{filename}"
            ]
            subprocess.run(scp_cmd, capture_output=True, timeout=30)
            
            self.add_execution_log(
                task_id, 
                f"文件上传: {filename} -> {relative_path}"
            )
            
            print(f"[OK] 文件已上传: {relative_path}")
            return relative_path
            
        except Exception as e:
            print(f"[ERROR] 上传文件失败: {e}")
            return None
    
    def upload_task_directory(self, task_id: int, source_dir: Path, 
                               pattern: str = "*") -> List[str]:
        """上传目录下所有文件（逐个上传，不上传压缩包）"""
        uploaded = []
        try:
            for file_path in source_dir.glob(pattern):
                if file_path.is_file():
                    relative_path = self.upload_task_file(task_id, file_path)
                    if relative_path:
                        uploaded.append(relative_path)
            
            print(f"[OK] 已上传 {len(uploaded)} 个文件")
            return uploaded
            
        except Exception as e:
            print(f"[ERROR] 上传目录失败: {e}")
            return uploaded
    
    def mark_task_completed(self, task_id: int, summary: str,
                           execution_details: str = None,
                           attachments: List[str] = None) -> bool:
        """标记任务完成（标准化流程）"""
        try:
            # 构建执行日志
            log_parts = []
            if execution_details:
                log_parts.append(execution_details)
            if attachments:
                log_parts.append(f"附件: {', '.join(attachments)}")
            
            execution_log = "\n".join(log_parts) if log_parts else None
            
            # 更新任务
            success = self.update_task_status(
                task_id=task_id,
                status='completed',
                task_summary=summary,
                execution_log=execution_log
            )
            
            if success:
                print(f"[OK] 任务 #{task_id} 已完成标记")
            
            return success
            
        except Exception as e:
            print(f"[ERROR] 标记任务完成失败: {e}")
            return False


# 便捷函数
def get_task_manager() -> KanbanTaskManager:
    """获取任务管理器实例"""
    manager = KanbanTaskManager()
    if manager.connect():
        return manager
    raise Exception("无法连接数据库")


if __name__ == "__main__":
    main()
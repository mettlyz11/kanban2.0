#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T109 MacMini 任务轮询服务 - 模拟 SLURM 测试版

用于在没有 SLURM 环境的机器上测试任务轮询逻辑
使用本地进程模拟 SLURM 作业执行
"""

import os
import sys
import json
import time
import sqlite3
import logging
import subprocess
import threading
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback
import hashlib
import shutil
import tempfile

# 配置日志
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, f'task_worker_sim_{datetime.now().strftime("%Y%m%d")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('TaskWorker-Sim')

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kanban_v5.db')

# 模拟输出目录
SIM_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sim_output')
os.makedirs(SIM_OUTPUT_DIR, exist_ok=True)


class TaskStatus(Enum):
    TODO = 'todo'
    IN_PROGRESS = 'in_progress'
    SUBMITTED = 'submitted'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    RETRYING = 'retrying'


@dataclass
class Task:
    """任务数据类"""
    id: int
    project_id: int
    title: str
    description: str
    status: str
    priority: str
    details: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str
    start_time: Optional[str]
    end_time: Optional[str]
    result_summary: Optional[str]
    depends_on: Optional[int]
    requires_audit: int
    audit_status: str
    slurm_job_id: Optional[int] = None
    slurm_output_file: Optional[str] = None
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SimulatedDatabase:
    """模拟数据库操作"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
    
    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, timeout=30)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def get_pending_tasks(self, limit: int = 10) -> List[Task]:
        conn = self._get_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT t.id, t.project_id, t.title, t.description, t.status, t.priority,
                   t.details, t.created_at, t.updated_at, t.start_time, t.end_time,
                   t.result_summary, t.depends_on, t.requires_audit, t.audit_status,
                   t.slurm_job_id, t.slurm_output_file, t.retry_count
            FROM tasks t
            WHERE t.status = 'todo'
              AND (t.depends_on IS NULL OR 
                   EXISTS (SELECT 1 FROM tasks dt 
                           WHERE dt.id = t.depends_on 
                           AND dt.status = 'completed'))
            ORDER BY 
                CASE t.priority 
                    WHEN 'critical' THEN 1 
                    WHEN 'high' THEN 2 
                    WHEN 'medium' THEN 3 
                    WHEN 'low' THEN 4 
                    ELSE 5 
                END,
                t.created_at ASC
            LIMIT ?
        ''', (limit,))
        
        rows = c.fetchall()
        tasks = []
        for row in rows:
            details = None
            if row['details']:
                try:
                    details = json.loads(row['details'])
                except (json.JSONDecodeError, TypeError):
                    details = {'raw': row['details']}
            
            task = Task(
                id=row['id'],
                project_id=row['project_id'],
                title=row['title'],
                description=row['description'],
                status=row['status'],
                priority=row['priority'],
                details=details,
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                start_time=row['start_time'],
                end_time=row['end_time'],
                result_summary=row['result_summary'],
                depends_on=row['depends_on'],
                requires_audit=row['requires_audit'],
                audit_status=row['audit_status'],
                slurm_job_id=row['slurm_job_id'],
                slurm_output_file=row['slurm_output_file'],
                retry_count=row['retry_count'] or 0
            )
            tasks.append(task)
        
        return tasks
    
    def update_task_status(self, task_id: int, status: str, 
                          result_summary: Optional[str] = None,
                          slurm_job_id: Optional[int] = None,
                          slurm_output_file: Optional[str] = None,
                          error_message: Optional[str] = None):
        conn = self._get_connection()
        c = conn.cursor()
        
        updates = ["status = ?", "updated_at = datetime('now')"]
        values = [status]
        
        if result_summary:
            updates.append("result_summary = ?")
            values.append(result_summary)
        
        if slurm_job_id is not None:
            updates.append("slurm_job_id = ?")
            values.append(slurm_job_id)
        
        if slurm_output_file is not None:
            updates.append("slurm_output_file = ?")
            values.append(slurm_output_file)
        
        if error_message:
            c.execute("SELECT details FROM tasks WHERE id = ?", (task_id,))
            row = c.fetchone()
            details = {}
            if row and row['details']:
                try:
                    details = json.loads(row['details'])
                except:
                    pass
            
            details['last_error'] = error_message
            details['last_error_time'] = datetime.now().isoformat()
            updates.append("details = ?")
            values.append(json.dumps(details, ensure_ascii=False))
        
        if status in ['in_progress', 'submitted', 'running']:
            updates.append("start_time = datetime('now')")
        elif status in ['completed', 'failed', 'cancelled']:
            updates.append("end_time = datetime('now')")
        
        values.append(task_id)
        
        sql = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        c.execute(sql, values)
        conn.commit()
        
        logger.info(f"任务 {task_id} 状态更新为：{status}")
    
    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        conn = self._get_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT id, project_id, title, description, status, priority,
                   details, created_at, updated_at, start_time, end_time,
                   result_summary, depends_on, requires_audit, audit_status,
                   slurm_job_id, slurm_output_file, retry_count
            FROM tasks
            WHERE id = ?
        ''', (task_id,))
        
        row = c.fetchone()
        if not row:
            return None
        
        details = None
        if row['details']:
            try:
                details = json.loads(row['details'])
            except:
                details = {'raw': row['details']}
        
        return Task(
            id=row['id'],
            project_id=row['project_id'],
            title=row['title'],
            description=row['description'],
            status=row['status'],
            priority=row['priority'],
            details=details,
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            start_time=row['start_time'],
            end_time=row['end_time'],
            result_summary=row['result_summary'],
            depends_on=row['depends_on'],
            requires_audit=row['requires_audit'],
            audit_status=row['audit_status'],
            slurm_job_id=row['slurm_job_id'],
            slurm_output_file=row['slurm_output_file'],
            retry_count=row['retry_count'] or 0
        )


class SimulatedSlurmManager:
    """模拟 SLURM 管理器 - 使用本地进程"""
    
    def __init__(self, output_dir: str = SIM_OUTPUT_DIR):
        self.output_dir = output_dir
        self.jobs = {}  # job_id -> process
    
    def submit_job(self, task: Task, script_content: str) -> Tuple[Optional[int], str]:
        """提交模拟作业"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_id = int(time.time() * 1000) % 1000000  # 生成唯一 ID
        
        script_file = os.path.join(self.output_dir, f"task_{task.id}_{job_id}.sh")
        output_file = os.path.join(self.output_dir, f"task_{task.id}_{job_id}.out")
        error_file = os.path.join(self.output_dir, f"task_{task.id}_{job_id}.err")
        
        # 创建执行脚本
        exec_script = f"""#!/bin/bash
echo "模拟 SLURM 作业 - 任务 {task.id}"
echo "开始时间：$(date)"
echo "任务标题：{task.title}"
echo ""

{script_content}

echo ""
echo "结束时间：$(date)"
echo "任务执行成功"
"""
        
        try:
            # 写入脚本
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(exec_script)
            
            os.chmod(script_file, 0o755)
            
            # 启动后台进程
            with open(output_file, 'w') as out, open(error_file, 'w') as err:
                process = subprocess.Popen(
                    ['bash', script_file],
                    stdout=out,
                    stderr=err,
                    cwd=self.output_dir
                )
            
            self.jobs[job_id] = {
                'process': process,
                'task_id': task.id,
                'output_file': output_file,
                'error_file': error_file,
                'start_time': datetime.now().isoformat()
            }
            
            logger.info(f"模拟作业 {job_id} 已提交 (任务 {task.id})")
            return job_id, ""
            
        except Exception as e:
            error_msg = f"提交失败：{str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def get_job_status(self, job_id: int) -> str:
        """获取作业状态"""
        if job_id not in self.jobs:
            return "COMPLETED"
        
        job_info = self.jobs[job_id]
        process = job_info['process']
        
        if process.poll() is None:
            return "RUNNING"
        else:
            return "COMPLETED"
    
    def get_job_output(self, task_id: int, job_id: int) -> Optional[str]:
        """获取作业输出"""
        if job_id in self.jobs:
            output_file = self.jobs[job_id]['output_file']
            if os.path.exists(output_file):
                with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
        return None
    
    def parse_job_result(self, output: str) -> Dict[str, Any]:
        """解析作业结果"""
        result = {'success': False, 'summary': '', 'metrics': {}}
        
        if not output:
            result['summary'] = '无输出'
            return result
        
        if '任务执行成功' in output or 'Completed successfully' in output:
            result['success'] = True
        
        # 提取最后几行作为摘要
        lines = output.strip().split('\n')
        result['summary'] = '\n'.join(lines[-5:])
        
        return result


class SimulatedExecutor:
    """模拟执行器"""
    
    def __init__(self, db: SimulatedDatabase, slurm: SimulatedSlurmManager):
        self.db = db
        self.slurm = slurm
        self.max_retries = 3
    
    def generate_script(self, task: Task) -> str:
        """生成执行脚本"""
        if not task.details:
            return f"""
echo "执行默认任务"
echo "任务：{task.title}"
sleep 5
echo "任务执行成功"
"""
        
        task_type = task.details.get('type', 'default')
        
        if task_type == 'psi4_calculation':
            return self._generate_psi4_script(task)
        elif task_type == 'data_processing':
            return self._generate_data_script(task)
        elif task_type == 'custom_script':
            return task.details.get('script', '')
        else:
            return self._generate_default_script(task)
    
    def _generate_psi4_script(self, task: Task) -> str:
        config = task.details.get('config', {})
        method = config.get('method', 'B3LYP')
        basis = config.get('basis', '6-31G(d)')
        geometry = task.details.get('geometry', '')
        
        return f"""
echo "PSI4 计算模拟"
echo "方法：{method}"
echo "基组：{basis}"
echo ""
echo "分子几何:"
echo "{geometry}"
echo ""
sleep 3
echo ""
echo "SCF 计算完成"
echo "Total energy: -76.3745987"
echo "任务执行成功"
"""
    
    def _generate_data_script(self, task: Task) -> str:
        return f"""
echo "数据处理模拟"
echo "输入：{task.details.get('input_file', 'N/A')}"
sleep 2
echo "处理完成"
echo "任务执行成功"
"""
    
    def _generate_default_script(self, task: Task) -> str:
        return f"""
echo "执行任务：{task.title}"
echo "描述：{task.description}"
sleep 2
echo "任务执行成功"
"""
    
    def execute_task(self, task: Task) -> bool:
        """执行任务"""
        logger.info(f"开始执行任务 {task.id}: {task.title}")
        
        try:
            self.db.update_task_status(task.id, TaskStatus.IN_PROGRESS.value)
            script_content = self.generate_script(task)
            
            job_id, error_msg = self.slurm.submit_job(task, script_content)
            
            if job_id:
                output_file = self.slurm.jobs[job_id]['output_file']
                self.db.update_task_status(
                    task.id, 
                    TaskStatus.SUBMITTED.value,
                    slurm_job_id=job_id,
                    slurm_output_file=output_file
                )
                logger.info(f"任务 {task.id} 已提交，作业 ID: {job_id}")
                return True
            else:
                retry_count = task.retry_count + 1
                if retry_count < self.max_retries:
                    logger.warning(f"任务 {task.id} 提交失败，第 {retry_count} 次重试")
                    self.db.update_task_status(
                        task.id, 
                        TaskStatus.RETRYING.value,
                        error_message=error_msg
                    )
                    time.sleep(2 * retry_count)
                    return self.execute_task(task)
                else:
                    logger.error(f"任务 {task.id} 提交失败，已达最大重试次数")
                    self.db.update_task_status(
                        task.id, 
                        TaskStatus.FAILED.value,
                        error_message=error_msg
                    )
                    return False
                    
        except Exception as e:
            logger.error(f"执行任务 {task.id} 异常：{e}")
            self.db.update_task_status(
                task.id, 
                TaskStatus.FAILED.value,
                error_message=f"执行异常：{str(e)}"
            )
            return False


class SimulatedMonitor:
    """模拟监控器"""
    
    def __init__(self, db: SimulatedDatabase, slurm: SimulatedSlurmManager, executor: SimulatedExecutor):
        self.db = db
        self.slurm = slurm
        self.executor = executor
    
    def check_submitted_tasks(self):
        """检查已提交的任务"""
        conn = self.db._get_connection()
        c = conn.cursor()
        
        c.execute("PRAGMA table_info(tasks)")
        columns = [col[1] for col in c.fetchall()]
        
        if 'slurm_job_id' not in columns:
            return
        
        c.execute('''
            SELECT id, slurm_job_id FROM tasks
            WHERE status IN ('submitted', 'running')
        ''')
        
        for row in c.fetchall():
            task_id = row['id']
            job_id = row['slurm_job_id']
            
            if not job_id:
                continue
            
            slurm_status = self.slurm.get_job_status(job_id)
            
            if slurm_status == "RUNNING":
                new_status = TaskStatus.RUNNING.value
            elif slurm_status == "COMPLETED":
                new_status = TaskStatus.COMPLETED.value
                self._process_completed_task(task_id, job_id)
            else:
                new_status = TaskStatus.COMPLETED.value
                self._process_completed_task(task_id, job_id)
            
            self.db.update_task_status(task_id, new_status)
    
    def _process_completed_task(self, task_id: int, job_id: int):
        """处理完成的任务"""
        logger.info(f"处理完成的任务 {task_id}")
        
        output = self.slurm.get_job_output(task_id, job_id)
        result = self.slurm.parse_job_result(output) if output else {'success': True, 'summary': '完成'}
        
        self.db.update_task_status(
            task_id,
            TaskStatus.COMPLETED.value,
            result_summary=result.get('summary', '任务完成')
        )
        
        logger.info(f"任务 {task_id} 处理完成：{result.get('summary', '')[:100]}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='T109 任务轮询服务 - 模拟模式')
    parser.add_argument('--start', action='store_true', help='启动服务')
    parser.add_argument('--once', action='store_true', help='执行一轮')
    parser.add_argument('--interval', type=int, default=10, help='轮询间隔（秒）')
    
    args = parser.parse_args()
    
    db = SimulatedDatabase()
    slurm = SimulatedSlurmManager()
    executor = SimulatedExecutor(db, slurm)
    monitor = SimulatedMonitor(db, slurm, executor)
    
    if args.start:
        logger.info("=" * 60)
        logger.info("T109 MacMini 任务轮询服务 - 模拟模式")
        logger.info("=" * 60)
        
        running = True
        
        def signal_handler(signum, frame):
            nonlocal running
            logger.info("收到停止信号")
            running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        while running:
            monitor.check_submitted_tasks()
            
            pending_tasks = db.get_pending_tasks(limit=5)
            if pending_tasks:
                logger.info(f"发现 {len(pending_tasks)} 个待处理任务")
                for task in pending_tasks:
                    executor.execute_task(task)
            else:
                logger.debug("暂无待处理任务")
            
            time.sleep(args.interval)
        
        logger.info("服务已停止")
    
    elif args.once:
        logger.info("执行单轮任务处理（模拟模式）")
        
        monitor.check_submitted_tasks()
        
        pending_tasks = db.get_pending_tasks(limit=5)
        if pending_tasks:
            logger.info(f"发现 {len(pending_tasks)} 个待处理任务")
            for task in pending_tasks:
                success = executor.execute_task(task)
                logger.info(f"任务 {task.id}: {'成功' if success else '失败'}")
        else:
            logger.info("暂无待处理任务")
        
        # 等待几秒让模拟作业完成
        logger.info("等待作业完成...")
        time.sleep(5)
        
        # 再次检查状态
        monitor.check_submitted_tasks()
        
        logger.info("单轮执行完成")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

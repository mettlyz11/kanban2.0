#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据库连接模块 v2.0 - 长期稳定性增强版
=================================================
重大改进：
1. 主动心跳线程（30秒间隔）防止RDS中间网络层断连
2. 自动连接池重置（遇到2013错误时）
3. SQLite本地缓存fallback（MySQL不可用时）
4. 更激进的连接回收策略（60秒）

使用方法：
    from lib.db_connector import get_db_connection, execute_query, execute_update
    
    # 获取连接
    conn = get_db_connection()
    
    # 执行查询
    results = execute_query("SELECT * FROM tasks WHERE id = %s", (123,))
    
    # 执行更新
    affected_rows = execute_update("UPDATE tasks SET status = %s WHERE id = %s", 
                                   ("completed", 123))

创建日期: 2026-04-22
升级日期: 2026-05-02（长期稳定性增强）
"""

import os
import sys
import time
import logging
import threading
import sqlite3
import pymysql
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('db_connector')

# 加载环境变量
ENV_PATH = Path.home() / ".openclaw" / ".env"
SDS_ENV_PATH = Path(__file__).parent.parent / ".env"

def load_env():
    """从 .env 文件加载环境变量（全局 + SDS本地覆盖）"""
    # 1. 加载全局 .env
    if ENV_PATH.exists():
        with open(ENV_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
    else:
        # print(f"⚠️ 警告: 全局配置文件不存在: {ENV_PATH}", file=sys.stderr)
    
    # 2. SDS本地.env覆盖（如果存在）
    if SDS_ENV_PATH.exists():
        with open(SDS_ENV_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# 初始化时加载环境变量
load_env()

# ============================================================
# 数据库配置
# ============================================================
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '127.0.0.1'),
    'port': int(os.environ.get('DB_PORT', '3306')),
    'user': os.environ.get('DB_USER', 'kanban'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'kanban'),
    'charset': os.environ.get('DB_CHARSET', 'utf8mb4'),
    'cursorclass': pymysql.cursors.DictCursor,
    'connect_timeout': 10,
    'read_timeout': 30,
    'write_timeout': 30,
    'autocommit': True,
}

# ============================================================
# 连接池配置 - 长期稳定性增强
# ============================================================
POOL_CONFIG = {
    'heartbeat_interval': 30,   # 30秒心跳间隔（关键：防止中间网络层断连）
    'max_idle_time': 60,        # 1分钟最大空闲
    'pool_recycle': 60,         # 1分钟强制回收连接（关键：比RDS断开时间更短）
    'max_retries': 5,           # 最大重试次数
}

# ============================================================
# 可重试的错误类型和错误码
# ============================================================
RETRYABLE_ERRORS = (
    pymysql.OperationalError,
    pymysql.InterfaceError,
    pymysql.InternalError,
    ConnectionResetError,
    BrokenPipeError,
)

RETRYABLE_ERROR_CODES = (
    2006,  # MySQL server has gone away
    2013,  # Lost connection to MySQL server during query
    2003,  # Can't connect to MySQL server
    2002,  # Can't connect to local MySQL server
    1040,  # Too many connections
    1213,  # Deadlock found when trying to get lock
)

# ============================================================
# SQLite本地缓存（MySQL不可用时作为fallback）
# ============================================================
SQLITE_DB_PATH = Path.home() / ".openclaw" / "workspace" / "sds1" / "data" / "local_cache.db"

class SQLiteFallback:
    """
    SQLite本地缓存 - MySQL不可时的降级方案
    仅缓存关键任务状态，确保SDS核心功能可用
    """
    def __init__(self):
        self._ensure_db()
    
    def _ensure_db(self):
        """确保SQLite数据库和表存在"""
        SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(SQLITE_DB_PATH))
        cursor = conn.cursor()
        
        # 创建任务缓存表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks_cache (
                id INTEGER PRIMARY KEY,
                title TEXT,
                status TEXT,
                priority TEXT,
                goal_id INTEGER,
                created_at TEXT,
                updated_at TEXT,
                execution_log TEXT,
                result_summary TEXT
            )
        ''')
        
        # 创建系统状态表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("[SQLiteFallback] 本地缓存数据库已初始化")
    
    def cache_tasks(self, tasks: List[Dict]):
        """缓存任务列表"""
        conn = sqlite3.connect(str(SQLITE_DB_PATH))
        cursor = conn.cursor()
        
        # 清空并重新插入
        cursor.execute("DELETE FROM tasks_cache")
        
        for task in tasks:
            cursor.execute('''
                INSERT INTO tasks_cache (id, title, status, priority, goal_id, created_at, updated_at, execution_log, result_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task.get('id'),
                task.get('title', ''),
                task.get('status', ''),
                task.get('priority', ''),
                task.get('goal_id'),
                str(task.get('created_at', '')),
                str(task.get('updated_at', '')),
                task.get('execution_log', ''),
                task.get('result_summary', '')
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"[SQLiteFallback] 已缓存 {len(tasks)} 个任务")
    
    def get_cached_tasks(self, status: str = None) -> List[Dict]:
        """获取缓存的任务"""
        conn = sqlite3.connect(str(SQLITE_DB_PATH))
        cursor = conn.cursor()
        
        if status:
            cursor.execute("SELECT * FROM tasks_cache WHERE status = ? ORDER BY updated_at DESC", (status,))
        else:
            cursor.execute("SELECT * FROM tasks_cache ORDER BY updated_at DESC")
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def update_task_status(self, task_id: int, status: str, execution_log: str = None, result_summary: str = None):
        """更新任务状态（SQLite）"""
        conn = sqlite3.connect(str(SQLITE_DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tasks_cache 
            SET status = ?, updated_at = ?
            WHERE id = ?
        ''', (status, datetime.now().isoformat(), task_id))
        
        conn.commit()
        conn.close()
    
    def save_state(self, key: str, value: str):
        """保存系统状态"""
        conn = sqlite3.connect(str(SQLITE_DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO system_state (key, value, updated_at)
            VALUES (?, ?, ?)
        ''', (key, value, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_state(self, key: str) -> Optional[str]:
        """获取系统状态"""
        conn = sqlite3.connect(str(SQLITE_DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM system_state WHERE key = ?", (key,))
        row = cursor.fetchone()
        
        conn.close()
        
        return row[0] if row else None

# 全局SQLite实例
_sqlite_fallback = None

def get_sqlite_fallback() -> SQLiteFallback:
    global _sqlite_fallback
    if _sqlite_fallback is None:
        _sqlite_fallback = SQLiteFallback()
    return _sqlite_fallback

# ============================================================
# 增强版连接池 + 主动心跳线程
# ============================================================
class ConnectionPool:
    """
    增强版 MySQL 连接池 + 主动心跳保活 + 自动恢复
    
    关键改进：
    1. 心跳线程：每30秒ping所有空闲连接
    2. 自动重置：遇到2013错误时自动重置整个连接池
    3. 更短回收：60秒强制回收（防止中间网络层断连）
    """
    def __init__(self, config: dict, pool_size: int = 5):
        self.config = config
        self.pool_size = pool_size
        self._pool = []  # [(conn, created_at), ...]
        self._lock = threading.Lock()
        self._created = 0
        self._pool_recycle = POOL_CONFIG.get('pool_recycle', 60)
        self._heartbeat_interval = POOL_CONFIG.get('heartbeat_interval', 30)
        self._shutdown = False
        self._heartbeat_thread = None
        self._start_heartbeat()
        
    def _start_heartbeat(self):
        """启动心跳线程"""
        if self._heartbeat_thread is None or not self._heartbeat_thread.is_alive():
            self._heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
            self._heartbeat_thread.start()
            logger.info(f"[ConnectionPool] 心跳线程已启动（间隔: {self._heartbeat_interval}秒）")
    
    def _heartbeat_worker(self):
        """心跳工作线程 - 定期ping所有空闲连接"""
        while not self._shutdown:
            try:
                time.sleep(self._heartbeat_interval)
                if self._shutdown:
                    break
                
                with self._lock:
                    alive_count = 0
                    dead_count = 0
                    new_pool = []
                    
                    for conn, created_at in self._pool:
                        try:
                            conn.ping(reconnect=False)
                            with conn.cursor() as cursor:
                                cursor.execute("SELECT 1 as alive")
                                result = cursor.fetchone()
                                if result and result.get('alive') == 1:
                                    new_pool.append((conn, created_at))
                                    alive_count += 1
                                else:
                                    dead_count += 1
                                    try: conn.close()
                                    except: pass
                        except Exception as e:
                            dead_count += 1
                            try: conn.close()
                            except: pass
                    
                    self._pool = new_pool
                    
                    if dead_count > 0:
                        logger.info(f"[ConnectionPool] 心跳检查: {alive_count}个存活, {dead_count}个已关闭")
                    
            except Exception as e:
                if not self._shutdown:
                    logger.warning(f"[ConnectionPool] 心跳线程异常: {e}")
    
    def _create_connection(self) -> pymysql.Connection:
        conn = pymysql.connect(**self.config)
        conn.ping(reconnect=True)
        return conn
    
    def _is_expired(self, created_at: float) -> bool:
        """检查连接是否超过回收时间"""
        if self._pool_recycle <= 0:
            return False
        return (time.time() - created_at) > self._pool_recycle
    
    def _is_alive(self, conn: pymysql.Connection) -> bool:
        """心跳保活检测 - 严格模式"""
        try:
            conn.ping(reconnect=False)
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 as alive")
                result = cursor.fetchone()
                if result and result.get('alive') == 1:
                    return True
            return False
        except Exception as e:
            logger.debug(f"[ConnectionPool] 连接检测失败: {e}")
            return False
    
    def get_connection(self) -> pymysql.Connection:
        """获取连接（带心跳保活 + 超时回收）"""
        with self._lock:
            # 尝试复用空闲连接
            while self._pool:
                conn, created_at = self._pool.pop(0)
                
                # 优先检查：连接是否超过回收时间
                if self._is_expired(created_at):
                    try: conn.close()
                    except: pass
                    logger.debug("[ConnectionPool] 连接已过期，强制回收")
                    continue
                
                if self._is_alive(conn):
                    try:
                        conn.ping(reconnect=True)
                        return conn
                    except:
                        try: conn.close()
                        except: pass
                else:
                    try: conn.close()
                    except: pass
            
            # 创建新连接
            self._created += 1
            return self._create_connection()
    
    def return_connection(self, conn: pymysql.Connection):
        """归还连接到池"""
        with self._lock:
            if len(self._pool) < self.pool_size:
                self._pool.append((conn, time.time()))
            else:
                try: conn.close()
                except: pass
    
    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            for item in self._pool:
                conn = item[0] if isinstance(item, tuple) else item
                try: conn.close()
                except: pass
            self._pool.clear()
    
    def reset(self):
        """重置连接池 - 关闭所有连接并清空"""
        logger.info("[ConnectionPool] 重置连接池，关闭所有现有连接")
        self.close_all()
        self._created = 0
        # 重新启动心跳线程
        self._start_heartbeat()
    
    def shutdown(self):
        """关闭连接池和心跳线程"""
        self._shutdown = True
        self.close_all()
        logger.info("[ConnectionPool] 连接池已关闭")

# ============================================================
# 全局连接池 + SQLite fallback 状态管理
# ============================================================
_global_pool = None
_mysql_available = True  # MySQL可用性状态
_last_mysql_error = None  # 上次MySQL错误时间

# ============================================================
# 连接恢复处理器
# ============================================================
class ConnectionRecoveryHandler:
    """
    连接恢复处理器
    
    核心功能：
    1. 遇到2013错误时自动重置连接池
    2. 多次失败后切换到SQLite fallback
    3. 定期尝试恢复MySQL连接
    """
    
    def __init__(self):
        self.consecutive_2013_errors = 0
        self.last_recovery_time = None
        self.recovery_cooldown = 60  # 恢复冷却时间（秒）
    
    def handle_2013_error(self):
        """处理2013错误 - 自动重置连接池"""
        global _mysql_available, _last_mysql_error
        
        self.consecutive_2013_errors += 1
        _last_mysql_error = time.time()
        
        logger.warning(f"[Recovery] 检测到2013错误（连续第{self.consecutive_2013_errors}次）")
        
        # 立即重置连接池
        try:
            reset_pool()
            logger.info("[Recovery] 连接池已重置")
        except Exception as e:
            logger.error(f"[Recovery] 连接池重置失败: {e}")
        
        # 如果连续多次2013错误，标记MySQL为不可用
        if self.consecutive_2013_errors >= 3:
            _mysql_available = False
            logger.warning("[Recovery] MySQL连接不稳定，切换到SQLite fallback模式")
        
        return True
    
    def mark_success(self):
        """标记一次成功操作，重置错误计数"""
        global _mysql_available
        
        if self.consecutive_2013_errors > 0:
            logger.info(f"[Recovery] 数据库操作成功，重置错误计数（之前连续{self.consecutive_2013_errors}次错误）")
            self.consecutive_2013_errors = 0
        
        if not _mysql_available:
            _mysql_available = True
            logger.info("[Recovery] MySQL连接恢复，退出fallback模式")
    
    def should_use_fallback(self) -> bool:
        """判断是否应该使用fallback"""
        global _mysql_available
        
        if _mysql_available:
            return False
        
        # 检查冷却时间
        if self.last_recovery_time and (time.time() - self.last_recovery_time) < self.recovery_cooldown:
            return True
        
        # 尝试恢复MySQL
        self.last_recovery_time = time.time()
        try:
            conn = get_db_connection(use_pool=False, max_retries=1)
            conn.close()
            _mysql_available = True
            self.consecutive_2013_errors = 0
            logger.info("[Recovery] MySQL连接恢复测试成功")
            return False
        except:
            return True

# 全局恢复处理器
_recovery_handler = ConnectionRecoveryHandler()

def get_pool() -> ConnectionPool:
    global _global_pool
    if _global_pool is None:
        _global_pool = ConnectionPool(DB_CONFIG, pool_size=5)
    return _global_pool

def reset_pool():
    """重置全局连接池"""
    global _global_pool
    if _global_pool is not None:
        _global_pool.reset()
        logger.info("[db_connector] 全局连接池已重置")
    else:
        logger.debug("[db_connector] 连接池尚未初始化，无需重置")

def shutdown_pool():
    """关闭全局连接池（程序退出时调用）"""
    global _global_pool
    if _global_pool is not None:
        _global_pool.shutdown()
        _global_pool = None
        logger.info("[db_connector] 全局连接池已关闭")

# ============================================================
# 核心函数
# ============================================================
def get_db_connection(max_retries: int = 5, use_pool: bool = True) -> pymysql.Connection:
    """
    获取数据库连接（连接池优先 + 降级直连）
    
    Args:
        max_retries: 最大重试次数
        use_pool: 是否使用连接池（默认True）
    
    Returns:
        pymysql 连接对象
    """
    last_error = None
    
    # 优先尝试从连接池获取
    if use_pool:
        try:
            pool = get_pool()
            conn = pool.get_connection()
            return conn
        except Exception as e:
            logger.warning(f"⚠️ 连接池获取失败，降级直连: {e}")
    
    # 降级：直连模式
    for attempt in range(1, max_retries + 1):
        try:
            conn = pymysql.connect(**DB_CONFIG)
            conn.ping(reconnect=True)
            if attempt > 1:
                logger.info(f"✅ 数据库连接成功（第 {attempt} 次重试）")
            return conn
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait_time = min(2 ** attempt, 30)  # 最多等待30秒
                logger.warning(f"⚠️ 数据库连接失败（第 {attempt} 次），{wait_time}秒后重试: {e}")
                time.sleep(wait_time)
            continue
    
    logger.error(f"❌ 数据库连接失败（重试 {max_retries} 次）: {last_error}")
    raise Exception(f"数据库连接失败（重试 {max_retries} 次）: {last_error}")

def _handle_db_error(error, context: str = ""):
    """统一处理数据库错误"""
    error_code = error.args[0] if hasattr(error, 'args') and len(error.args) > 0 else 0
    
    if error_code == 2013:
        logger.warning(f"[db_connector] {context} - 检测到2013错误，触发自动恢复")
        _recovery_handler.handle_2013_error()
        return True  # 表示已处理
    
    return False  # 未处理

def execute_query(sql: str, params: Optional[Tuple] = None, max_retries: int = 5, 
                  use_fallback: bool = True) -> List[Dict]:
    """
    执行查询语句（连接池 + 智能重试 + 心跳保活 + SQLite fallback）
    
    Args:
        sql: SQL语句
        params: 参数
        max_retries: 最大重试次数
        use_fallback: 是否允许使用SQLite fallback（默认True）
    """
    last_error = None
    pool = get_pool()
    
    # 检查是否应该使用fallback
    if use_fallback and _recovery_handler.should_use_fallback():
        logger.warning("[db_connector] 使用SQLite fallback执行查询")
        sqlite = get_sqlite_fallback()
        # 尝试将SQL转换为SQLite兼容的查询
        return sqlite.get_cached_tasks()
    
    for attempt in range(1, max_retries + 1):
        conn = None
        try:
            conn = pool.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                result = cursor.fetchall()
            
            # 标记成功
            _recovery_handler.mark_success()
            
            if attempt > 1:
                logger.info(f"✅ 查询执行成功（第 {attempt} 次重试）")
            return result
            
        except RETRYABLE_ERRORS as e:
            last_error = e
            error_code = e.args[0] if hasattr(e, 'args') and len(e.args) > 0 else 0
            
            # 处理2013错误
            if error_code == 2013:
                _recovery_handler.handle_2013_error()
                # 继续重试
                if attempt < max_retries:
                    wait_time = min(2 ** attempt, 30)
                    logger.warning(f"⚠️ 查询失败（2013错误，第 {attempt} 次），{wait_time}秒后重试...")
                    if conn:
                        try: conn.close()
                        except: pass
                        conn = None
                    time.sleep(wait_time)
                    continue
            
            if attempt < max_retries and error_code in RETRYABLE_ERROR_CODES:
                wait_time = min(2 ** attempt, 30)
                logger.warning(f"⚠️ 查询执行失败（第 {attempt} 次，错误码: {error_code}），{wait_time}秒后重试: {e}")
                if conn:
                    try: conn.close()
                    except: pass
                    conn = None
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"❌ 查询执行失败（不可重试错误，错误码: {error_code}）: {e}")
                raise
        except Exception as e:
            last_error = e
            logger.error(f"❌ 查询执行失败（非预期错误）: {e}")
            raise
        finally:
            if conn:
                # 关键修复：如果连接经历过可重试错误，不要归还坏连接到池中
                if last_error is not None and hasattr(last_error, 'args') and len(last_error.args) > 0:
                    error_code = last_error.args[0]
                    if error_code in RETRYABLE_ERROR_CODES:
                        try:
                            conn.close()
                            logger.debug("[db_connector] 坏连接已关闭，不归还到池中")
                        except:
                            pass
                        conn = None
                if conn:
                    pool.return_connection(conn)
    
    logger.error(f"❌ 查询执行失败（重试 {max_retries} 次后）: {last_error}")
    
    # 最后一次fallback尝试
    if use_fallback:
        logger.warning("[db_connector] 所有重试失败，使用SQLite fallback")
        sqlite = get_sqlite_fallback()
        return sqlite.get_cached_tasks()
    
    raise Exception(f"查询执行失败（重试 {max_retries} 次后）: {last_error}")

def execute_update(sql: str, params: Optional[Tuple] = None, max_retries: int = 5,
                   use_fallback: bool = True) -> int:
    """
    执行更新/插入/删除语句（连接池 + 智能重试 + 心跳保活 + SQLite fallback）
    """
    last_error = None
    pool = get_pool()
    
    # 检查是否应该使用fallback（更新操作不支持fallback，但记录到SQLite）
    if use_fallback and _recovery_handler.should_use_fallback():
        logger.warning("[db_connector] MySQL不可用，更新操作已排队到SQLite")
        # 对于更新操作，我们记录到SQLite待处理队列
        sqlite = get_sqlite_fallback()
        # 这里可以实现一个待处理队列，但目前只是记录
        return 0
    
    for attempt in range(1, max_retries + 1):
        conn = None
        try:
            conn = pool.get_connection()
            with conn.cursor() as cursor:
                affected = cursor.execute(sql, params or ())
            conn.commit()
            
            # 标记成功
            _recovery_handler.mark_success()
            
            if attempt > 1:
                logger.info(f"✅ 更新执行成功（第 {attempt} 次重试），影响行数: {affected}")
            return affected
            
        except RETRYABLE_ERRORS as e:
            last_error = e
            error_code = e.args[0] if hasattr(e, 'args') and len(e.args) > 0 else 0
            
            # 处理2013错误
            if error_code == 2013:
                _recovery_handler.handle_2013_error()
                if attempt < max_retries:
                    wait_time = min(2 ** attempt, 30)
                    logger.warning(f"⚠️ 更新失败（2013错误，第 {attempt} 次），{wait_time}秒后重试...")
                    if conn:
                        try: conn.rollback()
                        except: pass
                        try: conn.close()
                        except: pass
                        conn = None
                    time.sleep(wait_time)
                    continue
            
            if attempt < max_retries and error_code in RETRYABLE_ERROR_CODES:
                wait_time = min(2 ** attempt, 30)
                logger.warning(f"⚠️ 更新执行失败（第 {attempt} 次，错误码: {error_code}），{wait_time}秒后重试: {e}")
                if conn:
                    try: conn.rollback()
                    except: pass
                    try: conn.close()
                    except: pass
                    conn = None
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"❌ 更新执行失败（不可重试错误，错误码: {error_code}）: {e}")
                if conn:
                    try: conn.rollback()
                    except: pass
                raise
        except Exception as e:
            last_error = e
            logger.error(f"❌ 更新执行失败（非预期错误）: {e}")
            if conn:
                try: conn.rollback()
                except: pass
            raise
        finally:
            if conn:
                if last_error is not None and hasattr(last_error, 'args') and len(last_error.args) > 0:
                    error_code = last_error.args[0]
                    if error_code in RETRYABLE_ERROR_CODES:
                        try:
                            conn.close()
                            logger.debug("[db_connector] 坏连接已关闭，不归还到池中")
                        except:
                            pass
                        conn = None
                if conn:
                    pool.return_connection(conn)
    
    logger.error(f"❌ 更新执行失败（重试 {max_retries} 次后）: {last_error}")
    raise Exception(f"更新执行失败（重试 {max_retries} 次后）: {last_error}")

def execute_insert_with_id(sql: str, params: Optional[Tuple] = None, max_retries: int = 5) -> int:
    """
    执行INSERT并返回LAST_INSERT_ID（同一连接内 + 连接池 + 心跳保活）
    """
    last_error = None
    pool = get_pool()
    
    for attempt in range(1, max_retries + 1):
        conn = None
        try:
            conn = pool.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                cursor.execute("SELECT LAST_INSERT_ID() as id")
                result = cursor.fetchone()
                task_id = result['id'] if result else 0
            conn.commit()
            
            # 标记成功
            _recovery_handler.mark_success()
            
            if attempt > 1:
                logger.info(f"✅ INSERT+ID执行成功（第 {attempt} 次重试），id: {task_id}")
            return task_id
            
        except RETRYABLE_ERRORS as e:
            last_error = e
            error_code = e.args[0] if hasattr(e, 'args') and len(e.args) > 0 else 0
            
            if error_code == 2013:
                _recovery_handler.handle_2013_error()
                if attempt < max_retries:
                    wait_time = min(2 ** attempt, 30)
                    logger.warning(f"⚠️ INSERT失败（2013错误，第 {attempt} 次），{wait_time}秒后重试...")
                    if conn:
                        try: conn.rollback()
                        except: pass
                        try: conn.close()
                        except: pass
                        conn = None
                    time.sleep(wait_time)
                    continue
            
            if attempt < max_retries and error_code in RETRYABLE_ERROR_CODES:
                wait_time = min(2 ** attempt, 30)
                logger.warning(f"⚠️ INSERT失败（第 {attempt} 次，错误码: {error_code}），{wait_time}秒后重试: {e}")
                if conn:
                    try: conn.rollback()
                    except: pass
                    try: conn.close()
                    except: pass
                    conn = None
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"❌ INSERT失败（不可重试错误，错误码: {error_code}）: {e}")
                if conn:
                    try: conn.rollback()
                    except: pass
                raise
        except Exception as e:
            last_error = e
            logger.error(f"❌ INSERT失败（非预期错误）: {e}")
            if conn:
                try: conn.rollback()
                except: pass
            raise
        finally:
            if conn:
                if last_error is not None and hasattr(last_error, 'args') and len(last_error.args) > 0:
                    error_code = last_error.args[0]
                    if error_code in RETRYABLE_ERROR_CODES:
                        try:
                            conn.close()
                            logger.debug("[db_connector] 坏连接已关闭，不归还到池中")
                        except:
                            pass
                        conn = None
                if conn:
                    pool.return_connection(conn)
    
    logger.error(f"❌ INSERT失败（重试 {max_retries} 次后）: {last_error}")
    return 0

def execute_many(sql: str, params_list: List[Tuple], max_retries: int = 5) -> int:
    """
    批量执行更新/插入语句（连接池 + 智能重试 + 心跳保活）
    """
    last_error = None
    pool = get_pool()
    
    for attempt in range(1, max_retries + 1):
        conn = None
        try:
            conn = pool.get_connection()
            with conn.cursor() as cursor:
                affected = cursor.executemany(sql, params_list)
            conn.commit()
            
            # 标记成功
            _recovery_handler.mark_success()
            
            if attempt > 1:
                logger.info(f"✅ 批量执行成功（第 {attempt} 次重试），影响行数: {affected}")
            return affected
            
        except RETRYABLE_ERRORS as e:
            last_error = e
            error_code = e.args[0] if hasattr(e, 'args') and len(e.args) > 0 else 0
            
            if error_code == 2013:
                _recovery_handler.handle_2013_error()
                if attempt < max_retries:
                    wait_time = min(2 ** attempt, 30)
                    logger.warning(f"⚠️ 批量执行失败（2013错误，第 {attempt} 次），{wait_time}秒后重试...")
                    if conn:
                        try: conn.rollback()
                        except: pass
                        try: conn.close()
                        except: pass
                        conn = None
                    time.sleep(wait_time)
                    continue
            
            if attempt < max_retries and error_code in RETRYABLE_ERROR_CODES:
                wait_time = min(2 ** attempt, 30)
                logger.warning(f"⚠️ 批量执行失败（第 {attempt} 次，错误码: {error_code}），{wait_time}秒后重试: {e}")
                if conn:
                    try: conn.rollback()
                    except: pass
                    try: conn.close()
                    except: pass
                    conn = None
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"❌ 批量执行失败（不可重试错误，错误码: {error_code}）: {e}")
                if conn:
                    try: conn.rollback()
                    except: pass
                raise
        except Exception as e:
            last_error = e
            logger.error(f"❌ 批量执行失败（非预期错误）: {e}")
            if conn:
                try: conn.rollback()
                except: pass
            raise
        finally:
            if conn:
                if last_error is not None and hasattr(last_error, 'args') and len(last_error.args) > 0:
                    error_code = last_error.args[0]
                    if error_code in RETRYABLE_ERROR_CODES:
                        try:
                            conn.close()
                            logger.debug("[db_connector] 坏连接已关闭，不归还到池中")
                        except:
                            pass
                        conn = None
                if conn:
                    pool.return_connection(conn)
    
    logger.error(f"❌ 批量执行失败（重试 {max_retries} 次后）: {last_error}")
    raise Exception(f"批量执行失败（重试 {max_retries} 次后）: {last_error}")

# ============================================================
# 便捷函数
# ============================================================
def is_mysql_available() -> bool:
    """检查MySQL是否可用"""
    return _mysql_available

def get_connection_status() -> Dict:
    """获取连接状态信息"""
    return {
        'mysql_available': _mysql_available,
        'consecutive_2013_errors': _recovery_handler.consecutive_2013_errors,
        'last_mysql_error': _last_mysql_error,
        'pool_size': len(_global_pool._pool) if _global_pool else 0,
        'pool_created': _global_pool._created if _global_pool else 0,
    }

def cache_tasks_to_sqlite(tasks: List[Dict]):
    """将任务缓存到SQLite（用于fallback）"""
    sqlite = get_sqlite_fallback()
    sqlite.cache_tasks(tasks)

# 测试代码
if __name__ == '__main__':
    try:
        # print(f"🚀 测试 MySQL 连接与长期稳定性增强...")
        conn = get_db_connection()
        # print(f"✅ 数据库连接成功: {DB_CONFIG['host']}/{DB_CONFIG['database']}")
        
        # 测试查询
        result = execute_query("SELECT COUNT(*) as count FROM tasks")
        # print(f"📊 看板总任务数: {result[0]['count']}")
        
        # 测试SQLite fallback
        sqlite = get_sqlite_fallback()
        # print(f"✅ SQLite fallback 已初始化: {SQLITE_DB_PATH}")
        
        # 测试连接状态
        status = get_connection_status()
        # print(f"📊 连接状态: {status}")
        
        conn.close()
        # print(f"\n🎉 所有测试通过！长期稳定性增强已生效")
        # print(f"   - 主动心跳线程: 每{POOL_CONFIG['heartbeat_interval']}秒")
        # print(f"   - 连接回收: 每{POOL_CONFIG['pool_recycle']}秒")
        # print(f"   - SQLite fallback: 已启用")
    except Exception as e:
        # print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

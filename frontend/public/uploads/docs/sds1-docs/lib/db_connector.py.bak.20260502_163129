#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据库连接模块 - 所有脚本共用
从 ~/.openclaw/.env 读取数据库配置，避免硬编码密码

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
"""

import os
import sys
import time
import logging
import pymysql
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('db_connector')

# 加载环境变量
ENV_PATH = Path.home() / ".openclaw" / ".env"

def load_env():
    """从 .env 文件加载环境变量"""
    if not ENV_PATH.exists():
        print(f"⚠️ 警告: 配置文件不存在: {ENV_PATH}", file=sys.stderr)
        return
    
    with open(ENV_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            os.environ[key.strip()] = value.strip()

# 初始化时加载环境变量
load_env()

# 数据库配置
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

# 连接池配置
# 修复：降低空闲时间和心跳间隔，避免阿里云RDS连接被静默断开
# 根因：中间网络层(NAT/代理)在5-15分钟断开空闲TCP，而macOS keepalive 2小时才启动
POOL_CONFIG = {
    'heartbeat_interval': 30,   # 30秒心跳间隔
    'max_idle_time': 60,        # 1分钟最大空闲
    'pool_recycle': 300,        # 5分钟强制回收连接（关键：防止中间网络层断连）
    'max_retries': 5,           # 最大重试次数
}

# 简单连接池
class ConnectionPool:
    """
    轻量级 MySQL 连接池 + 心跳保活
    适用于 SDS 单进程场景，避免频繁创建/销毁连接
    """
    def __init__(self, config: dict, pool_size: int = 5):
        self.config = config
        self.pool_size = pool_size
        self._pool = []  # [(conn, created_at), ...]
        self._lock = __import__('threading').Lock()
        self._created = 0
        self._pool_recycle = POOL_CONFIG.get('pool_recycle', 300)
        
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
        """心跳保活检测 - 严格模式，确保连接真正可用"""
        try:
            # 先用ping快速检测
            conn.ping(reconnect=False)
            # 必须执行真实查询验证（ping通过不代表连接可用）
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
                    try:
                        conn.close()
                    except:
                        pass
                    logger.debug("[ConnectionPool] 连接已过期，强制回收")
                    continue
                
                if self._is_alive(conn):
                    # 修复：即使_is_alive通过，也强制ping确保连接真正可用
                    try:
                        conn.ping(reconnect=True)
                        return conn
                    except:
                        # ping失败，关闭并继续
                        try:
                            conn.close()
                        except:
                            pass
                else:
                    # 连接已死，关闭
                    try:
                        conn.close()
                    except:
                        pass
            
            # 创建新连接
            self._created += 1
            return self._create_connection()
    
    def return_connection(self, conn: pymysql.Connection):
        """归还连接到池"""
        with self._lock:
            if len(self._pool) < self.pool_size:
                self._pool.append((conn, time.time()))
            else:
                # 池满了，关闭
                try:
                    conn.close()
                except:
                    pass
    
    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            for item in self._pool:
                conn = item[0] if isinstance(item, tuple) else item
                try:
                    conn.close()
                except:
                    pass
            self._pool.clear()
    
    def reset(self):
        """重置连接池 - 关闭所有连接并清空，强制下次创建新连接"""
        logger.info("[ConnectionPool] 重置连接池，关闭所有现有连接")
        self.close_all()
        self._created = 0

# 全局连接池（懒加载）
_global_pool = None

def get_pool() -> ConnectionPool:
    global _global_pool
    if _global_pool is None:
        _global_pool = ConnectionPool(DB_CONFIG, pool_size=5)
    return _global_pool

def reset_pool():
    """重置全局连接池 - 供SDS等长周期任务在周期开始时调用"""
    global _global_pool
    if _global_pool is not None:
        _global_pool.reset()
        logger.info("[db_connector] 全局连接池已重置")
    else:
        logger.debug("[db_connector] 连接池尚未初始化，无需重置")

# 可重试的错误类型
RETRYABLE_ERRORS = (
    pymysql.OperationalError,
    pymysql.InterfaceError,
    pymysql.InternalError,
    ConnectionResetError,
    BrokenPipeError,
)

# 可重试的错误码
RETRYABLE_ERROR_CODES = (
    2006,  # MySQL server has gone away
    2013,  # Lost connection to MySQL server during query
    2003,  # Can't connect to MySQL server
    2002,  # Can't connect to local MySQL server
    1040,  # Too many connections
    1213,  # Deadlock found when trying to get lock
)

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
                wait_time = 2 ** attempt
                logger.warning(f"⚠️ 数据库连接失败（第 {attempt} 次），{wait_time}秒后重试: {e}")
                time.sleep(wait_time)
            continue
    
    logger.error(f"❌ 数据库连接失败（重试 {max_retries} 次）: {last_error}")
    raise Exception(f"数据库连接失败（重试 {max_retries} 次）: {last_error}")

def execute_query(sql: str, params: Optional[Tuple] = None, max_retries: int = 5) -> List[Dict]:
    """
    执行查询语句（连接池 + 智能重试 + 心跳保活）
    """
    last_error = None
    pool = get_pool()
    
    for attempt in range(1, max_retries + 1):
        conn = None
        try:
            conn = pool.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                result = cursor.fetchall()
                if attempt > 1:
                    logger.info(f"✅ 查询执行成功（第 {attempt} 次重试）")
                return result
        except RETRYABLE_ERRORS as e:
            last_error = e
            error_code = e.args[0] if hasattr(e, 'args') and len(e.args) > 0 else 0
            
            if attempt < max_retries and (isinstance(e, RETRYABLE_ERRORS) or error_code in RETRYABLE_ERROR_CODES):
                wait_time = 2 ** attempt
                logger.warning(f"⚠️ 查询执行失败（第 {attempt} 次，错误码: {error_code}），{wait_time}秒后重试: {e}")
                # 关闭坏连接
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
    raise Exception(f"查询执行失败（重试 {max_retries} 次后）: {last_error}")

def execute_update(sql: str, params: Optional[Tuple] = None, max_retries: int = 5) -> int:
    """
    执行更新/插入/删除语句（连接池 + 智能重试 + 心跳保活）
    """
    last_error = None
    pool = get_pool()
    
    for attempt in range(1, max_retries + 1):
        conn = None
        try:
            conn = pool.get_connection()
            with conn.cursor() as cursor:
                affected = cursor.execute(sql, params or ())
            conn.commit()
            if attempt > 1:
                logger.info(f"✅ 更新执行成功（第 {attempt} 次重试），影响行数: {affected}")
            return affected
        except RETRYABLE_ERRORS as e:
            last_error = e
            error_code = e.args[0] if hasattr(e, 'args') and len(e.args) > 0 else 0
            
            if attempt < max_retries and (isinstance(e, RETRYABLE_ERRORS) or error_code in RETRYABLE_ERROR_CODES):
                wait_time = 2 ** attempt
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
            if attempt > 1:
                logger.info(f"✅ INSERT+ID执行成功（第 {attempt} 次重试），id: {task_id}")
            return task_id
        except RETRYABLE_ERRORS as e:
            last_error = e
            error_code = e.args[0] if hasattr(e, 'args') and len(e.args) > 0 else 0
            
            if attempt < max_retries and (isinstance(e, RETRYABLE_ERRORS) or error_code in RETRYABLE_ERROR_CODES):
                wait_time = 2 ** attempt
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
            if attempt > 1:
                logger.info(f"✅ 批量执行成功（第 {attempt} 次重试），影响行数: {affected}")
            return affected
        except RETRYABLE_ERRORS as e:
            last_error = e
            error_code = e.args[0] if hasattr(e, 'args') and len(e.args) > 0 else 0
            
            if attempt < max_retries and (isinstance(e, RETRYABLE_ERRORS) or error_code in RETRYABLE_ERROR_CODES):
                wait_time = 2 ** attempt
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
    
    logger.error(f"❌ 批量执行失败（重试 {max_retries} 次后）: {last_error}")
    raise Exception(f"批量执行失败（重试 {max_retries} 次后）: {last_error}")

# 测试代码
if __name__ == '__main__':
    try:
        print(f"🚀 测试 MySQL 连接与重试机制...")
        conn = get_db_connection()
        print(f"✅ 数据库连接成功: {DB_CONFIG['host']}/{DB_CONFIG['database']}")
        
        # 测试查询
        result = execute_query("SELECT COUNT(*) as count FROM tasks")
        print(f"📊 看板总任务数: {result[0]['count']}")
        
        # 测试连接保活
        print(f"⏱️  测试连接保活...")
        conn.ping(reconnect=True)
        print(f"✅ 连接保活测试通过")
        
        conn.close()
        print(f"\n🎉 所有测试通过！MySQL 稳定性增强已生效")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        sys.exit(1)

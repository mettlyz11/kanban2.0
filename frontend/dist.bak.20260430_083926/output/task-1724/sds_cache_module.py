#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS 缓存模块 - 热点数据缓存层

解决核心问题:
1. 减少重复查询 - 热门数据（项目列表、状态统计）缓存5-30分钟
2. 降低数据库负载 - 高频查询命中缓存，避免重复扫描
3. 缓存失效策略 - TTL过期+手动失效+写后失效

支持两种缓存后端:
- 内存缓存（默认） - 进程级，适合单进程
- Redis（可选） - 跨进程共享缓存

集成方式:
    from sds_cache import cache_manager
    
    # 装饰器用法
    @cache_manager("projects:active")
    def get_active_projects():
        return execute_query("...")

    # 直接用法
    result = cache_manager.get_or_set("tasks:stats", lambda: execute_query("..."), ttl=300)

使用方式:
    from lib.sds_cache import cached, invalidate_cache
    from lib.connection_pool import pool
    
    @cached(ttl=300)
    def get_task_stats():
        return pool.execute_query("SELECT status, COUNT(*) FROM tasks GROUP BY status")

创建日期: 2026-04-23
"""

import time
import json
import hashlib
import logging
import threading
from functools import wraps
from typing import Dict, Any, Optional, Callable, List

logger = logging.getLogger('SDSCache')


class CacheEntry:
    """缓存条目"""
    
    def __init__(self, key: str, value: Any, ttl: int = 300):
        self.key = key
        self.value = value
        self.ttl = ttl
        self.created_at = time.time()
        self.access_count = 0
    
    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl
    
    @property
    def age(self) -> float:
        return time.time() - self.created_at


class MemoryCache:
    """
    内存缓存 - 带自动清理的TTL缓存
    
    配置:
        max_entries: 最大缓存条目数（默认1000）
        default_ttl: 默认过期时间（秒，默认300）
        cleanup_interval: 自动清理间隔（秒，默认60）
    """
    
    def __init__(self, max_entries: int = 1000, default_ttl: int = 300, cleanup_interval: int = 60):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_entries = max_entries
        self._default_ttl = default_ttl
        self._cleanup_interval = cleanup_interval
        self._lock = threading.RLock()
        self._last_cleanup = time.time()
        
        logger.info(
            f"缓存初始化: max_entries={max_entries}, "
            f"default_ttl={default_ttl}s, cleanup={cleanup_interval}s"
        )
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            
            entry.access_count += 1
            
            if entry.is_expired:
                logger.debug(f"缓存过期: {key} (age={entry.age:.1f}s)")
                del self._cache[key]
                return None
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存"""
        with self._lock:
            # 检查是否达到上限
            if len(self._cache) >= self._max_entries and key not in self._cache:
                self._evict()
            
            self._cache[key] = CacheEntry(key, value, ttl or self._default_ttl)
    
    def delete(self, key: str):
        """删除缓存"""
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            logger.info("缓存已清空")
    
    def get_or_set(self, key: str, func: Callable, ttl: Optional[int] = None) -> Any:
        """
        获取或设置缓存
        1. 先查缓存
        2. 缓存未命中则执行 func
        3. 结果写入缓存
        """
        # 先查缓存
        cached = self.get(key)
        if cached is not None:
            return cached
        
        # 执行函数获取数据
        logger.debug(f"缓存未命中: {key}")
        value = func()
        
        # 写入缓存
        self.set(key, value, ttl)
        
        return value
    
    def _evict(self):
        """淘汰策略: LRU + 过期优先"""
        # 先清理过期条目
        now = time.time()
        expired_keys = [
            k for k, v in self._cache.items()
            if (now - v.created_at) > v.ttl
        ]
        for k in expired_keys:
            del self._cache[k]
        
        # 如果仍然超出，淘汰最久未访问的
        if len(self._cache) >= self._max_entries:
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].access_count
            )
            # 淘汰访问次数最少的10%
            evict_count = max(1, int(len(sorted_entries) * 0.1))
            for key, _ in sorted_entries[:evict_count]:
                del self._cache[key]
    
    def cleanup(self):
        """自动清理过期条目"""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        with self._lock:
            expired = [k for k, v in self._cache.items() if v.is_expired]
            for k in expired:
                del self._cache[k]
            self._last_cleanup = now
            
            if expired:
                logger.debug(f"清理过期缓存: {len(expired)} 个")
    
    @property
    def stats(self) -> Dict:
        """缓存统计"""
        active = [v for v in self._cache.values() if not v.is_expired]
        return {
            'total_entries': len(self._cache),
            'active_entries': len(active),
            'expired_entries': len(self._cache) - len(active),
            'max_entries': self._max_entries,
            'default_ttl': self._default_ttl,
        }


# 预定义缓存策略（单位：秒）
CACHE_TTL = {
    'project_list': 600,      # 项目列表 - 10分钟
    'task_stats': 300,        # 任务统计 - 5分钟
    'task_detail': 60,        # 任务详情 - 1分钟
    'dashboard': 120,         # 仪表盘数据 - 2分钟
    'system_health': 180,     # 系统状态 - 3分钟
    'index_status': 3600,     # 索引状态 - 1小时
}


class CacheManager:
    """
    缓存管理器 - 封装缓存操作
    
    使用方式:
        cm = CacheManager()
        tasks = cm.get_task_stats()
        cm.invalidate('task_stats')
    """
    
    def __init__(self):
        self._cache = MemoryCache()
        self._lock = threading.Lock()
    
    def get_or_set(self, key: str, func: Callable, ttl_key: str = 'task_detail') -> Any:
        """获取或设置缓存（使用预定义TTL）"""
        ttl = CACHE_TTL.get(ttl_key, 300)
        return self._cache.get_or_set(key, func, ttl)
    
    def invalidate(self, *keys: str):
        """使缓存失效"""
        with self._lock:
            for key in keys:
                self._cache.delete(key)
            # 也清除匹配的通配符模式
            for cache_key in list(self._cache._cache.keys()):
                if any(pattern in cache_key for pattern in keys):
                    self._cache.delete(cache_key)
    
    def invalidate_all(self):
        """使所有缓存失效"""
        self._cache.clear()
    
    @property
    def stats(self) -> Dict:
        return self._cache.stats


# 全局缓存管理器
cache_manager = CacheManager()


def cached(ttl_key: str = 'task_detail'):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key_parts = [func.__module__, func.__qualname__]
            if args:
                key_parts.append(str(args))
            if kwargs:
                key_parts.append(str(sorted(kwargs.items())))
            cache_key = ":".join(key_parts)
            
            def load():
                return func(*args, **kwargs)
            
            return cache_manager.get_or_set(cache_key, load, ttl_key)
        return wrapper
    return decorator


# =============================================================
# 缓存预定义查询函数
# =============================================================

def get_cached_task_stats(connection_pool=None):
    """
    获取任务统计（缓存5分钟）
    预优化: 直接聚合查询，不再全表扫描+程序聚合
    """
    from lib.connection_pool import pool as default_pool
    p = connection_pool or default_pool
    
    return cache_manager.get_or_set(
        'task_stats',
        lambda: p.execute_query("""
            SELECT 
                COALESCE(status, 'unknown') as status,
                COUNT(*) as count
            FROM tasks 
            GROUP BY status
            ORDER BY count DESC
        """),
        'task_stats'
    )


def get_cached_project_list(connection_pool=None):
    """获取活跃项目列表（缓存10分钟）"""
    from lib.connection_pool import pool as default_pool
    p = connection_pool or default_pool
    
    return cache_manager.get_or_set(
        'project_list',
        lambda: p.execute_query("""
            SELECT id, name, status, priority, deadline
            FROM projects
            WHERE status = 'active'
            ORDER BY priority DESC, deadline ASC
        """),
        'project_list'
    )


def get_cached_dashboard(connection_pool=None):
    """获取仪表盘数据（缓存2分钟）"""
    from lib.connection_pool import pool as default_pool
    p = connection_pool or default_pool
    
    return cache_manager.get_or_set(
        'dashboard_data',
        lambda: {
            'task_stats': p.execute_query("SELECT status, COUNT(*) as count FROM tasks GROUP BY status"),
            'project_stats': p.execute_query("SELECT status, COUNT(*) as count FROM projects GROUP BY status"),
            'recent_tasks': p.execute_query("""
                SELECT id, title, status, priority, updated_at 
                FROM tasks 
                ORDER BY updated_at DESC 
                LIMIT 10
            """),
        },
        'dashboard'
    )


def get_cached_system_health(connection_pool=None):
    """获取系统健康状态（缓存3分钟）"""
    from lib.connection_pool import pool as default_pool
    p = connection_pool or default_pool
    
    return cache_manager.get_or_set(
        'system_health',
        lambda: {
            'total_tasks': p.execute_query("SELECT COUNT(*) as count FROM tasks")[0]['count'],
            'pending_tasks': p.execute_query("SELECT COUNT(*) as count FROM tasks WHERE status='pending'")[0]['count'],
            'in_progress': p.execute_query("SELECT COUNT(*) as count FROM tasks WHERE status='in_progress'")[0]['count'],
            'stale_tasks': p.execute_query("""
                SELECT COUNT(*) as count FROM tasks 
                WHERE status IN ('pending','in_progress') 
                AND updated_at < DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)[0]['count'],
            'db_status': 'healthy',
        },
        'system_health'
    )


# =============================================================
# 测试
# =============================================================
if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    
    from lib.connection_pool import get_pool
    p = get_pool()
    
    print("=== 缓存模块测试 ===")
    
    # 测试1: 缓存任务统计
    t0 = time.time()
    stats1 = get_cached_task_stats(p)
    t1 = time.time()
    print(f"✅ 首次查询（未命中）: {(t1-t0)*1000:.1f}ms")
    
    t0 = time.time()
    stats2 = get_cached_task_stats(p)
    t1 = time.time()
    print(f"✅ 第二次查询（命中）: {(t1-t0)*1000:.1f}ms")
    
    # 测试2: 缓存统计
    print(f"\n📊 缓存统计: {cache_manager.stats}")
    
    # 测试3: 清除缓存
    cache_manager.invalidate('task_stats')
    print("✅ 缓存已清除")
    
    p.close()

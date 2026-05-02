"""
Shared Memory Module - 多智能体共享记忆模块
v5.0 多智能体协作框架核心组件
"""
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class MemoryType(Enum):
    CONTEXT = "context"      # 任务上下文
    KNOWLEDGE = "knowledge"  # 通用知识
    RESULT = "result"        # 执行结果
    ERROR = "error"          # 错误信息
    EXPERIENCE = "experience" # 经验沉淀

@dataclass
class MemoryItem:
    id: str
    type: MemoryType
    content: Any
    source: str
    timestamp: float
    access_count: int = 0
    ttl: Optional[float] = None  # None = 永久有效
    
    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return time.time() > self.timestamp + self.ttl

class SharedMemory:
    def __init__(self, capacity: int = 1000):
        self.memory_store: Dict[str, MemoryItem] = {}
        self.capacity = capacity
        self.access_log: List[Dict] = []
        
    def add(self, 
            content: Any, 
            mem_type: MemoryType, 
            source: str,
            ttl: Optional[float] = None) -> str:
        """添加记忆项"""
        mem_id = f"mem_{int(time.time() * 1000)}_{len(self.memory_store)}"
        item = MemoryItem(
            id=mem_id,
            type=mem_type,
            content=content,
            source=source,
            timestamp=time.time(),
            ttl=ttl
        )
        
        # 容量控制：LRU淘汰
        if len(self.memory_store) >= self.capacity:
            self._evict_lru()
            
        self.memory_store[mem_id] = item
        return mem_id
    
    def get(self, mem_id: str) -> Optional[MemoryItem]:
        """获取记忆项"""
        item = self.memory_store.get(mem_id)
        if item and not item.is_expired():
            item.access_count += 1
            self.access_log.append({
                "mem_id": mem_id,
                "access_time": time.time()
            })
            return item
        return None
    
    def search(self, 
               query: Optional[str] = None,
               mem_type: Optional[MemoryType] = None,
               source: Optional[str] = None,
               limit: int = 10) -> List[MemoryItem]:
        """搜索记忆"""
        results = []
        for item in self.memory_store.values():
            if item.is_expired():
                continue
            if mem_type and item.type != mem_type:
                continue
            if source and item.source != source:
                continue
            if query:
                # 简单关键词匹配，生产环境可替换为向量检索
                content_str = json.dumps(item.content, ensure_ascii=False)
                if query.lower() not in content_str.lower():
                    continue
            results.append(item)
            
        # 按访问次数+时间排序
        results.sort(key=lambda x: (x.access_count, x.timestamp), reverse=True)
        return results[:limit]
    
    def _evict_lru(self):
        """LRU淘汰策略"""
        sorted_items = sorted(
            self.memory_store.values(),
            key=lambda x: (x.access_count, x.timestamp)
        )
        if sorted_items:
            del self.memory_store[sorted_items[0].id]
    
    def get_stats(self) -> Dict:
        """获取记忆统计"""
        type_counts = {t.value: 0 for t in MemoryType}
        for item in self.memory_store.values():
            if not item.is_expired():
                type_counts[item.type.value] += 1
                
        return {
            "total_items": len(self.memory_store),
            "type_distribution": type_counts,
            "total_accesses": len(self.access_log),
            "capacity_utilization": len(self.memory_store) / self.capacity
        }
    
    def export_to_json(self, path: str):
        """导出记忆到文件"""
        data = {
            "items": [asdict(item) for item in self.memory_store.values()],
            "stats": self.get_stats()
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

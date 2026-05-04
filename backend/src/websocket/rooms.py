"""
房间管理 - join/leave project room
房间名格式: project:${project_id}
"""

import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)

# socket_id -> set(room_name)
socket_rooms: Dict[str, Set[str]] = {}

# room_name -> set(socket_id)
room_members: Dict[str, Set[str]] = {}


def join_room(socket_id: str, room_name: str) -> bool:
    """
    加入房间
    
    Args:
        socket_id: Socket.IO session ID
        room_name: 房间名称
        
    Returns:
        是否成功加入
    """
    if not room_name:
        return False
    
    # 记录 socket 加入的房间
    if socket_id not in socket_rooms:
        socket_rooms[socket_id] = set()
    socket_rooms[socket_id].add(room_name)
    
    # 记录房间的成员
    if room_name not in room_members:
        room_members[room_name] = set()
    room_members[room_name].add(socket_id)
    
    logger.info(f"🏠 加入房间: sid={socket_id}, room={room_name}")
    return True


def leave_room(socket_id: str, room_name: str) -> bool:
    """
    离开房间
    
    Args:
        socket_id: Socket.IO session ID
        room_name: 房间名称
        
    Returns:
        是否成功离开
    """
    if not room_name:
        return False
    
    # 从 socket 的房间列表中移除
    if socket_id in socket_rooms:
        socket_rooms[socket_id].discard(room_name)
        if not socket_rooms[socket_id]:
            del socket_rooms[socket_id]
    
    # 从房间的成员列表中移除
    if room_name in room_members:
        room_members[room_name].discard(socket_id)
        if not room_members[room_name]:
            del room_members[room_name]
    
    logger.info(f"🚪 离开房间: sid={socket_id}, room={room_name}")
    return True


def leave_all_rooms(socket_id: str) -> int:
    """
    离开所有房间（断开连接时调用）
    
    Args:
        socket_id: Socket.IO session ID
        
    Returns:
        离开的房间数
    """
    if socket_id not in socket_rooms:
        return 0
    
    rooms = list(socket_rooms[socket_id])
    count = 0
    
    for room_name in rooms:
        leave_room(socket_id, room_name)
        count += 1
    
    # 清理 socket 的房间记录
    if socket_id in socket_rooms:
        del socket_rooms[socket_id]
    
    if count > 0:
        logger.info(f"🚪 离开所有房间: sid={socket_id}, 共 {count} 个房间")
    
    return count


def get_socket_rooms(socket_id: str) -> Set[str]:
    """
    获取 socket 加入的所有房间
    
    Args:
        socket_id: Socket.IO session ID
        
    Returns:
        房间名称集合
    """
    return set(socket_rooms.get(socket_id, set()))


def get_room_members(room_name: str) -> Set[str]:
    """
    获取房间的所有成员
    
    Args:
        room_name: 房间名称
        
    Returns:
        socket_id 集合
    """
    return set(room_members.get(room_name, set()))


def get_room_member_count(room_name: str) -> int:
    """
    获取房间成员数量
    
    Args:
        room_name: 房间名称
        
    Returns:
        成员数量
    """
    return len(room_members.get(room_name, set()))


def is_in_room(socket_id: str, room_name: str) -> bool:
    """
    检查 socket 是否在房间中
    
    Args:
        socket_id: Socket.IO session ID
        room_name: 房间名称
        
    Returns:
        是否在房间中
    """
    return room_name in socket_rooms.get(socket_id, set())


def make_project_room_name(project_id) -> str:
    """
    生成项目房间名称
    
    Args:
        project_id: 项目 ID
        
    Returns:
        房间名称，格式: project:${project_id}
    """
    return f"project:{project_id}"


def get_all_rooms() -> Dict[str, Set[str]]:
    """
    获取所有房间信息
    
    Returns:
        房间名称 -> socket_id 集合 的字典副本
    """
    return {name: set(members) for name, members in room_members.items()}


def get_room_stats() -> Dict[str, int]:
    """
    获取房间统计信息
    
    Returns:
        房间名称 -> 成员数量 的字典
    """
    return {name: len(members) for name, members in room_members.items()}

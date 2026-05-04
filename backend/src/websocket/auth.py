"""
JWT 认证中间件 - WebSocket 连接认证
从 query.token 或 header 读取 JWT token 验证用户身份
"""

import os
import jwt
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import pymysql

logger = logging.getLogger(__name__)

# JWT Secret
JWT_SECRET = os.environ.get('JWT_SECRET_KEY', os.environ.get('JWT_SECRET', 'kanban-secret'))

# 数据库配置
MYSQL_HOST = os.environ.get('MYSQL_HOST', 'rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com')
MYSQL_PORT = int(os.environ.get('MYSQL_PORT', '3306'))
MYSQL_USER = os.environ.get('MYSQL_USER', 'kanban')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'Irc210Irc210!')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'kanban')


def get_db_connection():
    """获取 MySQL 数据库连接"""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    验证 JWT token
    
    Args:
        token: JWT token 字符串
        
    Returns:
        解码后的 payload 字典，验证失败返回 None
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token 已过期")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT token 无效: {e}")
        return None
    except Exception as e:
        logger.error(f"JWT 验证异常: {e}")
        return None


def get_user_from_db(user_id: int) -> Optional[Dict[str, Any]]:
    """
    从数据库获取用户信息
    
    Args:
        user_id: 用户 ID
        
    Returns:
        用户信息字典，不存在返回 None
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, email, is_active, is_admin FROM users WHERE id = %s",
                (user_id,)
            )
            user = cursor.fetchone()
        conn.close()
        return user
    except Exception as e:
        logger.error(f"查询用户失败: {e}")
        return None


def authenticate_socket_connection(environ: dict) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    认证 WebSocket 连接
    
    从 query string 或 header 中读取 token 进行验证
    
    Args:
        environ: WSGI environ 字典
        
    Returns:
        (是否认证成功, 用户信息字典)
    """
    token = None
    
    # 1. 从 query string 读取 token
    query_string = environ.get('QUERY_STRING', '')
    if query_string:
        from urllib.parse import parse_qs
        params = parse_qs(query_string)
        if 'token' in params:
            token = params['token'][0]
    
    # 2. 从 header 读取 token (Authorization: Bearer <token>)
    if not token:
        http_authorization = environ.get('HTTP_AUTHORIZATION', '')
        if http_authorization.startswith('Bearer '):
            token = http_authorization[7:]
    
    # 3. 从 cookie 读取 token
    if not token:
        http_cookie = environ.get('HTTP_COOKIE', '')
        if 'token=' in http_cookie:
            for part in http_cookie.split(';'):
                part = part.strip()
                if part.startswith('token='):
                    token = part[6:]
                    break
    
    if not token:
        logger.warning("WebSocket 连接缺少认证 token")
        return False, None
    
    # 验证 token
    payload = verify_jwt_token(token)
    if not payload:
        return False, None
    
    user_id = payload.get('user_id') or payload.get('id')
    if not user_id:
        logger.warning("JWT payload 中缺少 user_id")
        return False, None
    
    # 查询用户信息
    user = get_user_from_db(int(user_id))
    if not user:
        logger.warning(f"用户不存在: user_id={user_id}")
        return False, None
    
    if not user.get('is_active', True):
        logger.warning(f"用户已被禁用: user_id={user_id}")
        return False, None
    
    logger.info(f"WebSocket 认证成功: user_id={user_id}, username={user['username']}")
    return True, user


def generate_test_token(user_id: int = 1, username: str = 'test') -> str:
    """
    生成测试用 JWT token
    
    Args:
        user_id: 用户 ID
        username: 用户名
        
    Returns:
        JWT token 字符串
    """
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': datetime.utcnow().timestamp() + 86400  # 24小时过期
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

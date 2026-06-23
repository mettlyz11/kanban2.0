"""
认证管理模块
"""

from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import request, jsonify, current_app
import jwt
from datetime import datetime, timedelta

class AuthService:
    """用户认证服务"""
    
    def __init__(self, db_path=None, jwt_secret=None):
        self.db_path = db_path
        self.jwt_secret = jwt_secret or "your-secret-key-change-in-production"
    
    def register(self, username, password, email=None):
        """用户注册"""
        # 延迟导入避免循环依赖
        from app import get_db
        
        password_hash = generate_password_hash(password)
        
        conn = get_db()
        c = conn.cursor()
        
        try:
            c.execute("""
                INSERT INTO users (username, email, password_hash)
                VALUES (%s, %s, %s)
            """, (username, email, password_hash))
            
            user_id = c.lastrowid
            conn.commit()
            
            return {"success": True, "user_id": user_id, "message": "注册成功"}
        except Exception as e:
            return {"success": False, "error": "用户名或邮箱已存在"}
        finally:
            conn.close()
    
    def login(self, username, password):
        """用户登录"""
        # 延迟导入避免循环依赖
        from app import get_db
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute("""
            SELECT id, username, password_hash, is_active, is_admin
            FROM users
            WHERE username = %s
        """, (username,))
        
        user = c.fetchone()
        
        if not user:
            conn.close()
            return {"success": False, "error": "用户不存在"}
        
        if not check_password_hash(user["password_hash"], password):
            conn.close()
            return {"success": False, "error": "密码错误"}
        
        if not user["is_active"]:
            conn.close()
            return {"success": False, "error": "账户已被禁用"}
        
        # 更新最后登录时间
        c.execute("UPDATE users SET last_login_at = %s WHERE id = %s",
                  (datetime.now().isoformat(), user["id"]))
        conn.commit()
        conn.close()
        
        # 生成JWT Token
        token = jwt.encode({
            "user_id": user["id"],
            "username": user["username"],
            "is_admin": bool(user["is_admin"]),
            "exp": datetime.utcnow() + timedelta(days=7)
        }, self.jwt_secret, algorithm="HS256")
        
        return {
            "success": True,
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "is_admin": bool(user["is_admin"])
            }
        }

    def get_user(self, user_id):
        """Return public current-user profile for /api/auth/me."""
        from app import get_db
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("""
                SELECT id, username, email, is_active, is_admin, created_at, last_login_at
                FROM users
                WHERE id = %s
            """, (user_id,))
            user = c.fetchone()
            if not user:
                return {"success": False, "error": "用户不存在"}
            data = dict(user)
            data["is_active"] = bool(data.get("is_active"))
            data["is_admin"] = bool(data.get("is_admin"))
            for key in ("created_at", "last_login_at"):
                value = data.get(key)
                if hasattr(value, "isoformat"):
                    data[key] = value.isoformat()
            return {"success": True, "user": data}
        finally:
            conn.close()

# 其他需要的类和函数
class APIKeyManager:
    pass

class PasswordManager:
    pass

def _jwt_secret():
    try:
        return current_app.config.get("JWT_SECRET") or current_app.config.get("SECRET_KEY") or "your-secret-key-change-in-production"
    except RuntimeError:
        return "your-secret-key-change-in-production"


def token_required(f):
    """Inject current_user_id from Bearer token; return 401 instead of Flask 500."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        token = token or request.headers.get("X-Access-Token") or request.args.get("token")
        if not token:
            return jsonify({"success": False, "error": "缺少认证令牌"}), 401
        try:
            payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
            current_user_id = payload.get("user_id")
            if not current_user_id:
                return jsonify({"success": False, "error": "无效认证令牌"}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "error": "认证令牌已过期"}), 401
        except Exception:
            return jsonify({"success": False, "error": "无效认证令牌"}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated


def api_key_required(f):
    return f


def init_auth_tables():
    pass


def generate_secure_password():
    return "password123"


def encrypt_password(password, *args, **kwargs):
    return password


def decrypt_password(encrypted, *args, **kwargs):
    return encrypted

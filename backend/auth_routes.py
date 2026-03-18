"""
P049项目 - API密钥管理和密码管理路由
任务: P049-T008 (API密钥管理), P049-T007 (密码管理)
"""

from flask import Blueprint, request, jsonify, current_app
import os
import sys

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth_manager import (
    APIKeyManager, PasswordManager, AuthService,
    token_required, api_key_required, init_auth_tables,
    generate_secure_password, encrypt_password, decrypt_password
)

# 创建蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# 获取数据库路径
def get_db_path():
    return current_app.config.get('DB_PATH', os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'kanban_v5.db'
    ))

# ============================================
# 认证相关路由
# ============================================

@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    email = data.get('email', '').strip() or None
    
    if not username or not password:
        return jsonify({'success': False, 'error': '用户名和密码不能为空'}), 400
    
    if len(password) < 6:
        return jsonify({'success': False, 'error': '密码长度至少6位'}), 400
    
    auth_service = AuthService(get_db_path())
    result = auth_service.register(username, password, email)
    
    if result['success']:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'success': False, 'error': '用户名和密码不能为空'}), 400
    
    auth_service = AuthService(get_db_path())
    result = auth_service.login(username, password)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 401


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user_id):
    """获取当前用户信息"""
    auth_service = AuthService(get_db_path())
    result = auth_service.get_user(current_user_id)
    return jsonify(result)


# ============================================
# API密钥管理路由 (P049-T008)
# ============================================

@auth_bp.route('/api-keys', methods=['POST'])
@token_required
def create_api_key(current_user_id):
    """创建新的API Key"""
    data = request.get_json()
    key_name = data.get('key_name', '').strip()
    permissions = data.get('permissions', ['read'])
    expires_days = data.get('expires_days')
    
    if not key_name:
        return jsonify({'success': False, 'error': 'Key名称不能为空'}), 400
    
    manager = APIKeyManager(get_db_path())
    result = manager.create_key(
        user_id=current_user_id,
        key_name=key_name,
        permissions=permissions,
        expires_days=expires_days
    )
    
    if result['success']:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@auth_bp.route('/api-keys', methods=['GET'])
@token_required
def list_api_keys(current_user_id):
    """列出所有API Key"""
    manager = APIKeyManager(get_db_path())
    result = manager.list_keys(current_user_id)
    return jsonify(result)


@auth_bp.route('/api-keys/<int:key_id>', methods=['PUT'])
@token_required
def update_api_key(current_user_id, key_id):
    """更新API Key"""
    data = request.get_json()
    key_name = data.get('key_name')
    permissions = data.get('permissions')
    is_active = data.get('is_active')
    
    manager = APIKeyManager(get_db_path())
    result = manager.update_key(
        user_id=current_user_id,
        key_id=key_id,
        key_name=key_name,
        permissions=permissions,
        is_active=is_active
    )
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400


@auth_bp.route('/api-keys/<int:key_id>/revoke', methods=['POST'])
@token_required
def revoke_api_key(current_user_id, key_id):
    """撤销API Key"""
    manager = APIKeyManager(get_db_path())
    result = manager.revoke_key(current_user_id, key_id)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400


@auth_bp.route('/api-keys/<int:key_id>', methods=['DELETE'])
@token_required
def delete_api_key(current_user_id, key_id):
    """删除API Key"""
    manager = APIKeyManager(get_db_path())
    result = manager.delete_key(current_user_id, key_id)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400


# ============================================
# 密码管理路由 (P049-T007)
# ============================================

@auth_bp.route('/passwords', methods=['POST'])
@token_required
def add_password(current_user_id):
    """添加新密码"""
    data = request.get_json()
    service_name = data.get('service_name', '').strip()
    password = data.get('password', '')
    service_url = data.get('service_url', '').strip() or None
    username = data.get('username', '').strip() or None
    notes = data.get('notes', '').strip() or None
    category = data.get('category', 'other')
    
    if not service_name or not password:
        return jsonify({'success': False, 'error': '服务名称和密码不能为空'}), 400
    
    # 加密密码
    master_key = current_app.config.get('MASTER_KEY', 'default-master-key-change-in-production')
    encrypted_password = encrypt_password(password, master_key)
    
    manager = PasswordManager(get_db_path(), master_key)
    result = manager.add_password(
        user_id=current_user_id,
        service_name=service_name,
        encrypted_password=encrypted_password,
        service_url=service_url,
        username=username,
        notes=notes,
        category=category
    )
    
    if result['success']:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@auth_bp.route('/passwords', methods=['GET'])
@token_required
def list_passwords(current_user_id):
    """列出所有密码"""
    category = request.args.get('category')
    search = request.args.get('search')
    
    manager = PasswordManager(get_db_path())
    result = manager.list_passwords(
        user_id=current_user_id,
        category=category,
        search=search
    )
    return jsonify(result)


@auth_bp.route('/passwords/<int:password_id>', methods=['GET'])
@token_required
def get_password(current_user_id, password_id):
    """获取单个密码（解密）"""
    master_key = current_app.config.get('MASTER_KEY', 'default-master-key-change-in-production')
    manager = PasswordManager(get_db_path(), master_key)
    result = manager.get_password(current_user_id, password_id)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 404


@auth_bp.route('/passwords/<int:password_id>', methods=['PUT'])
@token_required
def update_password_entry(current_user_id, password_id):
    """更新密码"""
    data = request.get_json()
    
    kwargs = {}
    if 'service_name' in data:
        kwargs['service_name'] = data['service_name']
    if 'service_url' in data:
        kwargs['service_url'] = data['service_url']
    if 'username' in data:
        kwargs['username'] = data['username']
    if 'notes' in data:
        kwargs['notes'] = data['notes']
    if 'category' in data:
        kwargs['category'] = data['category']
    
    # 如果更新密码，需要加密
    if 'password' in data and data['password']:
        master_key = current_app.config.get('MASTER_KEY', 'default-master-key-change-in-production')
        kwargs['encrypted_password'] = encrypt_password(data['password'], master_key)
    
    manager = PasswordManager(get_db_path())
    result = manager.update_password(current_user_id, password_id, **kwargs)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400


@auth_bp.route('/passwords/<int:password_id>', methods=['DELETE'])
@token_required
def delete_password_entry(current_user_id, password_id):
    """删除密码"""
    manager = PasswordManager(get_db_path())
    result = manager.delete_password(current_user_id, password_id)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400


@auth_bp.route('/passwords/<int:password_id>/favorite', methods=['POST'])
@token_required
def toggle_password_favorite(current_user_id, password_id):
    """切换密码收藏状态"""
    manager = PasswordManager(get_db_path())
    result = manager.toggle_favorite(current_user_id, password_id)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400


@auth_bp.route('/passwords/categories', methods=['GET'])
@token_required
def get_password_categories(current_user_id):
    """获取密码分类列表"""
    manager = PasswordManager(get_db_path())
    result = manager.get_categories()
    return jsonify(result)


@auth_bp.route('/passwords/generate', methods=['GET'])
@token_required
def generate_password(current_user_id):
    """生成安全密码"""
    length = request.args.get('length', 16, type=int)
    if length < 8:
        length = 8
    if length > 64:
        length = 64
    
    password = generate_secure_password(length)
    return jsonify({
        'success': True,
        'password': password,
        'length': length
    })


# ============================================
# 工具路由
# ============================================

@auth_bp.route('/init', methods=['POST'])
def init_auth_system():
    """初始化认证系统（创建必要的表）"""
    try:
        db_path = get_db_path()
        init_auth_tables(db_path)
        return jsonify({'success': True, 'message': '认证系统初始化成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# 测试路由
# ============================================

@auth_bp.route('/test', methods=['GET'])
def test_auth():
    """测试认证API是否正常工作"""
    return jsonify({
        'success': True,
        'message': '认证API正常工作',
        'endpoints': {
            'auth': [
                'POST /api/auth/register - 用户注册',
                'POST /api/auth/login - 用户登录',
                'GET /api/auth/me - 获取当前用户',
            ],
            'api_keys': [
                'POST /api/auth/api-keys - 创建API Key',
                'GET /api/auth/api-keys - 列出API Keys',
                'PUT /api/auth/api-keys/<id> - 更新API Key',
                'POST /api/auth/api-keys/<id>/revoke - 撤销API Key',
                'DELETE /api/auth/api-keys/<id> - 删除API Key',
            ],
            'passwords': [
                'POST /api/auth/passwords - 添加密码',
                'GET /api/auth/passwords - 列出密码',
                'GET /api/auth/passwords/<id> - 获取密码',
                'PUT /api/auth/passwords/<id> - 更新密码',
                'DELETE /api/auth/passwords/<id> - 删除密码',
                'POST /api/auth/passwords/<id>/favorite - 切换收藏',
                'GET /api/auth/passwords/categories - 分类列表',
                'GET /api/auth/passwords/generate - 生成密码',
            ]
        }
    })

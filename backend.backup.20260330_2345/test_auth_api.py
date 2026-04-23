#!/usr/bin/env python3
"""
P049项目 - API测试脚本
测试P049-T008 (API密钥管理) 和 P049-T007 (密码管理)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth_manager import (
    APIKeyManager, PasswordManager, AuthService,
    init_auth_tables, generate_secure_password, encrypt_password, decrypt_password
)
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kanban_v5.db')
MASTER_KEY = 'test-master-key-for-development'

def test_auth_service():
    """测试用户认证服务"""
    print("\n" + "="*60)
    print("测试 1: 用户认证服务")
    print("="*60)
    
    auth = AuthService(DB_PATH, jwt_secret='test-secret')
    
    # 1. 用户注册
    print("\n[1.1] 用户注册...")
    result = auth.register('testuser', 'password123', 'test@example.com')
    print(f"  注册结果: {result}")
    
    # 如果用户已存在，继续测试
    if not result['success'] and '已存在' in result.get('error', ''):
        print("  用户已存在，继续登录测试")
    
    # 2. 用户登录
    print("\n[1.2] 用户登录...")
    result = auth.login('testuser', 'password123')
    print(f"  登录结果: {result['success']}")
    
    if result['success']:
        token = result['token']
        user_id = result['user']['id']
        print(f"  Token: {token[:30]}...")
        print(f"  用户ID: {user_id}")
        return user_id
    return None

def test_api_key_manager(user_id):
    """测试API密钥管理 (P049-T008)"""
    print("\n" + "="*60)
    print("测试 2: API密钥管理 (P049-T008)")
    print("="*60)
    
    manager = APIKeyManager(DB_PATH)
    
    # 1. 创建API Key
    print("\n[2.1] 创建API Key...")
    result = manager.create_key(
        user_id=user_id,
        key_name='测试API Key',
        permissions=['read', 'write'],
        expires_days=30
    )
    print(f"  创建结果: {result['success']}")
    if result['success']:
        key_id = result['key_id']
        api_key = result['api_key']
        api_secret = result['api_secret']
        print(f"  Key ID: {key_id}")
        print(f"  API Key: {api_key}")
        print(f"  API Secret: {api_secret[:30]}...")
    else:
        print(f"  错误: {result.get('error')}")
        return None
    
    # 2. 列出API Keys
    print("\n[2.2] 列出API Keys...")
    result = manager.list_keys(user_id)
    print(f"  列表结果: {result['success']}")
    if result['success']:
        print(f"  共有 {len(result['keys'])} 个API Key")
        for key in result['keys']:
            print(f"    - {key['key_name']}: {key['api_key']} (权限: {key['permissions']})")
    
    # 3. 更新API Key
    print("\n[2.3] 更新API Key...")
    result = manager.update_key(
        user_id=user_id,
        key_id=key_id,
        key_name='更新后的API Key名称',
        permissions=['read', 'write', 'delete']
    )
    print(f"  更新结果: {result}")
    
    # 4. 撤销API Key
    print("\n[2.4] 撤销API Key...")
    result = manager.revoke_key(user_id, key_id)
    print(f"  撤销结果: {result}")
    
    # 5. 删除API Key
    print("\n[2.5] 删除API Key...")
    result = manager.delete_key(user_id, key_id)
    print(f"  删除结果: {result}")
    
    return True

def test_password_manager(user_id):
    """测试密码管理 (P049-T007)"""
    print("\n" + "="*60)
    print("测试 3: 密码管理 (P049-T007)")
    print("="*60)
    
    manager = PasswordManager(DB_PATH, MASTER_KEY)
    
    # 1. 添加密码
    print("\n[3.1] 添加密码...")
    password = "MySecurePassword123!"
    encrypted = encrypt_password(password, MASTER_KEY)
    result = manager.add_password(
        user_id=user_id,
        service_name='GitHub',
        encrypted_password=encrypted,
        service_url='https://github.com',
        username='myusername',
        notes='我的GitHub账号',
        category='work'
    )
    print(f"  添加结果: {result}")
    password_id = result.get('password_id')
    
    # 添加第二个密码
    result2 = manager.add_password(
        user_id=user_id,
        service_name='Gmail',
        encrypted_password=encrypt_password('GmailPass456!', MASTER_KEY),
        service_url='https://gmail.com',
        username='myemail@gmail.com',
        category='email'
    )
    password_id2 = result2.get('password_id')
    
    # 2. 列出密码
    print("\n[3.2] 列出所有密码...")
    result = manager.list_passwords(user_id)
    print(f"  列表结果: {result['success']}")
    if result['success']:
        print(f"  共有 {len(result['passwords'])} 个密码")
        for pwd in result['passwords']:
            print(f"    - {pwd['service_name']} ({pwd['category']})")
    
    # 3. 按分类筛选
    print("\n[3.3] 按分类筛选 (email)...")
    result = manager.list_passwords(user_id, category='email')
    print(f"  筛选结果: {len(result['passwords'])} 个密码")
    
    # 4. 搜索密码
    print("\n[3.4] 搜索密码...")
    result = manager.list_passwords(user_id, search='git')
    print(f"  搜索结果: {len(result['passwords'])} 个密码")
    
    # 5. 获取单个密码（解密）
    print("\n[3.5] 获取单个密码（解密）...")
    result = manager.get_password(user_id, password_id)
    print(f"  获取结果: {result['success']}")
    if result['success']:
        pwd = result['password']
        print(f"  服务: {pwd['service_name']}")
        print(f"  用户名: {pwd['username']}")
        print(f"  密码: {pwd['password']}")
    
    # 6. 更新密码
    print("\n[3.6] 更新密码...")
    new_password = "UpdatedPassword789!"
    result = manager.update_password(
        user_id=user_id,
        password_id=password_id,
        notes='更新后的备注信息',
        encrypted_password=encrypt_password(new_password, MASTER_KEY)
    )
    print(f"  更新结果: {result}")
    
    # 7. 切换收藏状态
    print("\n[3.7] 切换收藏状态...")
    result = manager.toggle_favorite(user_id, password_id)
    print(f"  收藏结果: {result}")
    
    # 8. 获取分类列表
    print("\n[3.8] 获取分类列表...")
    result = manager.get_categories()
    print(f"  分类数量: {len(result['categories'])}")
    for cat in result['categories']:
        print(f"    - {cat['id']}: {cat['name']}")
    
    # 9. 生成安全密码
    print("\n[3.9] 生成安全密码...")
    generated = generate_secure_password(20)
    print(f"  生成密码: {generated}")
    print(f"  密码长度: {len(generated)}")
    
    # 10. 删除密码
    print("\n[3.10] 删除密码...")
    result = manager.delete_password(user_id, password_id2)
    print(f"  删除结果: {result}")
    
    return True

def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("P049项目后端API测试")
    print("任务: P049-T008 (API密钥管理), P049-T007 (密码管理)")
    print("="*60)
    
    # 初始化数据库
    print("\n初始化数据库表...")
    init_auth_tables(DB_PATH)
    
    # 测试认证服务
    user_id = test_auth_service()
    
    if not user_id:
        # 尝试获取已存在的用户
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT id FROM users WHERE username = ?', ('testuser',))
        row = c.fetchone()
        if row:
            user_id = row[0]
        conn.close()
    
    if user_id:
        # 测试API密钥管理
        test_api_key_manager(user_id)
        
        # 测试密码管理
        test_password_manager(user_id)
    else:
        print("\n❌ 无法获取用户ID，跳过后续测试")
    
    print("\n" + "="*60)
    print("测试完成!")
    print("="*60)

if __name__ == '__main__':
    run_all_tests()

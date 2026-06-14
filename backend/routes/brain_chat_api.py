"""Routes: brain_chat_api - 知识大脑 + 聊天 + 登录"""
from datetime import timedelta
from flask import Blueprint, current_app, jsonify, request
from routes.helpers import get_db, row_to_dict
import hashlib
import traceback
from werkzeug.security import check_password_hash
import jwt
import os
import json
from datetime import datetime

bp = Blueprint("routes_brain_chat_api", __name__)
logger = __import__("logging").getLogger(__name__)

@bp.route('/api/brain/stats', methods=['GET'])
def get_brain_stats():
    """获取知识大脑统计"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        # 实体统计
        c.execute('SELECT COUNT(*) FROM entities')
        entity_count = list(c.fetchone().values())[0]
    
        # 关系统计
        c.execute('SELECT COUNT(*) FROM entity_relationships')
        relation_count = list(c.fetchone().values())[0]
    
        # 实体类型分布
        c.execute('SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type')
        type_distribution = {row[0]: row['count'] for row in c.fetchall()}
    
        conn.close()
    
        return jsonify({
            'success': True,
            'stats': {
                'entities': entity_count,
                'relationships': relation_count,
                'types': type_distribution
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/brain/nodes', methods=['GET'])
@bp.route('/api/brain/entities', methods=['GET'])
def get_brain_entities():
    """获取所有实体"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        entity_type = request.args.get('type', '')
        search = request.args.get('search', '')
    
        query = '''
            SELECT id, name, entity_type, description, metadata, created_at
            FROM entities
            WHERE 1=1
        '''
        params = []
    
        if entity_type:
            query += ' AND entity_type = %s'
            params.append(entity_type)
    
        if search:
            query += ' AND name LIKE %s'
            params.append(f'%{search}%')
    
        query += ' ORDER BY created_at DESC LIMIT 2000'
    
        c.execute(query, tuple(params))
        entities = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
    
        return jsonify({'success': True, 'entities': entities})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/brain/entity/<name>', methods=['GET'])
def get_brain_entity(name):
    """获取单个实体详情"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        # 获取实体信息
        c.execute('''
            SELECT id, name, entity_type, description, metadata, created_at
            FROM entities WHERE name = %s
        ''', (name,))
        entity = c.fetchone()
    
        if not entity:
            return jsonify({'success': False, 'error': '实体不存在'})
    
        entity_dict = dict(entity)
    
        # 获取相关关系
        c.execute('''
            SELECT source_entity, target_entity, relation_type, description
            FROM entity_relationships
            WHERE source_entity = %s OR target_entity = %s
        ''', (name, name))
        relationships = [row_to_dict(row, c) for row in c.fetchall()]
    
        entity_dict['relationships'] = relationships
    
        conn.close()
        return jsonify({'success': True, 'entity': entity_dict})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/brain/relationships', methods=['GET'])
def get_brain_relationships():
    """获取所有关系（带实体ID和关联实体）"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        # 获取所有实体
        c.execute('SELECT id, name, entity_type, description, metadata FROM entities')
        entity_map = {}
        all_entities = []
        for row in c.fetchall():
            entity_map[row['name']] = row['id']
            all_entities.append({
                'id': row['id'],
                'name': row['name'],
                'entity_type': row['entity_type'],
                'description': row['description']
            })
    
        # 获取关系数据，并转换为ID
        c.execute('''
            SELECT id, source_entity, target_entity, relation_type, description, created_at
            FROM entity_relationships
            ORDER BY created_at DESC
        ''')
        rows = c.fetchall()
    
        relationships = []
        related_entity_ids = set()
    
        for row in rows:
            source_id = entity_map.get(row['source_entity'])
            target_id = entity_map.get(row['target_entity'])
        
            # 只添加有效的关系（两端实体都存在）
            if source_id and target_id:
                relationships.append({
                    'id': row['id'],
                    'source_id': source_id,
                    'target_id': target_id,
                    'source_name': row['source_entity'],
                    'target_name': row['target_entity'],
                    'relation_type': row['relation_type'],
                    'description': row['description'],
                    'created_at': row['created_at']
                })
                related_entity_ids.add(source_id)
                related_entity_ids.add(target_id)
    
        # 只返回关系涉及的实体（用于网络图显示）
        related_entities = [e for e in all_entities if e['id'] in related_entity_ids]
    
        conn.close()
    
        return jsonify({
            'success': True, 
            'relationships': relationships,
            'entities': related_entities
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/brain/sync', methods=['POST'])
def sync_brain():
    """同步知识大脑数据"""
    try:
        # 这里可以触发知识图谱重建等操作
        return jsonify({'success': True, 'message': '同步完成'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/chat/messages', methods=['GET'])
def get_chat_messages():
    """获取聊天消息"""
    try:
        conn = get_db()
        c = conn.cursor()
        # 使用实际的表结构: user_message, bot_reply
        c.execute('''
            SELECT id, user_message as message, bot_reply as response, message_type, created_at
            FROM chat_messages
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        rows = c.fetchall()
        messages = []
        for row in rows:
            # 创建两条消息: 用户消息和机器人回复
            messages.append({
                'id': f"{row['id']}_user",
                'role': 'user',
                'content': row['message'],
                'created_at': row['created_at']
            })
            if row['response']:
                messages.append({
                    'id': f"{row['id']}_bot",
                    'role': 'assistant',
                    'content': row['response'],
                    'created_at': row['created_at']
                })
        conn.close()
        return jsonify({'success': True, 'messages': messages[::-1]})
    except Exception as e:
        # 如果表不存在，返回空列表
        return jsonify({'success': True, 'messages': []})

@bp.route('/api/chat/ask-dudu', methods=['POST'])
def ask_dudu():
    """向Dudu提问 - 调用OpenClaw API"""
    try:
        data = request.get_json()
        message = data.get('message', '')
    
        # 调用OpenClaw API (通过本地gateway)
        try:
            import requests
            import os
        
            # 从环境变量或配置获取OpenClaw Gateway地址
            gateway_url = os.getenv('OPENCLAW_GATEWAY_URL', 'http://127.0.0.1:18792')
        
            # 发送消息到OpenClaw
            res = requests.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "moonshot/kimi-k2.5",
                    "messages": [{"role": "user", "content": message}],
                    "stream": False
                },
                timeout=60,
                headers={"Content-Type": "application/json"}
            )
        
            if res.status_code == 200:
                result = res.json()
                response = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
                # 📊 记录 token 使用和费用
                usage = result.get('usage', {})
                prompt_tokens = usage.get('prompt_tokens', 0)
                completion_tokens = usage.get('completion_tokens', 0)
                if prompt_tokens > 0 or completion_tokens > 0:
                    record_token_usage(
                        provider='moonshot',
                        model='kimi-k2.5',
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens
                    )
            else:
                # 如果Gateway不可用，使用模拟回复
                response = f"[OpenClaw服务暂时不可用]\n\n你的消息：{message[:100]}"
            
        except Exception as api_error:
            # API调用失败时的备用回复
            response = f"[系统提示] 正在处理你的消息：{message[:50]}...\n\n目前OpenClaw连接需要配置Gateway。请确保本地OpenClaw正在运行，或联系管理员配置连接。"
    
        # 保存对话到数据库
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO chat_messages (user_message, bot_reply, message_type, created_at)
            VALUES (%s, %s, 'text', NOW())
        ''', (message, response))
        conn.commit()
        conn.close()
    
        return jsonify({'success': True, 'response': response})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/login', methods=['POST'])
def api_login():
    """用户登录 - 使用数据库验证"""
    try:
        data = request.get_json()
        username = data.get('username', '')
        password = data.get('password', '')
    
        # 从数据库验证用户
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id, username, password_hash, is_admin, is_active FROM users WHERE username = %s', (username,))
        user = c.fetchone()
        conn.close()
    
        if not user:
            return jsonify({'success': False, 'error': '用户名或密码错误'})
    
        from werkzeug.security import check_password_hash
        if not check_password_hash(user["password_hash"], password):
            return jsonify({'success': False, 'error': '用户名或密码错误'})
    
        if not user["is_active"]:
            return jsonify({'success': False, 'error': '账户已被禁用'})
    
        import jwt
        token = jwt.encode({
            'user_id': user["id"],
            'username': user["username"],
            'is_admin': bool(user["is_admin"]),
            'exp': datetime.utcnow() + timedelta(days=30)
        }, current_app.config["JWT_SECRET_KEY"], algorithm='HS256')
    
        return jsonify({
            'success': True,
            'token': token,
            'user': {'id': user["id"], 'username': user["username"], 'role': 'admin' if user["is_admin"] else 'user'}
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


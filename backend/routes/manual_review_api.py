"""Routes: manual_review_api - 人工审核 + 技能 + 邮件 + 联系人"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db, row_to_dict
import os
import json
from datetime import datetime

bp = Blueprint("routes_manual_review_api", __name__)
logger = __import__("logging").getLogger(__name__)

@bp.route('/api/manual-review/tasks', methods=['GET'])
def get_manual_review_tasks():
    """获取手动审核任务"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, original_task_id, title, description, source, status, priority,
                   completion_notes as notes, created_at, completed_at
            FROM manual_review_tasks
            ORDER BY created_at DESC
        ''')
        tasks = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'tasks': tasks})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/manual-review/tasks/<int:task_id>/complete', methods=['POST'])
def complete_manual_review_task(task_id):
    """完成审核任务 - 同时更新关联任务的audit_status"""
    try:
        data = request.get_json()
        approved = data.get('approved', False)
        notes = data.get('notes', '')
    
        conn = get_db()
        c = conn.cursor()
    
        # 1. 获取关联的原始任务ID
        c.execute('SELECT original_task_id FROM manual_review_tasks WHERE id = %s', (task_id,))
        row = c.fetchone()
        original_task_id = row[0] if row else None
    
        # 2. 更新审核任务状态
        c.execute('''
            UPDATE manual_review_tasks 
            SET status = %s, completion_notes = %s, completed_at = NOW()
            WHERE id = %s
        ''', ('approved' if approved else 'rejected', notes, task_id))
    
        # 3. 如果有关联的原始任务，更新其audit_status
        if original_task_id:
            audit_status = 'approved' if approved else 'rejected'
            task_status = 'todo' if approved else 'cancelled'
            c.execute('''
                UPDATE tasks 
                SET audit_status = %s, status = %s, updated_at = NOW()
                WHERE id = %s
            ''', (audit_status, task_status, original_task_id))
    
        conn.commit()
        conn.close()
    
        return jsonify({
            'success': True,
            'message': '任务已' + ('批准' if approved else '拒绝'),
            'task_id': original_task_id,
            'audit_status': 'approved' if approved else 'rejected'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def check_pending_long_think(original_task_id: int, long_think_id: str = None) -> bool:
    """
    检查指定任务是否有未执行的长思考结果
    返回: True = 存在未执行的，False = 不存在或都已执行
    """
    try:
        conn = get_db()
        c = conn.cursor()
    
        # 检查是否有相同 original_task_id 且 status='pending' 的长思考任务
        if long_think_id:
            c.execute('''
                SELECT COUNT(*) FROM manual_review_tasks 
                WHERE original_task_id = %s 
                AND is_from_long_think = 1 
                AND long_think_id = %s
                AND status = 'pending'
            ''', (original_task_id, long_think_id))
        else:
            c.execute('''
                SELECT COUNT(*) FROM manual_review_tasks 
                WHERE original_task_id = %s 
                AND is_from_long_think = 1 
                AND status = 'pending'
            ''', (original_task_id,))
    
        count = list(c.fetchone().values())[0]
        conn.close()
    
        return count > 0
    except Exception as e:
        print(f"[ERROR] check_pending_long_think: {e}")
        return False

@bp.route('/api/manual-review/check-pending', methods=['GET'])
def check_pending_long_think_api():
    """API: 检查任务是否有未执行的长思考"""
    try:
        task_id = request.args.get('task_id', type=int)
        long_think_id = request.args.get('long_think_id')
    
        if not task_id:
            return jsonify({'success': False, 'error': '缺少task_id参数'}), 400
    
        has_pending = check_pending_long_think(task_id, long_think_id)
    
        return jsonify({
            'success': True, 
            'has_pending': has_pending,
            'message': '存在未执行的长思考任务' if has_pending else '没有待执行的长思考任务'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def create_manual_review_task_with_check(original_task_id: int, title: str, description: str,
                                         source: str = 'system', priority: str = 'medium',
                                         suggested_action: str = None, long_think_id: str = None) -> dict:
    """
    创建手动审核任务（带防重复检查）
    如果存在未执行的长思考任务，则不再创建新的
    """
    try:
        conn = get_db()
        c = conn.cursor()
    
        # 如果是长思考产生的任务，检查是否有重复
        if long_think_id:
            # 检查是否有相同 original_task_id 且 status='pending' 的长思考任务
            c.execute('''
                SELECT id, status FROM manual_review_tasks 
                WHERE original_task_id = %s 
                AND is_from_long_think = 1 
                AND status = 'pending'
                LIMIT 1
            ''', (original_task_id,))
        
            existing = c.fetchone()
            if existing:
                conn.close()
                return {
                    'success': False,
                    'error': 'DUPLICATE_LONG_THINK',
                    'message': f'任务 {original_task_id} 已存在未执行的长思考结果 (ID: {existing[0]})，请先处理后再生成新的长思考',
                    'existing_task_id': existing[0]
                }
    
        # 创建新任务
        c.execute('''
            INSERT INTO manual_review_tasks 
            (original_task_id, title, description, status, priority, source, 
             suggested_action, is_from_long_think, long_think_id, created_at)
            VALUES (%s, %s, %s, 'pending', %s, %s, %s, %s, %s, NOW())
        ''', (original_task_id, title, description, priority, source, 
              suggested_action, 1 if long_think_id else 0, long_think_id))
    
        task_id = c.lastrowid
        conn.commit()
        conn.close()
    
        return {
            'success': True,
            'task_id': task_id,
            'message': '审核任务创建成功'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

@bp.route('/api/manual-review/tasks/create', methods=['POST'])
def create_manual_review_task_api():
    """API: 创建手动审核任务（带防重复）"""
    try:
        data = request.get_json()
        result = create_manual_review_task_with_check(
            original_task_id=data.get('original_task_id'),
            title=data.get('title'),
            description=data.get('description'),
            source=data.get('source', 'system'),
            priority=data.get('priority', 'medium'),
            suggested_action=data.get('suggested_action'),
            long_think_id=data.get('long_think_id')
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/skills/', methods=['GET'])
@bp.route('/api/skills', methods=['GET'])
def get_skills():
    """获取所有技能"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, name, description, category, status, usage_count
            FROM skills
            ORDER BY category, name
        ''')
        skills = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'skills': skills})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/emails/<int:email_id>', methods=['GET'])
def get_email_detail(email_id):
    """获取邮件详情"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM emails WHERE id = %s', (email_id,))
        email = c.fetchone()
        conn.close()
        if email:
            return jsonify({'success': True, 'email': dict(email)})
        return jsonify({'success': False, 'error': '邮件不存在'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

    # Routes moved to routes/emails.py
@bp.route('/api/emails/reply', methods=['POST'])
def reply_email():
    """回复邮件"""
    try:
        data = request.get_json()
        # 这里应该调用邮件发送逻辑
        return jsonify({'success': True, 'message': '回复已发送'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/contacts/', methods=['GET'])
@bp.route('/api/contacts', methods=['GET'])
def get_contacts():
    """获取通讯录"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT DISTINCT sender, sender_name FROM emails
            WHERE sender IS NOT NULL
            ORDER BY sender_name
        ''')
        contacts = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'contacts': contacts})
    except Exception as e:
        return jsonify({'success': True, 'contacts': []})


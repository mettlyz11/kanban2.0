"""Routes: emails"""
from flask import Blueprint, jsonify, request
import json
import os
from routes.helpers import get_db, row_to_dict
from datetime import datetime

bp = Blueprint('routes_emails', __name__)

@bp.route('/api/emails/<int:email_id>/read', methods=['POST'])
def mark_email_as_read(email_id):
    """标记邮件为已读"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('UPDATE emails SET is_read = 1 WHERE id = %s', (email_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '邮件已标记为已读'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/emails/<int:email_id>', methods=['DELETE'])
def delete_email(email_id):
    """删除邮件"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM emails WHERE id = %s', (email_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '邮件已删除'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/emails', methods=['GET'])
def get_emails():
    """获取邮件列表"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, message_id, subject, sender, sender_name, recipient,
                   folder, is_read, is_important, received_at as date,
                   SUBSTRING(body, 1, 200) as preview
            FROM emails
            ORDER BY received_at DESC
            LIMIT 100
        ''')
        emails = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'emails': emails})
    except Exception as e:
        print(f"[ERROR] get_emails: {e}")
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/emails/stats', methods=['GET'])
def get_email_stats():
    """获取邮件统计"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        c.execute('SELECT COUNT(*) as total FROM emails')
        result = c.fetchone()
        total = result['total']
    
        c.execute('SELECT COUNT(*) as unread FROM emails WHERE is_read = 0')
        result = c.fetchone()
        unread = result['unread']
    
        c.execute('SELECT COUNT(*) as important FROM emails WHERE is_important = 1')
        result = c.fetchone()
        important = result['important']
    
        # 按文件夹统计数量（前端需要这个显示各文件夹）
        c.execute('SELECT folder, COUNT(*) as count FROM emails GROUP BY folder')
        folder_stats = {}
        for row in c.fetchall():
            folder_stats[row['folder']] = row['count']
    
        conn.close()
    
        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'unread': unread,
                'important': important,
                'folders': folder_stats
            }
        })
    except Exception as e:
        print(f"[ERROR] get_email_stats: {e}")
        return jsonify({'success': False, 'error': str(e)})

# SPA 前端路由支持 - 所有非API路由返回index.html
# ============================================




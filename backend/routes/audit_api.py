"""Routes: audit_api - audit_api"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db, row_to_dict
import os
import json
from datetime import datetime

bp = Blueprint("routes_audit_api", __name__)
logger = __import__("logging").getLogger(__name__)

@bp.route('/api/audit/tasks/pending', methods=['GET'])
def get_pending_audit_tasks():
    """获取待审核任务列表"""
    try:
        source = request.args.get('source')
        conn = get_db()
        c = conn.cursor()
    
        if source:
            c.execute('''
                SELECT 
                    m.id,
                    m.task_type,
                    m.title,
                    m.description,
                    m.source,
                    m.status,
                    m.priority,
                    m.completion_notes as notes,
                    m.created_at,
                    m.completed_at,
                    m.completed_by as reviewer,
                    m.is_from_long_think,
                    m.original_task_id as source_id
                FROM manual_review_tasks m
                WHERE m.status = 'pending' AND m.task_type = %s
                ORDER BY 
                    CASE m.priority 
                        WHEN 'high' THEN 1 
                        WHEN 'medium' THEN 2 
                        ELSE 3 
                    END,
                    m.created_at DESC
            ''', (source,))
        else:
            c.execute('''
                SELECT 
                    m.id,
                    m.task_type,
                    m.title,
                    m.description,
                    m.source,
                    m.status,
                    m.priority,
                    m.completion_notes as notes,
                    m.created_at,
                    m.completed_at,
                    m.completed_by as reviewer,
                    m.is_from_long_think,
                    m.original_task_id as source_id
                FROM manual_review_tasks m
                WHERE m.status = 'pending'
                ORDER BY 
                    CASE m.priority 
                        WHEN 'high' THEN 1 
                        WHEN 'medium' THEN 2 
                        ELSE 3 
                    END,
                    m.created_at DESC
            ''')
    
        tasks = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
    
        return jsonify({
            'success': True,
            'count': len(tasks),
            'tasks': tasks
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/audit/tasks/<int:audit_id>/approve', methods=['POST'])
def approve_audit_task(audit_id):
    """批准任务"""
    try:
        data = request.get_json() or {}
        reviewer = data.get('reviewer', 'system')
        notes = data.get('notes', '审核通过')
    
        conn = get_db()
        c = conn.cursor()
    
        # 获取关联的任务ID
        c.execute('SELECT original_task_id FROM manual_review_tasks WHERE id = %s', (audit_id,))
        row = c.fetchone()
        original_task_id = row[0] if row else None
    
        # 更新审核任务状态
        c.execute('''
            UPDATE manual_review_tasks 
            SET status = 'approved', completed_by = %s, completion_notes = %s, completed_at = NOW()
            WHERE id = %s
        ''', (reviewer, notes, audit_id))
    
        # 更新原始任务状态
        if original_task_id:
            c.execute('''
                UPDATE tasks 
                SET audit_status = 'approved', updated_at = NOW()
                WHERE id = %s
            ''', (original_task_id,))
    
        conn.commit()
        conn.close()
    
        return jsonify({
            'success': True,
            'message': '任务已批准',
            'task_id': original_task_id,
            'audit_id': audit_id
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/audit/tasks/<int:audit_id>/reject', methods=['POST'])
def reject_audit_task(audit_id):
    """拒绝任务"""
    try:
        data = request.get_json() or {}
        reviewer = data.get('reviewer', 'system')
        reason = data.get('reason', data.get('notes', '审核未通过'))
    
        conn = get_db()
        c = conn.cursor()
    
        # 获取关联的任务ID
        c.execute('SELECT original_task_id FROM manual_review_tasks WHERE id = %s', (audit_id,))
        row = c.fetchone()
        original_task_id = row[0] if row else None
    
        # 更新审核任务状态
        c.execute('''
            UPDATE manual_review_tasks 
            SET status = 'rejected', completed_by = %s, completion_notes = %s, completed_at = NOW()
            WHERE id = %s
        ''', (reviewer, reason, audit_id))
    
        # 更新原始任务状态
        if original_task_id:
            c.execute('''
                UPDATE tasks 
                SET audit_status = 'rejected', status = 'cancelled', updated_at = NOW()
                WHERE id = %s
            ''', (original_task_id,))
    
        conn.commit()
        conn.close()
    
        return jsonify({
            'success': True,
            'message': '任务已拒绝',
            'task_id': original_task_id,
            'audit_id': audit_id
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/audit/tasks/<int:task_id>/check', methods=['GET'])
def check_task_audit_status(task_id):
    """检查任务审核状态"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        c.execute('''
            SELECT id, title, requires_audit, audit_status, status
            FROM tasks 
            WHERE id = %s
        ''', (task_id,))
    
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({
                'success': False,
                'error': '任务不存在'
            }), 404
    
        task = row_to_dict(row, c)
        requires_audit = task.get('requires_audit', 0)
        audit_status = task.get('audit_status') or 'pending'
    
        can_execute = False
        message = ''
    
        if not requires_audit:
            can_execute = True
            message = '任务不需要审核'
        elif audit_status == 'approved':
            can_execute = True
            message = '审核已通过'
        elif audit_status == 'rejected':
            can_execute = False
            message = '任务已被拒绝'
        else:
            can_execute = False
            message = '任务待审核'
    
        conn.close()
    
        return jsonify({
            'success': True,
            'task_id': task_id,
            'can_execute': can_execute,
            'status': audit_status,
            'message': message
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/audit/tasks/stats', methods=['GET'])
def get_audit_stats():
    """获取审核统计"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        c.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
            FROM manual_review_tasks
        ''')
    
        row = c.fetchone()
        stats = row_to_dict(row, c) if row else {}
    
        # 按来源统计
        c.execute('''
            SELECT task_type, COUNT(*) as count
            FROM manual_review_tasks
            GROUP BY task_type
        ''')
    
        by_source = {row[0]: row['count'] for row in c.fetchall()}
    
        conn.close()
    
        return jsonify({
            'success': True,
            'stats': {
                'total': stats.get('total', 0),
                'pending': stats.get('pending', 0),
                'approved': stats.get('approved', 0),
                'rejected': stats.get('rejected', 0),
                'by_source': by_source
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/audit/dashboard', methods=['GET'])
def get_audit_dashboard():
    """获取审核仪表板数据"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        # 总体统计
        c.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
            FROM manual_review_tasks
        ''')
    
        row = c.fetchone()
        stats = row_to_dict(row, c) if row else {}
    
        # 按优先级统计待审核
        c.execute('''
            SELECT 
                priority,
                COUNT(*) as count
            FROM manual_review_tasks
            WHERE status = 'pending'
            GROUP BY priority
        ''')
    
        by_priority = {row[0]: row['count'] for row in c.fetchall()}
    
        # 最近10个待审核
        c.execute('''
            SELECT 
                id,
                title,
                priority,
                task_type,
                created_at
            FROM manual_review_tasks
            WHERE status = 'pending'
            ORDER BY created_at DESC
            LIMIT 10
        ''')
    
        recent_pending = [row_to_dict(row, c) for row in c.fetchall()]
    
        conn.close()
    
        return jsonify({
            'success': True,
            'dashboard': {
                'summary': {
                    'total': stats.get('total', 0),
                    'pending': stats.get('pending', 0),
                    'approved': stats.get('approved', 0),
                    'rejected': stats.get('rejected', 0),
                    'by_priority': by_priority
                },
                'recent_pending': recent_pending,
                'timestamp': datetime.now().isoformat()
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/file-content', methods=['GET'])
def get_file_content_by_query():
    """通过 query 参数获取文件内容"""
    try:
        type_param = request.args.get('type', 'personal')
        name = request.args.get('name', '')
        format_type = request.args.get('format', 'raw')
        
        # 构建文件路径
        if type_param == 'personal':
            # 人员档案路径: Files/Personal/刘宇宙.md
            filepath = f'文档/个人信息/{name}.md'
        elif type_param == 'company':
            # 公司档案路径: Files/Companies/和光智成.md
            filepath = f'文档/公司信息/{name}.md'
        else:
            return jsonify({'success': False, 'error': '无效的类型'})
        
        workspace_path = '/opt/kanban-react/Files'
        full_path = os.path.join(workspace_path, filepath)
        
        # 安全检查
        if not full_path.startswith(workspace_path):
            return jsonify({'success': False, 'error': '非法路径'})
        
        if not os.path.exists(full_path):
            return jsonify({'success': False, 'error': '文件不存在', 'data': ''})
        
        # 限制文件大小
        if os.path.getsize(full_path) > 1024 * 1024:
            return jsonify({'success': False, 'error': '文件过大'})
        
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 解析内容
        if format_type == 'parsed':
            # 简单的解析：提取标题和段落
            lines = content.split("\n")
            parsed = {
                'title': '',
                'sections': []
            }
            current_section = None
            
            for line in lines:
                if line.startswith('# '):
                    parsed['title'] = line[2:].strip()
                elif line.startswith('## '):
                    if current_section:
                        parsed['sections'].append(current_section)
                    current_section = {
                        'title': line[3:].strip(),
                        'content': []
                    }
                elif current_section and line.strip():
                    current_section['content'].append(line)
            
            if current_section:
                parsed['sections'].append(current_section)
            
            return jsonify({'success': True, 'data': parsed})
        else:
            return jsonify({'success': True, 'data': content})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("=" * 60)
    print("Kanban React - Flask API Server")
    print("=" * 60)
    print("API地址: http://localhost:8086")
    print("=" * 60)

    # 记录系统启动事件
    try:
        perception_recorder.record_event(
            event_type='system_startup',
            severity='info',
            source='backend',
            message='看板系统后端服务启动',
            metadata={'version': 'v2.4.12', 'port': 8086, 'host': '0.0.0.0'}
        )
        print("✅ 系统启动事件已记录到感知监控")
    except Exception as e:
        print(f"⚠️ 记录启动事件失败: {e}")

    # 启动感知Agent
    init_perception_agent()

    # 启动P049-T041监控告警系统
    try:
        from p049_monitoring import init_monitoring, stop_monitoring
        alert_manager, monitoring_dashboard = init_monitoring()
        print("✅ P049-T041 监控告警系统已启动")
    except Exception as e:
        print(f"⚠️ 监控告警系统启动失败: {e}")
        alert_manager = None

    # 启动Flask服务 (支持 WebSocket)
    try:
        if socketio:
            socketio.run(app, host='0.0.0.0', port=8086, debug=False, allow_unsafe_werkzeug=True)
        else:
            app.run(host='0.0.0.0', port=8086, debug=False)
    finally:
        # 确保感知Agent正确停止
        if PERCEPTION_AGENT_AVAILABLE:
            stop_perception_agent()
            print("\n✅ PerceptionAgent stopped")
        # 停止监控告警系统
        if alert_manager:
            stop_monitoring()
            print("✅ P049-T041 监控告警系统已停止")
        
        # 关闭 WebSocket
        if WEBSOCKET_AVAILABLE:
            try:
                shutdown_socketio()
                print("✅ WebSocket 服务已关闭")
            except Exception as e:
                print(f"⚠️ WebSocket 关闭异常: {e}")



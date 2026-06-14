"""Routes: calendar_api - calendar_api"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db, row_to_dict
import os
import json
from datetime import datetime

bp = Blueprint("routes_calendar_api", __name__)
logger = __import__("logging").getLogger(__name__)

@bp.route('/api/calendar/accounts', methods=['POST'])
def create_calendar_account():
    """创建CalDAV账户"""
    try:
        data = request.get_json()
    
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO calendar_accounts
            (name, account_type, server_url, username, password, calendar_path, calendar_name, sync_enabled)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('name'),
            data.get('account_type', 'caldav'),
            data.get('server_url'),
            data.get('username'),
            data.get('password'),
            data.get('calendar_path', '/'),
            data.get('calendar_name'),
            1
        ))
    
        conn.commit()
        account_id = c.lastrowid
        conn.close()
    
        return jsonify({'success': True, 'id': account_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

    # Routes moved to routes/calendar.py
@bp.route('/api/calendar/events', methods=['POST'])
def create_calendar_event():
    """创建日历事件"""
    try:
        data = request.get_json()
        from datetime import datetime, timedelta
    
        conn = get_db()
        c = conn.cursor()
    
        c.execute('''
            INSERT INTO calendar_events 
            (id, title, description, start_time, end_time, is_all_day, location, 
             category, event_color, reminder_minutes, participants, meeting_minutes_id, 
             recurrence
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('id', 'evt_' + datetime.now().strftime('%Y%m%d%H%M%S')),
            data.get('title'),
            data.get('description'),
            data.get('start_time'),
            data.get('end_time'),
            data.get('is_all_day', 0),
            data.get('location'),
            data.get('category', 'default'),
            data.get('color', '#667eea'),
            data.get('reminder_minutes', 15),
            data.get('participants'),
            data.get('meeting_minutes_id'),
            data.get('recurrence'),
            datetime.now().isoformat()
        ))
    
        conn.commit()
        event_id = c.lastrowid
        conn.close()
    
        return jsonify({'success': True, 'id': event_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

    # Routes moved to routes/calendar.py
@bp.route('/api/calendar/events/<event_id>', methods=['DELETE', 'OPTIONS'])
def delete_calendar_event(event_id):
    """删除日历事件（支持CORS预检）"""
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'DELETE, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    # DELETE 方法处理
    try:
        conn = get_db()
        c = conn.cursor()
    
        # 硬删除（因为表中没有status字段）
        c.execute('''
            DELETE FROM calendar_events 
            WHERE id = %s
        ''', (event_id,))
    
        conn.commit()
        conn.close()
    
        return jsonify({'success': True, 'message': '日程已删除'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

    # Routes moved to routes/calendar.py
@bp.route('/api/calendar/settings', methods=['GET'])
def get_calendar_settings():
    """获取日历设置"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM calendar_settings WHERE id = 1')
        row = c.fetchone()
        conn.close()
    
        if row:
            settings = {
                'default_view': row['default_view'],
                'first_day_of_week': row['first_day_of_week'],
                'show_weekends': bool(row['show_weekends']),
                'working_hours_start': row['working_hours_start'],
                'working_hours_end': row['working_hours_end'],
                'default_reminder_minutes': row['default_reminder_minutes'],
                'enable_notifications': bool(row['enable_notifications']),
                'notification_sound': bool(row['notification_sound']),
                'sync_enabled': bool(row['sync_enabled']),
                'sync_interval_minutes': row['sync_interval_minutes'],
                'default_calendar_color': row['default_calendar_color']
            }
            return jsonify({'success': True, 'settings': settings})
        else:
            # 返回默认设置
            return jsonify({
                'success': True, 
                'settings': {
                    'default_view': 'month',
                    'first_day_of_week': 0,
                    'show_weekends': True,
                    'working_hours_start': '09:00',
                    'working_hours_end': '18:00',
                    'default_reminder_minutes': 15,
                    'enable_notifications': True,
                    'notification_sound': True,
                    'sync_enabled': False,
                    'sync_interval_minutes': 30,
                    'default_calendar_color': '#667eea'
                }
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

    # Routes moved to routes/calendar.py
@bp.route('/api/meetings/', methods=['GET'])  # 支持尾部斜杠
@bp.route('/api/meetings/', methods=['GET'])
@bp.route('/api/meetings', methods=['GET'])
def get_meetings():
    """获取会议纪要列表"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        limit = request.args.get('limit', 50, type=int)
    
        c.execute('''
            SELECT id, title, date, time, participants, summary, content, action_items, created_at
            FROM meetings
            ORDER BY date DESC, time DESC
            LIMIT %s
        ''', (limit,))
    
        meetings = []
        for row in c.fetchall():
            meetings.append({
                'id': row['id'],
                'title': row['title'],
                'date': row['date'],
                'time': row['time'],
                'participants': row['participants'],
                'summary': row['summary'],
                'content': row['content'],
                'action_items': parse_action_items(row['action_items']),
                'created_at': row['created_at']
            })
    
        conn.close()
    
        return jsonify({
            'success': True,
            'meetings': meetings,
            'count': len(meetings)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/meetings/<int:meeting_id>', methods=['GET'])
def get_meeting(meeting_id):
    """获取单个会议纪要详情"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        c.execute('''
            SELECT id, title, date, time, participants, summary, content, action_items, created_at
            FROM meetings
            WHERE id = %s
        ''', (meeting_id,))
    
        row = c.fetchone()
        conn.close()
    
        if not row:
            return jsonify({'success': False, 'error': '会议纪要不存在'}), 404
    
        meeting = {
            'id': row['id'],
            'title': row['title'],
            'date': row['date'],
            'time': row['time'],
            'participants': row['participants'],
            'summary': row['summary'],
            'content': row['content'],
            'action_items': parse_action_items(row['action_items']),
            'created_at': row['created_at']
        }

        return jsonify({'success': True, 'meeting': meeting})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/meetings', methods=['POST'])
def create_meeting():
    """创建会议纪要"""
    try:
        data = request.get_json()
    
        if not data.get('title') or not data.get('date'):
            return jsonify({'success': False, 'error': '标题和日期不能为空'}), 400
    
        conn = get_db()
        c = conn.cursor()
    
        c.execute('''
            INSERT INTO meetings (title, date, time, participants, summary, content, action_items)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('title'),
            data.get('date'),
            data.get('time', ''),
            data.get('participants', ''),
            data.get('summary', ''),
            data.get('content', ''),
            json.dumps(data.get('action_items', []))
        ))
    
        meeting_id = c.lastrowid
        conn.commit()
        conn.close()
    
        return jsonify({
            'success': True,
            'id': meeting_id,
            'message': '会议纪要创建成功'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/meetings/<int:meeting_id>', methods=['PUT'])
def update_meeting(meeting_id):
    """更新会议纪要"""
    try:
        data = request.get_json()
    
        conn = get_db()
        c = conn.cursor()
    
        # 检查是否存在
        c.execute('SELECT id FROM meetings WHERE id = %s', (meeting_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '会议纪要不存在'}), 404
    
        c.execute('''
            UPDATE meetings SET
                title = COALESCE(%s, title),
                date = COALESCE(%s, date),
                time = COALESCE(%s, time),
                participants = COALESCE(%s, participants),
                summary = COALESCE(%s, summary),
                content = COALESCE(%s, content),
                action_items = COALESCE(%s, action_items),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (
            data.get('title'),
            data.get('date'),
            data.get('time'),
            data.get('participants'),
            data.get('summary'),
            data.get('content'),
            json.dumps(data.get('action_items')) if data.get('action_items') is not None else None,
            meeting_id
        ))
    
        conn.commit()
        conn.close()
    
        return jsonify({'success': True, 'message': '会议纪要更新成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/meetings/<int:meeting_id>', methods=['DELETE'])
def delete_meeting(meeting_id):
    """删除会议纪要"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        c.execute('DELETE FROM meetings WHERE id = %s', (meeting_id,))
    
        if c.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': '会议纪要不存在'}), 404
    
        conn.commit()
        conn.close()
    
        return jsonify({'success': True, 'message': '会议纪要已删除'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


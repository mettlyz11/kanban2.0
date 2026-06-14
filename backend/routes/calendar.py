"""Routes: calendar"""
from flask import Blueprint, jsonify, request
import json
import os
from routes.helpers import get_db, row_to_dict
from datetime import datetime

bp = Blueprint('routes_calendar', __name__)

@bp.route('/api/calendar/accounts', methods=['GET'])
def get_calendar_accounts():
    """获取CalDAV账户列表"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id, name, account_type, server_url, username, calendar_name, sync_enabled, last_sync_at FROM calendar_accounts')
        accounts = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'accounts': accounts})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/calendar/sync', methods=['POST'])
def sync_calendar():
    """手动同步日历"""
    try:
        from caldav_sync import sync_all_accounts
    
        results = sync_all_accounts(DB_PATH)
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/calendar/events', methods=['GET'])
def get_calendar_events():
    """获取日历事件"""
    try:
        start = request.args.get('start')
        end = request.args.get('end')
    
        conn = get_db()
        c = conn.cursor()
    
        query = '''
            SELECT * FROM calendar_events
            WHERE 1=1
        '''
        params = []
    
        if start:
            query += ' AND end_time >= %s'
            params.append(start)
        if end:
            query += ' AND start_time <= %s'
            params.append(end)
        
        query += ' ORDER BY start_time'
    
        c.execute(query, tuple(params))
        events = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
    
        return jsonify({'success': True, 'events': events})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/calendar/events/<event_id>', methods=['PUT'])
def update_calendar_event(event_id):
    """更新日历事件"""
    try:
        data = request.get_json()
    
        conn = get_db()
        c = conn.cursor()
    
        # 获取现有数据
        c.execute('SELECT * FROM calendar_events WHERE id = %s', (event_id,))
        existing = c.fetchone()
        if not existing:
            return jsonify({'success': False, 'error': '事件不存在'})
    
        # 更新字段
        c.execute('''
            UPDATE calendar_events SET
                title = %s,
                description = %s,
                start_time = %s,
                end_time = %s,
                all_day = %s,
                location = %s,
                category = %s,
                event_color = %s,
                reminder_minutes = %s,
                status = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (
            data.get('title', existing['title']),
            data.get('description', existing['description']),
            data.get('start_time', existing['start_time']),
            data.get('end_time', existing['end_time']),
            data.get('all_day', existing['all_day']),
            data.get('location', existing['location']),
            data.get('category', existing['category']),
            data.get('event_color', existing['color']),
            data.get('reminder_minutes', existing['reminder_minutes']),
            data.get('status', existing['status']),
            event_id
        ))
    
        conn.commit()
        conn.close()
    
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/calendar/stats', methods=['GET'])
def get_calendar_stats():
    """获取日历统计"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        # 今日事件数
        c.execute('''
            SELECT COUNT(*) FROM calendar_events
            WHERE date(start_time) = date('now')
        ''')
        today_count = list(c.fetchone().values())[0]
    
        # 本周事件数
        c.execute('''
            SELECT COUNT(*) FROM calendar_events
            WHERE start_time >= date('now', 'weekday 0', '-7 days')
            AND start_time < date('now', 'weekday 0', '0 days')
        ''')
        week_count = list(c.fetchone().values())[0]
    
        # 本月事件数
        c.execute('''
            SELECT COUNT(*) FROM calendar_events
            WHERE strftime('%Y-%m', start_time) = strftime('%Y-%m', 'now')
        ''')
        month_count = list(c.fetchone().values())[0]
    
        # 待处理事件（未来）
        c.execute('''
            SELECT COUNT(*) FROM calendar_events
            WHERE start_time > NOW()
        ''')
        upcoming_count = list(c.fetchone().values())[0]
    
        conn.close()
    
        return jsonify({
            'success': True,
            'stats': {
                'today': today_count,
                'week': week_count,
                'month': month_count,
                'upcoming': upcoming_count
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 日历设置 API
# ============================================


@bp.route('/api/calendar/settings', methods=['POST'])
def update_calendar_settings():
    """更新日历设置"""
    try:
        data = request.get_json()
    
        conn = get_db()
        c = conn.cursor()
    
        # 确保设置记录存在
        c.execute('INSERT OR IGNORE INTO calendar_settings (id) VALUES (1)')
    
        # 更新设置
        update_fields = []
        params = []
    
        field_mapping = {
            'default_view': 'default_view',
            'first_day_of_week': 'first_day_of_week',
            'show_weekends': 'show_weekends',
            'working_hours_start': 'working_hours_start',
            'working_hours_end': 'working_hours_end',
            'default_reminder_minutes': 'default_reminder_minutes',
            'enable_notifications': 'enable_notifications',
            'notification_sound': 'notification_sound',
            'sync_enabled': 'sync_enabled',
            'sync_interval_minutes': 'sync_interval_minutes',
            'default_calendar_color': 'default_calendar_color'
        }
    
        for api_field, db_field in field_mapping.items():
            if api_field in data:
                update_fields.append(f"{db_field} = %s")
                value = data[api_field]
                # 转换布尔值为整数
                if isinstance(value, bool):
                    value = 1 if value else 0
                params.append(value)
    
        if update_fields:
            params.append(1)  # id = 1
            query = f"UPDATE calendar_settings SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
            c.execute(query, tuple(params))
    
        conn.commit()
        conn.close()
    
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 会议纪要 API
# ============================================



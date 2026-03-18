#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/kanban-react/backend')

from datetime import datetime, timedelta
import pymysql
from database_config import DB_CONFIG

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def get_upcoming_events(hours_ahead: int):
    """获取未来N小时的事件"""
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    now = datetime.now()
    target_start = now + timedelta(hours=hours_ahead)
    target_end = target_start + timedelta(hours=1)
    
    sql = '''
        SELECT id, title, start_time, end_time, location, description
        FROM calendar_events
        WHERE start_time BETWEEN %s AND %s
        AND status = 'confirmed'
    '''
    
    cursor.execute(sql, (target_start, target_end))
    events = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return events

def get_today_events():
    """获取今日所有事件"""
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    
    sql = '''
        SELECT id, title, start_time, end_time, location, description
        FROM calendar_events
        WHERE start_time BETWEEN %s AND %s
        AND status = 'confirmed'
        ORDER BY start_time
    '''
    
    cursor.execute(sql, (today, tomorrow))
    events = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return events

def format_event_message(event, reminder_type=''):
    """格式化事件消息"""
    title = event.get('title', '无标题')
    start_time = event.get('start_time')
    location = event.get('location', '')
    description = event.get('description', '')
    
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time.replace(' ', 'T'))
    
    time_str = start_time.strftime('%Y-%m-%d %H:%M')
    
    if reminder_type == '24h':
        emoji = '⏰'
        prefix = '24小时后'
    elif reminder_type == '1h':
        emoji = '🔔'
        prefix = '1小时后'
    else:
        emoji = '📅'
        prefix = '今日'
    
    message = f"""{emoji} **{prefix}开始: {title}**

📅 **时间:** {time_str}
"""
    
    if location:
        message += f"📍 **地点:** {location}\n"
    if description:
        message += f"📝 **描述:** {description}\n"
    
    message += "\n[查看详情](http://47.93.184.128/calendar)"
    
    return message

def send_feishu_message(message):
    """发送飞书消息（这里可以集成飞书API）"""
    print(f"[飞书消息]\n{message}\n{'='*50}")

def check_24h_reminders():
    """检查24小时提醒"""
    print(f"[{datetime.now()}] 检查24小时提醒...")
    events = get_upcoming_events(24)
    
    for event in events:
        message = format_event_message(event, '24h')
        send_feishu_message(message)

def check_1h_reminders():
    """检查1小时提醒"""
    print(f"[{datetime.now()}] 检查1小时提醒...")
    events = get_upcoming_events(1)
    
    for event in events:
        message = format_event_message(event, '1h')
        send_feishu_message(message)

def send_daily_summary():
    """发送每日汇总"""
    print(f"[{datetime.now()}] 发送每日汇总...")
    events = get_today_events()
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    if not events:
        message = f"📅 **今日事件汇总 ({today_str})**\n\n今天没有安排的事件。"
    else:
        message = f"📅 **今日事件汇总 ({today_str})**\n\n共 **{len(events)}** 个事件\n\n"
        
        for i, event in enumerate(events, 1):
            title = event.get('title', '无标题')
            start_time = event.get('start_time')
            location = event.get('location', '')
            
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace(' ', 'T'))
            
            time_str = start_time.strftime('%H:%M')
            
            message += f"{i}. **{time_str}** - {title}"
            if location:
                message += f" 📍{location}"
            message += "\n"
    
    message += "\n[查看完整日历](http://47.93.184.128/calendar)"
    send_feishu_message(message)

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == '24h':
            check_24h_reminders()
        elif cmd == '1h':
            check_1h_reminders()
        elif cmd == 'daily':
            send_daily_summary()
        else:
            print('用法: python calendar_reminder.py [24h|1h|daily]')
    else:
        # 默认执行所有检查
        check_24h_reminders()
        check_1h_reminders()

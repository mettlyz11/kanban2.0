#!/usr/bin/env python3
"""
日历事件提醒系统 - OpenClaw飞书通道版 (SQLite版本)
使用 OpenClaw 的 message 工具发送飞书通知

部署：/opt/kanban-react/backend/scripts/calendar_reminder_openclaw.py
Cron:
- 0 * * * *  (每小时检查24小时提醒)
- */10 * * * * (每10分钟检查1小时提醒)
- 0 8 * * * (每天早上8点发送汇总)
"""

import sys
import os
import subprocess
import json
import sqlite3

sys.path.insert(0, '/opt/kanban-react/backend')

from datetime import datetime, timedelta

# 数据库配置 - 使用本地 SQLite
DB_PATH = '/opt/kanban-react/backend/kanban_v5.db'

# OpenClaw 配置
FEISHU_CHAT_ID = os.getenv('FEISHU_CHAT_ID', '')


class OpenClawNotifier:
    """OpenClaw 通知器"""
    
    def send_message(self, content: str):
        """通过 OpenClaw 发送飞书消息"""
        try:
            # 使用 OpenClaw CLI 发送消息
            cmd = [
                'openclaw', 'message', 'send',
                '--channel', 'feishu',
                '--message', content
            ]
            
            if FEISHU_CHAT_ID:
                cmd.extend(['--target', FEISHU_CHAT_ID])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"✅ 消息发送成功")
                return True
            else:
                print(f"❌ 发送失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 发送异常: {e}")
            # 备用：直接打印消息
            print(f"\n{'='*60}")
            print(f"[飞书消息 - 备用输出]")
            print(f"{'='*60}")
            print(content)
            print(f"{'='*60}\n")
            return True


class CalendarReminder:
    """日历提醒器"""
    
    def __init__(self):
        self.notifier = OpenClawNotifier()
        self.reminder_cache = set()
    
    def get_db_connection(self):
        """获取 SQLite 数据库连接"""
        return sqlite3.connect(DB_PATH)
    
    def get_events_in_range(self, start: datetime, end: datetime):
        """获取时间范围内的事件"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        sql = '''
            SELECT id, title, start_time, end_time, location, description
            FROM calendar_events
            WHERE start_time BETWEEN ? AND ?
            AND status = 'confirmed'
            ORDER BY start_time
        '''
        
        cursor.execute(sql, (start.isoformat(), end.isoformat()))
        rows = cursor.fetchall()
        
        # 转换为字典列表
        events = []
        for row in rows:
            events.append({
                'id': row[0],
                'title': row[1],
                'start_time': row[2],
                'end_time': row[3],
                'location': row[4],
                'description': row[5]
            })
        
        cursor.close()
        conn.close()
        
        return events
    
    def format_event_message(self, event: dict, reminder_type: str) -> str:
        """格式化事件消息"""
        title = event.get('title', '无标题')
        start_time = event.get('start_time', '')
        location = event.get('location', '')
        description = event.get('description', '')
        
        # 解析时间
        if isinstance(start_time, str):
            try:
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except:
                pass
        
        if isinstance(start_time, datetime):
            time_str = start_time.strftime('%Y-%m-%d %H:%M')
        else:
            time_str = str(start_time)
        
        # 根据提醒类型选择表情
        if reminder_type == '24h':
            emoji = '⏰'
            prefix = '24小时后'
        elif reminder_type == '1h':
            emoji = '🔔'
            prefix = '1小时后'
        else:
            emoji = '📅'
            prefix = '今日'
        
        # 构建消息
        message = f"{emoji} **{prefix}开始: {title}**\n\n"
        message += f"📅 **时间:** {time_str}\n"
        
        if location:
            message += f"📍 **地点:** {location}\n"
        if description:
            message += f"📝 **描述:** {description}\n"
        
        message += f"\n👉 [查看日历](http://47.93.184.128/calendar)"
        
        return message
    
    def send_reminder(self, event: dict, reminder_type: str):
        """发送提醒"""
        event_id = event.get('id')
        cache_key = f"{reminder_type}_{event_id}_{datetime.now().strftime('%Y%m%d%H')}"
        
        if cache_key in self.reminder_cache:
            return
        
        message = self.format_event_message(event, reminder_type)
        self.notifier.send_message(message)
        
        self.reminder_cache.add(cache_key)
        print(f"✅ 已发送 {reminder_type} 提醒: {event.get('title')}")
    
    def check_24h_reminders(self):
        """检查24小时提醒"""
        print(f"\n[{datetime.now()}] 检查24小时提醒...")
        
        now = datetime.now()
        target_start = now + timedelta(hours=24)
        target_end = target_start + timedelta(minutes=59)
        
        events = self.get_events_in_range(target_start, target_end)
        
        for event in events:
            self.send_reminder(event, '24h')
        
        print(f"找到 {len(events)} 个事件")
    
    def check_1h_reminders(self):
        """检查1小时提醒"""
        print(f"\n[{datetime.now()}] 检查1小时提醒...")
        
        now = datetime.now()
        target_start = now + timedelta(hours=1)
        target_end = target_start + timedelta(minutes=59)
        
        events = self.get_events_in_range(target_start, target_end)
        
        for event in events:
            self.send_reminder(event, '1h')
        
        print(f"找到 {len(events)} 个事件")
    
    def send_daily_summary(self):
        """发送每日汇总"""
        print(f"\n[{datetime.now()}] 发送每日汇总...")
        
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        events = self.get_events_in_range(today_start, today_end)
        
        today_str = now.strftime('%Y年%m月%d日')
        
        if not events:
            message = f"📅 **今日事件汇总 ({today_str})**\n\n今天没有安排的事件。"
            self.notifier.send_message(message)
            print("✅ 已发送空汇总")
            return
        
        # 构建汇总消息
        message = f"📅 **今日事件汇总 ({today_str})**\n\n"
        message += f"共 **{len(events)}** 个事件\n\n"
        
        for i, event in enumerate(events, 1):
            title = event.get('title', '无标题')
            start_time = event.get('start_time', '')
            location = event.get('location', '')
            
            # 解析时间
            if isinstance(start_time, str):
                try:
                    start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                except:
                    pass
            
            if isinstance(start_time, datetime):
                time_str = start_time.strftime('%H:%M')
            else:
                time_str = str(start_time)
            
            message += f"{i}. **{time_str}** {title}"
            if location:
                message += f" 📍{location}"
            message += "\n"
        
        message += f"\n👉 [查看完整日历](http://47.93.184.128/calendar)"
        
        self.notifier.send_message(message)
        print(f"✅ 已发送今日 {len(events)} 个事件的汇总")


def main():
    """主函数"""
    import sys
    
    reminder = CalendarReminder()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == '24h':
            reminder.check_24h_reminders()
        elif cmd == '1h':
            reminder.check_1h_reminders()
        elif cmd == 'daily':
            reminder.send_daily_summary()
        else:
            print('用法: python calendar_reminder_openclaw.py [24h|1h|daily]')
            print('')
            print('命令说明:')
            print('  24h   - 检查24小时前的提醒')
            print('  1h    - 检查1小时前的提醒')
            print('  daily - 发送今日事件汇总')
    else:
        # 默认执行所有检查
        reminder.check_24h_reminders()
        reminder.check_1h_reminders()


if __name__ == '__main__':
    main()

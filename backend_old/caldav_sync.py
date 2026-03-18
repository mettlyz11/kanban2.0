#!/usr/bin/env python3
"""
CalDAV同步模块
用于与iPhone/Mac日历同步
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sqlite3
import os

# CalDAV命名空间
NAMESPACES = {
    'd': 'DAV:',
    'c': 'urn:ietf:params:xml:ns:caldav',
    'cs': 'http://calendarserver.org/ns/'
}

class CalDAVClient:
    """CalDAV客户端"""
    
    def __init__(self, server_url: str, username: str, password: str):
        self.server_url = server_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({
            'Content-Type': 'application/xml; charset=utf-8',
            'User-Agent': 'Kanban-Calendar/1.0'
        })
    
    def discover_calendars(self) -> List[Dict]:
        """发现可用的日历"""
        try:
            # 发送PROPFIND请求发现日历
            propfind_xml = '''<?xml version="1.0" encoding="utf-8"?>
            <d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
                <d:prop>
                    <d:displayname/>
                    <c:calendar-description/>
                    <c:supported-calendar-component-set/>
                </d:prop>
            </d:propfind>'''
            
            response = self.session.request(
                'PROPFIND',
                f"{self.server_url}/calendars/{self.username}/",
                data=propfind_xml,
                headers={'Depth': '1'}
            )
            
            if response.status_code == 207:  # Multi-Status
                return self._parse_calendar_list(response.text)
            
            return []
        except Exception as e:
            print(f"发现日历失败: {e}")
            return []
    
    def _parse_calendar_list(self, xml_response: str) -> List[Dict]:
        """解析日历列表响应"""
        calendars = []
        root = ET.fromstring(xml_response)
        
        for response in root.findall('.//{DAV:}response'):
            href = response.find('.//{DAV:}href')
            displayname = response.find('.//{DAV:}displayname')
            
            if href is not None and displayname is not None:
                calendars.append({
                    'path': href.text,
                    'name': displayname.text,
                    'url': f"{self.server_url}{href.text}"
                })
        
        return calendars
    
    def get_events(self, calendar_path: str, start: datetime, end: datetime) -> List[Dict]:
        """获取日历事件"""
        try:
            # 构建时间范围查询
            start_str = start.strftime('%Y%m%dT%H%M%SZ')
            end_str = end.strftime('%Y%m%dT%H%M%SZ')
            
            query_xml = f'''<?xml version="1.0" encoding="utf-8"?>
            <c:calendar-query xmlns:c="urn:ietf:params:xml:ns:caldav" xmlns:d="DAV:">
                <d:prop>
                    <d:getetag/>
                    <c:calendar-data/>
                </d:prop>
                <c:filter>
                    <c:comp-filter name="VCALENDAR">
                        <c:comp-filter name="VEVENT">
                            <c:time-range start="{start_str}" end="{end_str}"/>
                        </c:comp-filter>
                    </c:comp-filter>
                </c:filter>
            </c:calendar-query>'''
            
            response = self.session.request(
                'REPORT',
                f"{self.server_url}{calendar_path}",
                data=query_xml,
                headers={'Depth': '1'}
            )
            
            if response.status_code == 207:
                return self._parse_events(response.text)
            
            return []
        except Exception as e:
            print(f"获取事件失败: {e}")
            return []
    
    def _parse_events(self, xml_response: str) -> List[Dict]:
        """解析事件数据"""
        events = []
        root = ET.fromstring(xml_response)
        
        for response in root.findall('.//{DAV:}response'):
            href = response.find('.//{DAV:}href')
            calendar_data = response.find('.//{urn:ietf:params:xml:ns:caldav}calendar-data')
            
            if href is not None and calendar_data is not None:
                event_data = self._parse_icalendar(calendar_data.text)
                event_data['href'] = href.text
                events.append(event_data)
        
        return events
    
    def _parse_icalendar(self, ical_data: str) -> Dict:
        """解析iCalendar数据"""
        event = {
            'title': '',
            'description': '',
            'start_time': None,
            'end_time': None,
            'location': '',
            'uid': ''
        }
        
        lines = ical_data.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('SUMMARY:'):
                event['title'] = line[8:]
            elif line.startswith('DESCRIPTION:'):
                event['description'] = line[12:]
            elif line.startswith('DTSTART:'):
                event['start_time'] = self._parse_datetime(line[8:])
            elif line.startswith('DTEND:'):
                event['end_time'] = self._parse_datetime(line[6:])
            elif line.startswith('LOCATION:'):
                event['location'] = line[9:]
            elif line.startswith('UID:'):
                event['uid'] = line[4:]
        
        return event
    
    def _parse_datetime(self, dt_str: str) -> Optional[str]:
        """解析日期时间字符串"""
        try:
            # 处理UTC时间 (20240101T120000Z)
            if 'Z' in dt_str:
                dt = datetime.strptime(dt_str, '%Y%m%dT%H%M%SZ')
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            # 处理本地时间 (20240101T120000)
            else:
                dt = datetime.strptime(dt_str, '%Y%m%dT%H%M%S')
                return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return None
    
    def create_event(self, calendar_path: str, event_data: Dict) -> bool:
        """创建日历事件"""
        try:
            uid = event_data.get('uid', f"kanban-{datetime.now().timestamp()}")
            
            # 构建iCalendar数据
            ical_data = self._build_icalendar(event_data, uid)
            
            response = self.session.put(
                f"{self.server_url}{calendar_path}{uid}.ics",
                data=ical_data,
                headers={'Content-Type': 'text/calendar; charset=utf-8'}
            )
            
            return response.status_code in [201, 204]
        except Exception as e:
            print(f"创建事件失败: {e}")
            return False
    
    def _build_icalendar(self, event: Dict, uid: str) -> str:
        """构建iCalendar数据"""
        now = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        
        # 转换时间格式
        start = event.get('start_time', '')
        end = event.get('end_time', '')
        
        if start:
            start = start.replace('-', '').replace(' ', 'T').replace(':', '') + 'Z'
        if end:
            end = end.replace('-', '').replace(' ', 'T').replace(':', '') + 'Z'
        
        ical = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Kanban Calendar//EN
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{now}
DTSTART:{start}
DTEND:{end}
SUMMARY:{event.get('title', '')}
DESCRIPTION:{event.get('description', '')}
LOCATION:{event.get('location', '')}
END:VEVENT
END:VCALENDAR"""
        
        return ical


class CalendarSyncManager:
    """日历同步管理器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_accounts(self) -> List[Dict]:
        """获取所有CalDAV账户"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('SELECT * FROM calendar_accounts WHERE sync_enabled = 1')
        accounts = [dict(row) for row in c.fetchall()]
        
        conn.close()
        return accounts
    
    def sync_account(self, account_id: int) -> Dict:
        """同步指定账户"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # 获取账户信息
        c.execute('SELECT * FROM calendar_accounts WHERE id = ?', (account_id,))
        account = c.fetchone()
        
        if not account:
            return {'success': False, 'error': '账户不存在'}
        
        # 创建CalDAV客户端
        client = CalDAVClient(
            account['server_url'],
            account['username'],
            account['password']
        )
        
        # 发现日历
        calendars = client.discover_calendars()
        
        if not calendars:
            return {'success': False, 'error': '未发现可用日历'}
        
        # 获取时间范围（未来3个月）
        now = datetime.now()
        start = now - timedelta(days=30)
        end = now + timedelta(days=90)
        
        sync_count = 0
        
        for calendar in calendars:
            # 获取远程事件
            remote_events = client.get_events(calendar['path'], start, end)
            
            for event in remote_events:
                # 检查事件是否已存在
                c.execute('SELECT id FROM calendar_events WHERE external_id = ?', (event['uid'],))
                existing = c.fetchone()
                
                if existing:
                    # 更新现有事件
                    c.execute('''
                        UPDATE calendar_events SET
                            title = ?,
                            description = ?,
                            start_time = ?,
                            end_time = ?,
                            location = ?,
                            sync_status = 'synced',
                            last_sync_at = ?
                        WHERE external_id = ?
                    ''', (
                        event['title'],
                        event['description'],
                        event['start_time'],
                        event['end_time'],
                        event['location'],
                        datetime.now().isoformat(),
                        event['uid']
                    ))
                else:
                    # 创建新事件
                    c.execute('''
                        INSERT INTO calendar_events
                        (title, description, start_time, end_time, location, external_id, external_source, sync_status, last_sync_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        event['title'],
                        event['description'],
                        event['start_time'],
                        event['end_time'],
                        event['location'],
                        event['uid'],
                        account['account_type'],
                        'synced',
                        datetime.now().isoformat()
                    ))
                
                sync_count += 1
        
        # 更新最后同步时间
        c.execute('''
            UPDATE calendar_accounts 
            SET last_sync_at = ? 
            WHERE id = ?
        ''', (datetime.now().isoformat(), account_id))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'synced_events': sync_count,
            'calendars_found': len(calendars)
        }


# 便捷函数
def sync_all_accounts(db_path: str) -> List[Dict]:
    """同步所有账户"""
    manager = CalendarSyncManager(db_path)
    accounts = manager.get_accounts()
    
    results = []
    for account in accounts:
        result = manager.sync_account(account['id'])
        results.append({
            'account_id': account['id'],
            'account_name': account['name'],
            **result
        })
    
    return results


if __name__ == '__main__':
    # 测试
    db_path = os.path.expanduser('~/.openclaw/workspace/kanban/kanban_v5.db')
    results = sync_all_accounts(db_path)
    print(json.dumps(results, indent=2, ensure_ascii=False))

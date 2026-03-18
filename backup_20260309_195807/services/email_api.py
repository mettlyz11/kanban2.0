#!/usr/bin/env python3
"""
邮件系统API接口
为看板系统提供邮件功能的REST API
"""

import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# 添加技能路径
sys.path.insert(0, '/opt/kanban-react/backend/skills/mutt-skill')
from skills.mutt_skill.mutt_skill import (
    send_email, check_mutt_status,
    ContactManager, EmailReceiver
)

class EmailAPIHandler(BaseHTTPRequestHandler):
    """邮件API处理器"""
    
    def _send_json(self, data, status=200):
        """发送JSON响应"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    
    def _get_post_data(self):
        """获取POST数据"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            post_data = self.rfile.read(content_length)
            try:
                return json.loads(post_data.decode())
            except:
                return {}
        return {}
    
    def do_OPTIONS(self):
        """处理CORS预检请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """处理GET请求"""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        # 获取邮件状态
        if path == '/api/email/status':
            status = check_mutt_status()
            cm = ContactManager()
            status['contacts_count'] = len(cm.list_contacts())
            self._send_json({"success": True, "data": status})
        
        # 获取邮件列表
        elif path == '/api/email/inbox':
            account = query.get('account', ['foxmail'])[0]
            folder = query.get('folder', ['Inbox'])[0]
            limit = int(query.get('limit', ['20'])[0])
            
            receiver = EmailReceiver(account=account)
            emails = receiver.fetch_emails(folder, limit)
            self._send_json({"success": True, "data": emails})
        
        # 获取邮件详情
        elif path.startswith('/api/email/detail/'):
            email_id = path.split('/')[-1]
            account = query.get('account', ['foxmail'])[0]
            folder = query.get('folder', ['Inbox'])[0]
            
            receiver = EmailReceiver(account=account)
            email = receiver.get_email_detail(email_id, folder)
            if email:
                self._send_json({"success": True, "data": email})
            else:
                self._send_json({"success": False, "error": "邮件不存在"}, 404)
        
        # 获取邮件文件夹
        elif path == '/api/email/folders':
            account = query.get('account', ['foxmail'])[0]
            receiver = EmailReceiver(account=account)
            folders = receiver.get_folders()
            self._send_json({"success": True, "data": folders})
        
        # 获取联系人列表
        elif path == '/api/contacts':
            cm = ContactManager()
            tag = query.get('tag', [None])[0]
            contacts = cm.list_contacts(tag)
            self._send_json({"success": True, "data": contacts})
        
        # 获取联系人标签
        elif path == '/api/contacts/tags':
            cm = ContactManager()
            tags = cm.get_tags()
            self._send_json({"success": True, "data": tags})
        
        # 搜索联系人
        elif path == '/api/contacts/search':
            query_str = query.get('q', [''])[0]
            cm = ContactManager()
            results = cm.search_contacts(query_str)
            self._send_json({"success": True, "data": results})
        
        else:
            self._send_json({"success": False, "error": "未知接口"}, 404)
    
    def do_POST(self):
        """处理POST请求"""
        parsed = urlparse(self.path)
        path = parsed.path
        data = self._get_post_data()
        
        # 发送邮件
        if path == '/api/email/send':
            to = data.get('to')
            subject = data.get('subject')
            body = data.get('body')
            cc = data.get('cc')
            account = data.get('account', 'foxmail')
            
            if not all([to, subject, body]):
                self._send_json({"success": False, "error": "缺少必要参数"}, 400)
                return
            
            result = send_email(to, subject, body, cc, account)
            self._send_json(result)
        
        # 同步邮件
        elif path == '/api/email/sync':
            account = data.get('account', 'foxmail')
            receiver = EmailReceiver(account=account)
            result = receiver.sync_mail()
            self._send_json(result)
        
        # 添加联系人
        elif path == '/api/contacts':
            name = data.get('name')
            email = data.get('email')
            phone = data.get('phone', '')
            company = data.get('company', '')
            tags = data.get('tags', [])
            
            if not all([name, email]):
                self._send_json({"success": False, "error": "缺少必要参数"}, 400)
                return
            
            cm = ContactManager()
            result = cm.add_contact(name, email, phone, company, tags)
            self._send_json(result)
        
        else:
            self._send_json({"success": False, "error": "未知接口"}, 404)
    
    def do_PUT(self):
        """处理PUT请求"""
        parsed = urlparse(self.path)
        path = parsed.path
        data = self._get_post_data()
        
        # 更新联系人
        if path.startswith('/api/contacts/'):
            contact_id = path.split('/')[-1]
            cm = ContactManager()
            result = cm.update_contact(contact_id, **data)
            self._send_json(result)
        else:
            self._send_json({"success": False, "error": "未知接口"}, 404)
    
    def do_DELETE(self):
        """处理DELETE请求"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # 删除联系人
        if path.startswith('/api/contacts/'):
            contact_id = path.split('/')[-1]
            cm = ContactManager()
            result = cm.delete_contact(contact_id)
            self._send_json(result)
        else:
            self._send_json({"success": False, "error": "未知接口"}, 404)


def run_server(port=8089):
    """运行邮件API服务器"""
    server = HTTPServer(('0.0.0.0', port), EmailAPIHandler)
    print(f"邮件API服务器运行在端口 {port}")
    server.serve_forever()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8089, help='端口号')
    args = parser.parse_args()
    run_server(args.port)

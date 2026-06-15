#!/usr/bin/env python3
"""
看板邮件同步API服务
支持邮件同步、文件夹管理、邮件查看
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATA_DIR = '/opt/kanban-react/backend/data'
os.makedirs(DATA_DIR, exist_ok=True)

# 模拟邮件数据存储
EMAILS_FILE = os.path.join(DATA_DIR, 'emails.json')
FOLDERS_FILE = os.path.join(DATA_DIR, 'folders.json')

def load_emails():
    if os.path.exists(EMAILS_FILE):
        with open(EMAILS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_emails(emails):
    with open(EMAILS_FILE, 'w') as f:
        json.dump(emails, f, ensure_ascii=False, indent=2)

def load_folders():
    if os.path.exists(FOLDERS_FILE):
        with open(FOLDERS_FILE, 'r') as f:
            return json.load(f)
    return [
        {"id": "inbox", "name": "收件箱", "unread": 0},
        {"id": "sent", "name": "已发送", "unread": 0},
        {"id": "drafts", "name": "草稿箱", "unread": 0},
        {"id": "trash", "name": "垃圾箱", "unread": 0}
    ]

# 健康检查
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "email-api",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    })

# 获取邮件文件夹
@app.route('/api/emails/folders', methods=['GET'])
def get_folders():
    folders = load_folders()
    return jsonify({"success": True, "folders": folders})

# 同步邮件
@app.route('/api/emails/sync', methods=['POST'])
def sync_emails():
    data = request.get_json() or {}
    folder = data.get('folder', 'inbox')
    
    # 模拟同步过程
    emails = load_emails()
    
    # 如果没有邮件，创建一些示例邮件
    if not emails:
        sample_emails = [
            {
                "id": "1",
                "subject": "欢迎使用看板邮件系统",
                "sender": "system@kanban.com",
                "sender_name": "看板系统",
                "recipient": "user@example.com",
                "date": datetime.now().isoformat(),
                "folder": "inbox",
                "read": False,
                "content": "这是看板2.4邮件系统的欢迎使用邮件。您可以通过邮件同步功能管理您的邮件。",
                "attachments": []
            },
            {
                "id": "2",
                "subject": "项目进度更新",
                "sender": "pm@company.com",
                "sender_name": "项目经理",
                "recipient": "user@example.com",
                "date": datetime.now().isoformat(),
                "folder": "inbox",
                "read": True,
                "content": "您好，这是本周的项目进度更新报告。",
                "attachments": [{"name": "周报.pdf", "size": 1024000}]
            },
            {
                "id": "3",
                "subject": "会议邀请：技术评审",
                "sender": "calendar@company.com",
                "sender_name": "日历系统",
                "recipient": "user@example.com",
                "date": datetime.now().isoformat(),
                "folder": "inbox",
                "read": False,
                "content": "您有一个即将开始的会议：技术评审会议。时间：明天上午10点。",
                "attachments": []
            }
        ]
        emails = sample_emails
        save_emails(emails)
    
    # 筛选指定文件夹的邮件
    folder_emails = [e for e in emails if e.get('folder') == folder]
    
    return jsonify({
        "success": True,
        "message": f"同步完成，共 {len(folder_emails)} 封邮件",
        "count": len(folder_emails),
        "emails": folder_emails
    })

# 获取邮件列表
@app.route('/api/emails/', methods=['GET'])
@app.route('/api/emails', methods=['GET'])
def get_emails():
    folder = request.args.get('folder', 'inbox')
    emails = load_emails()
    folder_emails = [e for e in emails if e.get('folder') == folder]
    return jsonify({"success": True, "emails": folder_emails})

# 获取单封邮件
@app.route('/api/emails/<email_id>', methods=['GET'])
def get_email(email_id):
    emails = load_emails()
    email = next((e for e in emails if e.get('id') == email_id), None)
    if email:
        # 标记为已读
        if not email.get('read', False):
            email['read'] = True
            save_emails(emails)
        return jsonify({"success": True, "email": email})
    return jsonify({"success": False, "error": "邮件不存在"}), 404

# 标记邮件已读/未读
@app.route('/api/emails/<email_id>/read', methods=['PUT'])
def mark_read(email_id):
    data = request.get_json() or {}
    read_status = data.get('read', True)
    
    emails = load_emails()
    email = next((e for e in emails if e.get('id') == email_id), None)
    if email:
        email['read'] = read_status
        save_emails(emails)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "邮件不存在"}), 404

# 移动邮件到文件夹
@app.route('/api/emails/<email_id>/move', methods=['PUT'])
def move_email(email_id):
    data = request.get_json() or {}
    target_folder = data.get('folder', 'inbox')
    
    emails = load_emails()
    email = next((e for e in emails if e.get('id') == email_id), None)
    if email:
        email['folder'] = target_folder
        save_emails(emails)
        return jsonify({"success": True, "message": f"邮件已移动到 {target_folder}"})
    return jsonify({"success": False, "error": "邮件不存在"}), 404

# 删除邮件
@app.route('/api/emails/<email_id>', methods=['DELETE'])
def delete_email(email_id):
    emails = load_emails()
    email = next((e for e in emails if e.get('id') == email_id), None)
    if email:
        email['folder'] = 'trash'
        save_emails(emails)
        return jsonify({"success": True, "message": "邮件已移至垃圾箱"})
    return jsonify({"success": False, "error": "邮件不存在"}), 404

# 发送邮件（模拟）
@app.route('/api/emails/send', methods=['POST'])
def send_email():
    data = request.get_json() or {}
    
    new_email = {
        "id": str(int(datetime.now().timestamp())),
        "subject": data.get('subject', '无主题'),
        "sender": "user@example.com",
        "sender_name": "我",
        "recipient": data.get('to', ''),
        "date": datetime.now().isoformat(),
        "folder": "sent",
        "read": True,
        "content": data.get('content', ''),
        "attachments": data.get('attachments', [])
    }
    
    emails = load_emails()
    emails.append(new_email)
    save_emails(emails)
    
    return jsonify({"success": True, "message": "邮件已发送", "email_id": new_email["id"]})

if __name__ == '__main__':
    # print("✅ 邮件API服务启动")
    # print("📍 端口: 8089")
    app.run(host='0.0.0.0', port=8089, debug=False)

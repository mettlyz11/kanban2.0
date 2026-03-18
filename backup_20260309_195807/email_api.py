#!/usr/bin/env python3
from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# 模拟邮件数据
emails_db = [
    {"id": 1, "subject": "测试邮件1", "sender": "test@example.com", "date": "2026-03-03", "read": False},
    {"id": 2, "subject": "测试邮件2", "sender": "noreply@system.com", "date": "2026-03-03", "read": True},
]

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "email-api", "version": "1.0.0"})

@app.route('/api/emails/sync', methods=['POST'])
def sync_emails():
    return jsonify({"success": True, "message": "邮件同步成功", "count": len(emails_db)})

@app.route('/api/emails/folders', methods=['GET'])
def get_folders():
    return jsonify({"success": True, "folders": ["收件箱", "已发送", "草稿箱", "垃圾箱"]})

@app.route('/api/emails', methods=['GET'])
def get_emails():
    return jsonify({"success": True, "emails": emails_db})

@app.route('/api/emails/<int:email_id>', methods=['GET'])
def get_email(email_id):
    email = next((e for e in emails_db if e["id"] == email_id), None)
    if email:
        return jsonify({"success": True, "email": email})
    return jsonify({"success": False, "error": "邮件不存在"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8089, debug=False)

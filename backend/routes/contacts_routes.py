"""Contacts API (联系人总览)"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db
import os, json

bp = Blueprint('routes_contacts', __name__)
logger = __import__('logging').getLogger(__name__)

PEOPLE_DIR = "/opt/kanban-react/backend/uploads/people-profiles"


@bp.route('/api/contacts/list', methods=['GET'])
def list_contacts():
    """从 contacts 表 + people-profiles 返回联系人总览"""
    search = request.args.get('q', '').strip()
    page = int(request.args.get('page', '1'))
    limit = min(int(request.args.get('limit', '100')), 500)
    offset = (page - 1) * limit

    try:
        conn = get_db()
        c = conn.cursor()

        # Count
        if search:
            c.execute("SELECT COUNT(*) FROM contacts WHERE name LIKE %s OR org LIKE %s OR company LIKE %s OR email LIKE %s",
                       (f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%'))
        else:
            c.execute("SELECT COUNT(*) FROM contacts")
        total = c.fetchone()['COUNT(*)']

        # Query
        if search:
            c.execute("""SELECT id, name, org, title, department, email, phone, wechat, company, notes, status
                         FROM contacts WHERE name LIKE %s OR org LIKE %s OR company LIKE %s OR email LIKE %s
                         ORDER BY id ASC LIMIT %s OFFSET %s""",
                       (f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%', limit, offset))
        else:
            c.execute("SELECT id, name, org, title, department, email, phone, wechat, company, notes, status FROM contacts ORDER BY id ASC LIMIT %s OFFSET %s", (limit, offset))
        rows = c.fetchall()
        conn.close()
    except Exception as e:
        logger.warning(f"contacts query failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

    contacts = []
    for r in rows:
        contacts.append({
            "id": r["id"],
            "name": r.get("name", ""),
            "org": r.get("org", ""),
            "title": r.get("title", ""),
            "department": r.get("department", ""),
            "email": r.get("email", ""),
            "phone": r.get("phone", ""),
            "wechat": r.get("wechat", ""),
            "company": r.get("company", ""),
            "notes": r.get("notes", ""),
            "status": r.get("status", "active"),
        })

    # Also read people-profiles for rich profiles
    profiles = []
    if os.path.exists(PEOPLE_DIR):
        for fname in sorted(os.listdir(PEOPLE_DIR)):
            if fname.endswith('.md'):
                fpath = os.path.join(PEOPLE_DIR, fname)
                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                pname = fname[:-3]
                profiles.append({"name": pname, "filename": fname, "content": content[:2000], "size": os.path.getsize(fpath)})

    return jsonify({
        "success": True,
        "contacts": contacts,
        "total": total,
        "page": page,
        "profiles": profiles,
        "profile_count": len(profiles),
    })


@bp.route('/api/contacts/profile', methods=['GET'])
def get_profile():
    """读取某个本地 profiles 完整内容"""
    name = request.args.get('name', '')
    if not name:
        return jsonify({"success": False, "error": "需要 name 参数"}), 400
    fpath = os.path.join(PEOPLE_DIR, name + '.md')
    if not os.path.exists(fpath):
        return jsonify({"success": False, "error": "profile 不存在"}), 404
    with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    return jsonify({"success": True, "name": name, "content": content})

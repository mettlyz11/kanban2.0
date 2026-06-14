"""Routes: wiki_api - wiki_api"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db, row_to_dict
import os
import json
from datetime import datetime

bp = Blueprint("routes_wiki_api", __name__)
logger = __import__("logging").getLogger(__name__)

@bp.route('/api/monitoring/api-performance', methods=['GET'])
def get_api_performance():
    """获取API性能统计"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        # 获取慢API统计（最近24小时）
        c.execute('''
            SELECT event_type, source, message, metadata, timestamp
            FROM perception_events 
            WHERE event_type = 'slow_api' 
            AND timestamp > datetime('now', '-24 hours')
            ORDER BY timestamp DESC
            LIMIT 50
        ''')
    
        slow_apis = []
        for row in c.fetchall():
            try:
                metadata = json.loads(row[3]) if row[3] else {}
                slow_apis.append({
                    'endpoint': metadata.get('endpoint', 'unknown'),
                    'method': metadata.get('method', 'GET'),
                    'duration': metadata.get('duration', 0),
                    'status_code': metadata.get('status_code', 200),
                    'timestamp': row[4]
                })
            except:
                pass
    
        # 统计信息
        stats = {
            'total_slow_apis': len(slow_apis),
            'avg_duration': round(sum(a['duration'] for a in slow_apis) / len(slow_apis), 3) if slow_apis else 0,
            'max_duration': max(a['duration'] for a in slow_apis) if slow_apis else 0,
            'apis_over_3s': len([a for a in slow_apis if a['duration'] > 3.0]),
            'apis_over_5s': len([a for a in slow_apis if a['duration'] > 5.0])
        }
    
        conn.close()
    
        return jsonify({
            'success': True,
            'stats': stats,
            'slow_apis': slow_apis[:20]  # 只返回前20条
        })
    except Exception as e:
        logger.error(f"Error getting api performance: {e}")
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/backlog', methods=['GET'])
def get_backlog():
    """获取所有需求，按状态分组返回"""
    try:
        conn = get_db()
        c = conn.cursor(pymysql.cursors.DictCursor)
        c.execute('''
            SELECT * FROM backlog 
            ORDER BY priority DESC, created_at DESC
        ''')
        backlog = c.fetchall()
        conn.close()
        return jsonify({'success': True, 'backlog': backlog})
    except Exception as e:
        print(f"[ERROR] get_backlog: {e}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/backlog', methods=['POST'])
def create_backlog():
    """创建新需求"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO backlog (title, description, status, priority, project, tags, estimated_hours)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('title'),
            data.get('description'),
            data.get('status', 'todo'),
            data.get('priority', 1),
            data.get('project'),
            data.get('tags'),
            data.get('estimated_hours')
        ))
        conn.commit()
        new_id = c.lastrowid
        conn.close()
        return jsonify({'success': True, 'id': new_id})
    except Exception as e:
        print(f"[ERROR] create_backlog: {e}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/backlog/<int:item_id>', methods=['PUT'])
def update_backlog(item_id):
    """更新需求"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        
        # 构建更新 SQL
        fields = []
        params = []
        for key in ['title', 'description', 'status', 'priority', 'project', 'tags', 'estimated_hours']:
            if key in data:
                fields.append(f"{key} = %s")
                params.append(data[key])
        params.append(item_id)
        
        sql = f"UPDATE backlog SET {', '.join(fields)} WHERE id = %s"
        c.execute(sql, params)
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] update_backlog: {e}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/backlog/<int:item_id>', methods=['DELETE'])
def delete_backlog(item_id):
    """删除需求"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM backlog WHERE id = %s', (item_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] delete_backlog: {e}")
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/wiki/entries', methods=['GET'])
def get_wiki_entries():
    """获取所有百科词条，支持分类筛选和关键词搜索"""
    try:
        category = request.args.get('category')
        search = request.args.get('search')
        
        conn = get_db()
        c = conn.cursor(pymysql.cursors.DictCursor)
        
        sql = "SELECT id, title, category, tags, author, status, views, created_at, updated_at FROM wiki_entries WHERE status = 'published'"
        params = []
        
        if category:
            sql += " AND category = %s"
            params.append(category)
        
        if search:
            sql += " AND (title LIKE %s OR content LIKE %s)"
            search_term = f"%{search}%"
            params.append(search_term)
            params.append(search_term)
        
        sql += " ORDER BY created_at DESC"
        
        c.execute(sql, params)
        entries = c.fetchall()
        conn.close()
        return jsonify({'success': True, 'entries': entries})
    except Exception as e:
        print(f"[ERROR] get_wiki_entries: {e}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/wiki/entries/<int:entry_id>', methods=['GET'])
def get_wiki_entry(entry_id):
    """获取单个百科词条详情"""
    try:
        conn = get_db()
        c = conn.cursor(pymysql.cursors.DictCursor)
        c.execute('SELECT * FROM wiki_entries WHERE id = %s AND status = "published"', (entry_id,))
        entry = c.fetchone()
        
        if entry:
            # 增加浏览次数
            c.execute('UPDATE wiki_entries SET views = views + 1 WHERE id = %s', (entry_id,))
            conn.commit()
        
        conn.close()
        
        if entry:
            return jsonify({'success': True, 'entry': entry})
        else:
            return jsonify({'success': False, 'error': '词条不存在'})
    except Exception as e:
        print(f"[ERROR] get_wiki_entry: {e}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/wiki/categories', methods=['GET'])
def get_wiki_categories():
    """获取所有分类"""
    try:
        conn = get_db()
        c = conn.cursor(pymysql.cursors.DictCursor)
        c.execute('''
            SELECT category, COUNT(*) as count 
            FROM wiki_entries 
            WHERE status = 'published' 
            GROUP BY category 
            ORDER BY count DESC
        ''')
        categories = c.fetchall()
        conn.close()
        return jsonify({'success': True, 'categories': categories})
    except Exception as e:
        print(f"[ERROR] get_wiki_categories: {e}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/wiki/entries', methods=['POST'])
def create_wiki_entry():
    """创建新词条"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO wiki_entries (title, content, category, tags, author, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            data.get('title'),
            data.get('content'),
            data.get('category'),
            data.get('tags'),
            data.get('author'),
            data.get('status', 'published')
        ))
        conn.commit()
        new_id = c.lastrowid
        conn.close()
        return jsonify({'success': True, 'id': new_id})
    except Exception as e:
        print(f"[ERROR] create_wiki_entry: {e}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/wiki/entries/<int:entry_id>', methods=['PUT'])
def update_wiki_entry(entry_id):
    """更新词条"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        
        fields = []
        params = []
        for key in ['title', 'content', 'category', 'tags', 'author', 'status']:
            if key in data:
                fields.append(f"{key} = %s")
                params.append(data[key])
        params.append(entry_id)
        
        sql = f"UPDATE wiki_entries SET {', '.join(fields)} WHERE id = %s"
        c.execute(sql, params)
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] update_wiki_entry: {e}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/wiki/entries/<int:entry_id>', methods=['DELETE'])
def delete_wiki_entry(entry_id):
    """删除词条"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM wiki_entries WHERE id = %s', (entry_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] delete_wiki_entry: {e}")
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/projects/gantt', methods=['GET'])
def get_projects_gantt():
    """获取项目甘特图数据"""
    try:
        conn = get_db()
        c = conn.cursor(pymysql.cursors.DictCursor)
        c.execute('''
            SELECT id, number, chinese_name as title, status, priority, 
                   start_date, end_date, deadline
            FROM projects 
            WHERE status != 'deleted'
            ORDER BY priority DESC, created_at DESC
        ''')
        projects = c.fetchall()
        conn.close()
        
        # 转换为甘特图格式
        gantt_data = []
        for p in projects:
            gantt_data.append({
                'id': p['id'],
                'name': p['title'] or p['number'],
                'start': p['start_date'].isoformat() if p['start_date'] else None,
                'end': p['end_date'].isoformat() if p['end_date'] else None,
                'progress': 0,
                'status': p['status'],
                'priority': p['priority']
            })
        
        return jsonify({'success': True, 'data': gantt_data})
    except Exception as e:
        print(f"[ERROR] get_projects_gantt: {e}")
        return jsonify({'success': False, 'error': str(e)})



@bp.route('/api/activity-log', methods=['GET'])
def get_activity_log():
    """Get activity log"""
    try:
        conn = get_db()
        c = conn.cursor(pymysql.cursors.DictCursor)
        limit = request.args.get('limit', '50')
        try:
            limit = int(limit)
        except:
            limit = 50
        
        c.execute('''
            SELECT * FROM activity_log
            ORDER BY created_at DESC
            LIMIT %s
        ''', (limit,))
        logs = c.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'logs': logs,
            'total': len(logs)
        })
    except Exception as e:
        print(f"[ERROR] get_activity_log: {e}")
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/activity-log', methods=['POST'])
def create_activity_log():
    """Create activity log entry"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO activity_log 
            (user_id, username, action, entity_type, entity_id, description, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('user_id'),
            data.get('username'),
            data.get('action'),
            data.get('entity_type'),
            data.get('entity_id'),
            data.get('description'),
            request.remote_addr,
            request.headers.get('User-Agent')
        ))
        conn.commit()
        new_id = c.lastrowid
        conn.close()
        
        return jsonify({'success': True, 'id': new_id})
    except Exception as e:
        print(f"[ERROR] create_activity_log: {e}")
        return jsonify({'success': False, 'error': str(e)})



@bp.route('/api/wechat/contacts', methods=['GET'])
def get_wechat_contacts():
    """Get WeChat contacts"""
    try:
        search = request.args.get('search', '')
        limit = request.args.get('limit', '200')
        try:
            limit = int(limit)
        except:
            limit = 200
        
        conn = get_db()
        c = conn.cursor(pymysql.cursors.DictCursor)
        
        if search:
            search = f"%{search}%"
            c.execute('''
                SELECT * FROM wechat_contacts 
                WHERE display_name LIKE %s OR tags LIKE %s OR company LIKE %s
                ORDER BY relation_score DESC, display_name ASC
                LIMIT %s
            ''', (search, search, search, limit))
        else:
            c.execute('''
                SELECT * FROM wechat_contacts 
                ORDER BY relation_score DESC, display_name ASC
                LIMIT %s
            ''', (limit,))
        
        contacts = c.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'contacts': contacts,
            'total': len(contacts)
        })
    except Exception as e:
        print(f"[ERROR] get_wechat_contacts: {e}")
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/wechat/contacts/<int:contact_id>', methods=['PUT'])
def update_wechat_contact(contact_id):
    """Update WeChat contact"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        
        allowed_fields = [
            'display_name', 'wechat_id', 'phone', 'email', 'company', 'position',
            'industry', 'relation_type', 'relation_score', 'how_met',
            'first_contact_date', 'last_contact_date', 'tags', 'notes',
            'source_account_id', 'source_chat_count'
        ]
        
        updates = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not updates:
            return jsonify({'success': False, 'error': '没有要更新的字段'}), 400
        
        set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [contact_id]
        
        c.execute(f"UPDATE wechat_contacts SET {set_clause}, updated_at = NOW() WHERE id = %s", values)
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] update_wechat_contact: {e}")
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/wechat/contacts', methods=['POST'])
def create_wechat_contact():
    """Create WeChat contact"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO wechat_contacts 
            (display_name, wechat_id, phone, email, company, position, industry, 
             relation_type, relation_score, how_met, first_contact_date, 
             last_contact_date, tags, notes, source_account_id, source_chat_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('display_name'),
            data.get('wechat_id'),
            data.get('phone'),
            data.get('email'),
            data.get('company'),
            data.get('position'),
            data.get('industry'),
            data.get('relation_type'),
            data.get('relation_score', 50),
            data.get('how_met'),
            data.get('first_contact_date'),
            data.get('last_contact_date'),
            data.get('tags'),
            data.get('notes'),
            data.get('source_account_id'),
            data.get('source_chat_count', 0),
        ))
        conn.commit()
        new_id = c.lastrowid
        conn.close()
        
        return jsonify({'success': True, 'id': new_id})
    except Exception as e:
        print(f"[ERROR] create_wechat_contact: {e}")
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/wechat/contacts/<int:contact_id>', methods=['DELETE'])
def delete_wechat_contact(contact_id):
    """Delete WeChat contact (soft delete handled in frontend)"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM wechat_contacts WHERE id = %s", (contact_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] delete_wechat_contact: {e}")
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/wechat/accounts', methods=['GET'])
def get_wechat_accounts():
    """Get WeChat accounts"""
    try:
        conn = get_db()
        c = conn.cursor(pymysql.cursors.DictCursor)
        c.execute('''SELECT * FROM wechat_accounts ORDER BY account_name ASC''')
        accounts = c.fetchall()
        conn.close()
        return jsonify({'success': True, 'accounts': accounts})
    except Exception as e:
        print(f"[ERROR] get_wechat_accounts: {e}")
        return jsonify({'success': False, 'error': str(e)})




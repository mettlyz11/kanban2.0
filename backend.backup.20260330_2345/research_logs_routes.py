"""
文献调研记录 API 路由
提供调研记录的增删改查功能
"""

from flask import Blueprint, request, jsonify
from database_config import get_db_connection
import os
from datetime import datetime
import json

research_logs_bp = Blueprint('research_logs', __name__)

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kanban_v5.db')


def get_db():
    """获取数据库连接"""
    conn = get_db_connection()
    return conn


@research_logs_bp.route('/api/research-logs', methods=['POST'])
def create_research_log():
    """
    创建新的调研记录
    POST /api/research-logs
    
    Request Body:
    {
        "date": "2026-03-11",
        "project": "T109",
        "query": "transition state calculation",
        "papers_found": 10,
        "key_findings": "关键发现...",
        "report_path": "/path/to/report"
    }
    """
    try:
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['date', 'project', 'query']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'缺少必填字段：{field}'
                }), 400
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO research_logs 
            (date, project, query, papers_found, key_findings, report_path)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['date'],
            data['project'],
            data['query'],
            data.get('papers_found', 0),
            data.get('key_findings', ''),
            data.get('report_path', '')
        ))
        
        record_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'id': record_id,
                'message': '调研记录创建成功'
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@research_logs_bp.route('/api/research-logs', methods=['GET'])
def get_research_logs():
    """
    获取调研记录列表
    GET /api/research-logs?page=1&limit=20&project=T109&date_from=2026-03-01
    
    Query Parameters:
    - page: 页码 (默认 1)
    - limit: 每页数量 (默认 20)
    - project: 按项目筛选
    - date_from: 起始日期
    - date_to: 结束日期
    """
    try:
        # 获取查询参数
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        project = request.args.get('project', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        offset = (page - 1) * limit
        
        conn = get_db()
        c = conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if project:
            conditions.append('project = ?')
            params.append(project)
        
        if date_from:
            conditions.append('date >= ?')
            params.append(date_from)
        
        if date_to:
            conditions.append('date <= ?')
            params.append(date_to)
        
        where_clause = ''
        if conditions:
            where_clause = 'WHERE ' + ' AND '.join(conditions)
        
        # 查询总数
        c.execute(f'SELECT COUNT(*) FROM research_logs {where_clause}', params)
        total = c.fetchone()[0]
        
        # 查询数据
        c.execute(f'''
            SELECT * FROM research_logs 
            {where_clause}
            ORDER BY date DESC, created_at DESC
            LIMIT ? OFFSET ?
        ''', params + [limit, offset])
        
        rows = c.fetchall()
        conn.close()
        
        # 转换为字典列表
        logs = []
        for row in rows:
            logs.append({
                'id': row['id'],
                'date': row['date'],
                'project': row['project'],
                'query': row['query'],
                'papers_found': row['papers_found'],
                'key_findings': row['key_findings'],
                'report_path': row['report_path'],
                'created_at': row['created_at']
            })
        
        return jsonify({
            'success': True,
            'data': logs,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'total_pages': (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@research_logs_bp.route('/api/research-logs/<int:log_id>', methods=['GET'])
def get_research_log(log_id):
    """
    获取单个调研记录详情
    GET /api/research-logs/<id>
    """
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('SELECT * FROM research_logs WHERE id = ?', (log_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            return jsonify({
                'success': False,
                'error': '记录不存在'
            }), 404
        
        log = {
            'id': row['id'],
            'date': row['date'],
            'project': row['project'],
            'query': row['query'],
            'papers_found': row['papers_found'],
            'key_findings': row['key_findings'],
            'report_path': row['report_path'],
            'created_at': row['created_at']
        }
        
        return jsonify({
            'success': True,
            'data': log
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@research_logs_bp.route('/api/research-logs/<int:log_id>', methods=['PUT'])
def update_research_log(log_id):
    """
    更新调研记录
    PUT /api/research-logs/<id>
    
    Request Body:
    {
        "date": "2026-03-11",
        "project": "T109",
        "query": "updated query",
        "papers_found": 15,
        "key_findings": "更新后的关键发现",
        "report_path": "/new/path"
    }
    """
    try:
        data = request.get_json()
        
        conn = get_db()
        c = conn.cursor()
        
        # 检查记录是否存在
        c.execute('SELECT * FROM research_logs WHERE id = ?', (log_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({
                'success': False,
                'error': '记录不存在'
            }), 404
        
        # 构建更新字段
        update_fields = []
        update_values = []
        
        allowed_fields = ['date', 'project', 'query', 'papers_found', 'key_findings', 'report_path']
        for field in allowed_fields:
            if field in data:
                update_fields.append(f'{field} = ?')
                update_values.append(data[field])
        
        if not update_fields:
            conn.close()
            return jsonify({
                'success': False,
                'error': '没有可更新的字段'
            }), 400
        
        update_values.append(log_id)
        
        c.execute(f'''
            UPDATE research_logs 
            SET {', '.join(update_fields)}
            WHERE id = ?
        ''', update_values)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'id': log_id,
                'message': '调研记录更新成功'
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@research_logs_bp.route('/api/research-logs/<int:log_id>', methods=['DELETE'])
def delete_research_log(log_id):
    """
    删除调研记录
    DELETE /api/research-logs/<id>
    """
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 检查记录是否存在
        c.execute('SELECT * FROM research_logs WHERE id = ?', (log_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({
                'success': False,
                'error': '记录不存在'
            }), 404
        
        c.execute('DELETE FROM research_logs WHERE id = ?', (log_id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'id': log_id,
                'message': '调研记录删除成功'
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@research_logs_bp.route('/api/research-logs/stats', methods=['GET'])
def get_research_logs_stats():
    """
    获取调研记录统计信息
    GET /api/research-logs/stats
    
    Response:
    {
        "total_logs": 100,
        "total_papers": 500,
        "projects": {"T109": 30, "Pepi": 20},
        "recent_logs": [...],
        "logs_by_month": {...}
    }
    """
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 总记录数
        c.execute('SELECT COUNT(*) FROM research_logs')
        total_logs = c.fetchone()[0]
        
        # 总论文数
        c.execute('SELECT SUM(papers_found) FROM research_logs')
        total_papers = c.fetchone()[0] or 0
        
        # 按项目统计
        c.execute('''
            SELECT project, COUNT(*) as count 
            FROM research_logs 
            GROUP BY project 
            ORDER BY count DESC
        ''')
        projects = {row['project']: row['count'] for row in c.fetchall()}
        
        # 最近 10 条记录
        c.execute('''
            SELECT * FROM research_logs 
            ORDER BY date DESC, created_at DESC 
            LIMIT 10
        ''')
        recent_logs = []
        for row in c.fetchall():
            recent_logs.append({
                'id': row['id'],
                'date': row['date'],
                'project': row['project'],
                'query': row['query'],
                'papers_found': row['papers_found'],
                'key_findings': row['key_findings'][:200] + '...' if len(row['key_findings'] or '') > 200 else row['key_findings']
            })
        
        # 按月份统计
        c.execute('''
            SELECT strftime('%Y-%m', date) as month, COUNT(*) as count
            FROM research_logs
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        ''')
        logs_by_month = {row['month']: row['count'] for row in c.fetchall()}
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total_logs': total_logs,
                'total_papers': total_papers,
                'projects': projects,
                'recent_logs': recent_logs,
                'logs_by_month': logs_by_month
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@research_logs_bp.route('/api/research-logs/projects', methods=['GET'])
def get_projects():
    """
    获取所有项目列表（用于筛选）
    GET /api/research-logs/projects
    """
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('SELECT DISTINCT project FROM research_logs ORDER BY project')
        projects = [row['project'] for row in c.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': projects
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

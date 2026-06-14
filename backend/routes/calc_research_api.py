"""Routes: calc_research_api - 计算任务 + 调研 + 复盘 + 化学"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db, row_to_dict
import os
import json
from datetime import datetime

bp = Blueprint("routes_calc_research_api", __name__)
logger = __import__("logging").getLogger(__name__)

@bp.route('/api/calc-tasks', methods=['GET'])
def get_calc_tasks():
    """获取计算任务列表 - 从t109_calculations表"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT id, smiles, basis_set, functional, status, method, 
                       total_energy, activation_energy, reaction_energy,
                       homo_energy, lumo_energy, dipole_moment, created_at
                FROM t109_calculations
                ORDER BY created_at DESC
                LIMIT 50
            ''')
            tasks = [row_to_dict(row, c) for row in c.fetchall()]
        return jsonify({'success': True, 'tasks': tasks})
    except Exception as e:
        logger.error(f"获取计算任务失败: {e}")
        return jsonify({'success': True, 'tasks': []})

@bp.route('/api/calc-tasks/stats', methods=['GET'])
def get_calc_stats():
    """获取计算任务统计"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) as count FROM t109_calculations')
            total = c.fetchone()['count']
            c.execute("SELECT COUNT(*) as count FROM t109_calculations WHERE status = 'completed'")
            completed = c.fetchone()['count']
            c.execute("SELECT COUNT(*) as count FROM t109_calculations WHERE status = 'error' OR status = 'failed'")
            failed = c.fetchone()['count']
            c.execute("SELECT COUNT(*) as count FROM t109_calculations WHERE status = 'running' OR status = 'pending'")
            running = c.fetchone()['count']
        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'running': running,
                'completed': completed,
                'failed': failed
            }
        })
    except Exception as e:
        logger.error(f"获取计算统计失败: {e}")
        return jsonify({'success': True, 'stats': {'total': 0, 'running': 0, 'completed': 0, 'failed': 0}})

@bp.route('/api/calc-tasks/<task_id>', methods=['GET'])
def get_calc_task(task_id):
    """获取单个计算任务详情"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT * FROM t109_calculations WHERE id = %s
        ''', (task_id,))
        task = c.fetchone()
        conn.close()
        
        if not task:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
            
        return jsonify({'success': True, 'task': row_to_dict(task, c)})
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/calc-tasks/sync', methods=['POST'])
def sync_calc_tasks():
    """从T109服务器同步计算任务状态"""
    try:
        import requests
        # 调用T109 API获取最新任务
        response = requests.get('http://60.205.197.9:8000/calculations', timeout=10)
        if response.status_code == 200:
            t109_tasks = response.json()
            return jsonify({
                'success': True, 
                'message': '同步成功',
                'synced_count': len(t109_tasks) if isinstance(t109_tasks, list) else 0
            })
        else:
            return jsonify({'success': False, 'error': 'T109 API返回错误'}), 500
    except Exception as e:
        logger.error(f"同步T109任务失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/calc-tasks/submit', methods=['POST'])
def submit_calc_task():
    """提交计算任务到T109队列"""
    try:
        data = request.get_json()
        smiles = data.get('smiles')
        basis_set = data.get('basis_set', 'sto-3g')
        
        if not smiles:
            return jsonify({'success': False, 'error': 'SMILES不能为空'}), 400
        
        # 调用T109 API提交任务
        import requests
        response = requests.post(
            'http://60.205.197.9:8000/calculate',
            json={'smiles': smiles, 'basis_set': basis_set},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'success': True,
                'message': '任务已提交到T109',
                'task': result
            })
        else:
            return jsonify({'success': False, 'error': 'T109提交失败'}), 500
            
    except Exception as e:
        logger.error(f"提交计算任务失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/research', methods=['GET'])
def get_research_notes():
    """获取调研记录"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT * FROM research_notes
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        notes = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'notes': notes})
    except Exception as e:
        return jsonify({'success': True, 'notes': []})

@bp.route('/api/research/notes', methods=['POST'])
def create_research_note():
    """创建调研记录"""
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        content = data.get('content', '')
        category = data.get('category', '文献调研')
        source = data.get('source', '')
        tags = data.get('tags', '')
    
        if not title:
            return jsonify({'success': False, 'error': '标题不能为空'}), 400
    
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO research_notes (title, content, category, source, tags, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
        ''', (title, content, category, source, tags))
    
        note_id = c.lastrowid
        conn.commit()
        conn.close()
    
        return jsonify({'success': True, 'note_id': note_id, 'message': '调研记录创建成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/daily-reviews', methods=['GET'])
def get_daily_reviews():
    """获取每日复盘"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT * FROM daily_reviews
            ORDER BY review_date DESC
            LIMIT 30
        ''')
        reviews = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'reviews': reviews})
    except Exception as e:
        return jsonify({'success': True, 'reviews': []})



@bp.route('/api/daily-reviews', methods=['POST'])
def create_daily_review():
    """创建每日复盘"""
    try:
        data = request.get_json()
        review_date = data.get('review_date')
        mood = data.get('mood', '')
        summary = data.get('summary', '')
        
        if not review_date or not summary:
            return jsonify({'success': False, 'error': '日期和总结内容不能为空'})
        
        conn = get_db()
        c = conn.cursor()
        
        # 检查是否已存在该日期的复盘
        c.execute('SELECT id FROM daily_reviews WHERE review_date = %s', (review_date,))
        if c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '该日期已有复盘记录'})
        
        c.execute('INSERT INTO daily_reviews (review_date, mood, summary, created_at) VALUES (%s, %s, %s, NOW())', (review_date, mood, summary))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': '复盘创建成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/chemistry/elements', methods=['GET'])
def get_chemical_elements():
    """获取化学元素列表"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM chemical_elements ORDER BY atomic_number')
        elements = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'elements': elements})
    except Exception as e:
        return jsonify({'success': True, 'elements': []})

# ─── 自驱计算管线 API ──────────────────────────────────────────────────

@bp.route('/api/compute/servers', methods=['GET'])
def compute_get_servers():
    """获取GPU服务器状态"""
    servers = [
        {"ip": "47.93.236.63", "name": "Server 1", "location": "阿里云上海"},
        {"ip": "39.105.76.19", "name": "Server 2", "location": "阿里云上海"},
    ]
    return jsonify({"success": True, "servers": servers})

@bp.route('/api/compute/tasks', methods=['GET'])
def compute_get_tasks():
    """获取ORCA计算任务列表"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, ligand, reaction_type, method, pal_cores, status,
                       server_ip, energy_result, started_at, finished_at, created_at
                FROM compute_orca_tasks
                ORDER BY created_at DESC
                LIMIT 50
            """)
            tasks = [dict(row) for row in c.fetchall()]
        return jsonify({"success": True, "tasks": tasks})
    except Exception as e:
        return jsonify({"success": False, "tasks": [], "error": str(e)})

@bp.route('/api/compute/stats', methods=['GET'])
def compute_get_stats():
    """获取计算管线统计"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) as cnt FROM compute_orca_tasks")
            total = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM compute_orca_tasks WHERE status='completed'")
            completed = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM compute_orca_tasks WHERE status='running'")
            running = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM compute_orca_tasks WHERE status='pending'")
            pending = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM compute_orca_tasks WHERE status='failed'")
            failed = c.fetchone()['cnt']
            c.execute("SELECT * FROM compute_pipeline_state WHERE id=1")
            state = c.fetchone()
        return jsonify({
            "success": True,
            "stats": {
                "total": total, "completed": completed,
                "running": running, "pending": pending, "failed": failed
            },
            "pipeline": dict(state) if state else None
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@bp.route('/api/compute/ml-runs', methods=['GET'])
def compute_get_ml_runs():
    """获取ML训练记录"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM compute_ml_runs ORDER BY created_at DESC LIMIT 10")
            runs = [dict(row) for row in c.fetchall()]
        return jsonify({"success": True, "runs": runs})
    except Exception as e:
        return jsonify({"success": True, "runs": []})


@bp.route('/api/molecules', methods=['GET'])
@bp.route('/api/chemistry/molecules', methods=['GET'])
def get_molecules():
    """获取分子列表"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM molecules ORDER BY molecular_weight')
        molecules = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'molecules': molecules})
    except Exception as e:
        return jsonify({'success': True, 'molecules': []})

@bp.route('/api/reactions', methods=['GET'])
def get_reactions():
    """获取化学反应列表"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM reactions ORDER BY created_at DESC')
        reactions = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'reactions': reactions})
    except Exception as e:
        return jsonify({'success': True, 'reactions': []})


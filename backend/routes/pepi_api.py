"""Routes: pepi_api - pepi_api"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db, row_to_dict
import subprocess
import os
import json
from datetime import datetime

bp = Blueprint("routes_pepi_api", __name__)
logger = __import__("logging").getLogger(__name__)

@bp.route('/api/pepi/status', methods=['GET'])
@bp.route('/api/pepi/info', methods=['GET'])
def get_pepi_info():
    """获取Pepi信息"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM pepi_info ORDER BY id DESC LIMIT 1')
        row = c.fetchone()
        conn.close()
    
        if row:
            return jsonify({'success': True, 'info': row_to_dict(row, c)})
    
        # 默认信息
        return jsonify({
            'success': True,
            'info': {
                'name': 'Pepi',
                'version': '1.0',
                'status': 'active',
                'description': 'AI驱动的数字员工系统',
                'tasks_completed': 156,
                'avg_rating': 4.5,
                'total_hours': 320
            }
        })
    except Exception as e:
        return jsonify({'success': True, 'info': {
            'name': 'Pepi',
            'version': '1.0',
            'status': 'active'
        }})

@bp.route('/api/pepi/evaluations', methods=['GET'])
def get_pepi_evaluations():
    """获取Pepi评估记录"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT * FROM pepi_evaluations
            ORDER BY eval_date DESC
            LIMIT 50
        ''')
        evaluations = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'evaluations': evaluations})
    except Exception as e:
        return jsonify({'success': True, 'evaluations': []})

@bp.route('/api/pepi/sync', methods=['POST'])
def sync_pepi():
    """手动同步Pepi数据"""
    try:
        import subprocess
        result = subprocess.run(
            ['python3', 'sync_pepi.py'],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True
        )
    
        if result.returncode == 0:
            return jsonify({'success': True, 'message': '同步成功', 'output': result.stdout})
        else:
            return jsonify({'success': False, 'error': result.stderr})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/pepi/work-history', methods=['GET'])
def get_pepi_work_history():
    """获取Pepi工作历史（GIF记录）"""
    try:
        limit = request.args.get('limit', 20, type=int)
        work_type = request.args.get('work_type', None)
    
        conn = get_db()
    
        c = conn.cursor()
    
        if work_type:
            c.execute('''
                SELECT * FROM pepi_work_gifs 
                WHERE work_type = %s
                ORDER BY created_at DESC 
                LIMIT %s
            ''', (work_type, limit))
        else:
            c.execute('''
                SELECT * FROM pepi_work_gifs 
                ORDER BY created_at DESC 
                LIMIT %s
            ''', (limit,))
    
        records = []
        for row in c.fetchall():
            record = row_to_dict(row, c)
            # 格式化文件大小
            if record['gif_size']:
                size_mb = record['gif_size'] / (1024 * 1024)
                record['gif_size_formatted'] = f"{size_mb:.1f} MB"
            records.append(record)
    
        conn.close()
    
        return jsonify({
            'success': True,
            'records': records,
            'count': len(records)
        })
    
    except Exception as e:
        logger.error(f"Error getting pepi work history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/pepi/work-history/<int:record_id>', methods=['GET'])
def get_pepi_work_detail(record_id):
    """获取单条工作记录详情"""
    try:
        conn = get_db()
    
        c = conn.cursor()
    
        c.execute('SELECT * FROM pepi_work_gifs WHERE id = %s', (record_id,))
        row = c.fetchone()
        conn.close()
    
        if row:
            record = row_to_dict(row, c)
            return jsonify({'success': True, 'record': record})
        else:
            return jsonify({'success': False, 'error': 'Record not found'}), 404
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/pepi/work-history', methods=['POST'])
def add_pepi_work_record():
    """添加Pepi工作记录（供自动化脚本调用）"""
    try:
        data = request.get_json() or {}
    
        required_fields = ['task_name', 'gif_path']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
    
        conn = get_db()
        c = conn.cursor()
    
        gif_size = os.path.getsize(data['gif_path']) if os.path.exists(data['gif_path']) else 0
    
        c.execute('''
            INSERT INTO pepi_work_gifs 
            (task_name, task_description, gif_path, gif_size, 
             duration_seconds, frame_count, fps, work_type, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data['task_name'],
            data.get('task_description', ''),
            data['gif_path'],
            gif_size,
            data.get('duration_seconds', 0),
            data.get('frame_count', 0),
            data.get('fps', 2),
            data.get('work_type', 'desktop'),
            json.dumps(data.get('metadata', {})),
            datetime.now().isoformat()
        ))
    
        conn.commit()
        record_id = c.lastrowid
        conn.close()
    
        return jsonify({
            'success': True,
            'record_id': record_id,
            'message': 'Work record added successfully'
        })
    
    except Exception as e:
        logger.error(f"Error adding pepi work record: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/pepi/work-types', methods=['GET'])
def get_pepi_work_types():
    """获取Pepi工作类型统计"""
    try:
        conn = get_db()
    
        c = conn.cursor()
    
        c.execute('''
            SELECT work_type, COUNT(*) as count 
            FROM pepi_work_gifs 
            GROUP BY work_type
            ORDER BY count DESC
        ''')
    
        types = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
    
        return jsonify({
            'success': True,
            'work_types': types
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500




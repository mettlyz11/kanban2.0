"""Routes: goals_api - goals_api"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db, row_to_dict
from database_config import table_exists
import os
import json
from datetime import datetime

bp = Blueprint("routes_goals_api", __name__)
logger = __import__("logging").getLogger(__name__)

@bp.route('/api/life-goals/', methods=['GET'])
@bp.route('/api/life-goals', methods=['GET'])
@bp.route('/api/my-goals', methods=['GET'])
@bp.route('/api/life-goals', methods=['GET'])
def get_life_goals():
    """获取人生目标列表 - 动态统计项目和任务，MySQL不可用时fallback"""
    try:
        category = request.args.get('category', '')
        try:
            conn = get_db()
            c = conn.cursor()
            query = 'SELECT * FROM goals WHERE status = "active"'
            params = []
            if category:
                query += ' AND category = %s'
                params.append(category)
            query += ' ORDER BY id'
            c.execute(query, params)
            goals = [row_to_dict(row, c) for row in c.fetchall()]
            for goal in goals:
                goal['title'] = goal.get('name', goal.get('title', ''))
                gid = goal['id']
                c.execute('SELECT COUNT(*) as cnt FROM projects WHERE goal_id = %s AND status != "deleted"', (gid,))
                row = c.fetchone()
                goal['project_count'] = row['cnt'] if row else 0
                c.execute('SELECT COUNT(*) as cnt FROM tasks t JOIN projects p ON t.project_id = p.id WHERE p.goal_id = %s AND t.status != "deleted"', (gid,))
                row = c.fetchone()
                goal['task_count'] = row['cnt'] if row else 0
                c.execute('SELECT COUNT(*) as total, SUM(CASE WHEN t.status = "completed" THEN 1 ELSE 0 END) as done FROM tasks t JOIN projects p ON t.project_id = p.id WHERE p.goal_id = %s AND t.status != "deleted"', (gid,))
                row = c.fetchone()
                total = row['total'] if row and row['total'] else 0
                done = row['done'] if row and row['done'] else 0
                goal['progress'] = round((done / total) * 100) if total > 0 else 0
                try:
                    c.execute('SELECT id, description, target_value, current_value, unit, status FROM life_key_results WHERE life_goal_id = %s', (gid,))
                    goal['key_results'] = [row_to_dict(row, c) for row in c.fetchall()]
                except:
                    goal['key_results'] = []
            conn.close()
            return jsonify({'success': True, 'goals': goals, 'source': 'mysql'})
        except Exception as db_err:
            app.logger.warning(f"MySQL unavailable, using fallback: {db_err}")
            # Fallback: return hardcoded goals with last-known stats
            goals = [
                {"id":1,"name":"AI助手优化与效率提升","title":"AI助手优化与效率提升","description":"打造AI助手，提升工作效率","category":"tech","progress":70,"status":"active","project_count":12,"task_count":45,"key_results":[]},
                {"id":2,"name":"和光智成商业化成功","title":"和光智成商业化成功","description":"和光智成商业化运作","category":"business","progress":50,"status":"active","project_count":8,"task_count":28,"key_results":[]},
                {"id":3,"name":"学术竞争力建设","title":"学术竞争力建设","description":"提升学术影响力","category":"academic","progress":95,"status":"active","project_count":1,"task_count":8,"key_results":[]},
                {"id":4,"name":"财富增值与资产管理","title":"财富增值与资产管理","description":"实现财富增值","category":"finance","progress":0,"status":"active","project_count":1,"task_count":3,"key_results":[]},
                {"id":5,"name":"家庭幸福与子女教育","title":"家庭幸福与子女教育","description":"家庭幸福","category":"family","progress":0,"status":"active","project_count":1,"task_count":2,"key_results":[]},
                {"id":6,"name":"法律诉讼与社会工作","title":"法律诉讼与社会工作","description":"处理法律事务","category":"legal","progress":52,"status":"active","project_count":2,"task_count":5,"key_results":[]},
                {"id":7,"name":"身心健康与生活质量","title":"身心健康与生活质量","description":"保持身心健康","category":"health","progress":0,"status":"active","project_count":1,"task_count":1,"key_results":[]}
            ]
            return jsonify({'success': True, 'goals': goals, 'source': 'fallback'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/reviews', methods=['GET'])
def get_reviews():
    """获取审核列表"""
    try:
        conn = get_db()
        c = conn.cursor()
        status_filter = request.args.get('status')
        query = '''
            SELECT * FROM reviews
            ORDER BY created_at DESC
            LIMIT 100
        '''
        if status_filter:
            query = '''
                SELECT * FROM reviews
                WHERE status = %s
                ORDER BY created_at DESC
                LIMIT 100
            '''
            c.execute(query, (status_filter,))
        else:
            c.execute(query)
        reviews = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'reviews': reviews, 'total': len(reviews)})
    except Exception as e:
        logger.error(f"Error getting reviews: {e}")
        return jsonify({'success': False, 'error': str(e), 'reviews': []})

@bp.route('/api/reviews/<int:review_id>', methods=['PUT'])
def update_review(review_id):
    """更新审核状态"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        update_fields = []
        params = []
        if 'status' in data:
            update_fields.append('status = %s')
            params.append(data['status'])
        if 'reviewer_id' in data:
            update_fields.append('reviewer_id = %s')
            params.append(data['reviewer_id'])
        update_fields.append('updated_at = NOW()')
        params.append(review_id)
        query = f'UPDATE reviews SET ' + ', '.join(update_fields) + ' WHERE id = %s'
        c.execute(query, params)
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error updating review: {e}")
        return jsonify({'success': False, 'error': str(e)})


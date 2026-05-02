"""
战略目标-项目-任务关系图 API
"""
from flask import Blueprint, jsonify
import pymysql
import os

strategic_map_bp = Blueprint('strategic_map', __name__)

def get_db():
    config = {
        "host": os.environ.get("MYSQL_HOST", "rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "user": os.environ.get("MYSQL_USER", "kanban"),
        "password": os.environ.get("MYSQL_PASSWORD", "Irc210Irc210!"),
        "database": os.environ.get("MYSQL_DATABASE", "kanban"),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": False,
        "connect_timeout": 3,
        "read_timeout": 10,
    }
    return pymysql.connect(**config)

@strategic_map_bp.route('/api/strategic-map', methods=['GET'])
def get_strategic_map():
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute("SELECT id, title, category, progress, status FROM goals WHERE status != 'cancelled' ORDER BY id")
        goals = c.fetchall()
        
        c.execute("SELECT id, number, chinese_name as name, english_name, description, status, goal_id, start_date FROM projects WHERE status IN ('active', 'todo', '进行中') ORDER BY goal_id, id")
        projects = c.fetchall()
        
        c.execute("SELECT id, number, title, status, priority, project_id, goal_id, created_at FROM tasks WHERE status IN ('pending', 'in_progress', 'completed', 'failed_retryable') AND project_id IS NOT NULL ORDER BY project_id, id DESC LIMIT 500")
        tasks = c.fetchall()
        
        result = []
        for goal in goals:
            gid = goal['id']
            goal_projects = [p for p in projects if p.get('goal_id') == gid]
            
            goal_node = {
                'id': f"goal-{gid}",
                'type': 'goal',
                'name': goal['title'],
                'category': goal.get('category', ''),
                'progress': goal.get('progress', 0),
                'status': goal.get('status', ''),
                'project_count': len(goal_projects),
                'task_count': len([t for t in tasks if t.get('goal_id') == gid]),
                'children': []
            }
            
            for project in goal_projects:
                pid = project['id']
                project_tasks = [t for t in tasks if t.get('project_id') == pid]
                
                project_node = {
                    'id': f"project-{pid}",
                    'type': 'project',
                    'name': project['name'] or project['english_name'] or f"项目#{pid}",
                    'number': project.get('number', ''),
                    'status': project.get('status', ''),
                    'task_count': len(project_tasks),
                    'children': []
                }
                
                for task in project_tasks[:20]:
                    task_node = {
                        'id': f"task-{task['id']}",
                        'type': 'task',
                        'name': task['title'],
                        'number': task.get('number', ''),
                        'status': task.get('status', ''),
                        'priority': task.get('priority', ''),
                        'raw_id': task['id']
                    }
                    project_node['children'].append(task_node)
                
                goal_node['children'].append(project_node)
            
            result.append(goal_node)
        
        return jsonify({
            'success': True,
            'data': result,
            'summary': {
                'total_goals': len(goals),
                'total_projects': len(projects),
                'total_tasks': len(tasks)
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

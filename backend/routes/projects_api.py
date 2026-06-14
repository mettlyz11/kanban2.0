from flask import Blueprint, request, jsonify, send_file
import os
import uuid
import datetime
import pymysql
import logging

logger = logging.getLogger(__name__)

def get_db():
    """获取 MySQL 数据库连接"""
    # 从环境变量获取完整配置，确保密码正确传递
    import os
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
    conn = pymysql.connect(**config)
    return conn

def row_to_dict(row, cursor):
    """将行数据转换为字典，兼容SQLite和MySQL"""
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    # 元组情况，从cursor获取列名
    if hasattr(cursor, 'description') and cursor.description:
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    return row

bp = Blueprint('projects_api', __name__)

# 文件上传配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
# 允许的文件类型：pdf, doc, docx, md, txt, py, js, vue, sql
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'md', 'txt', 'py', 'js', 'vue', 'sql'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def check_project_member_permission(project_id, user_id=None):
    """检查用户是否是项目成员（简化版，可根据需要扩展）"""
    # TODO: 实现实际的项目成员验证逻辑
    # 目前允许所有已登录用户访问
    return True

def get_project_upload_path(project_id):
    """获取项目的上传目录路径"""
    upload_path = os.path.join(UPLOAD_FOLDER, 'projects', str(project_id))
    if not os.path.exists(upload_path):
        os.makedirs(upload_path, exist_ok=True)
    return upload_path

# ============================================
# 项目 API
# ============================================

@bp.route('/api/projects/', methods=['GET'])
@bp.route('/api/projects', methods=['GET'])
def get_projects():
    """获取所有项目"""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT 
            p.id, p.number, p.name, p.description, p.goal, p.summary, 
            p.status, p.priority, p.created_at, p.updated_at, p.deadline,
            COALESCE(t.task_stats, '{}') as task_stats_json
        FROM projects p
        LEFT JOIN (
            SELECT project_id, 
                   JSON_OBJECT(
                       'total', COUNT(*),
                       'completed', SUM(CASE WHEN status IN ('completed','done') THEN 1 ELSE 0 END),
                       'in_progress', SUM(CASE WHEN status IN ('in_progress','progress') THEN 1 ELSE 0 END),
                       'todo', SUM(CASE WHEN status IN ('pending','todo','pending_review') THEN 1 ELSE 0 END)
                   ) as task_stats
            FROM tasks 
            WHERE status != 'deleted'
            GROUP BY project_id
        ) t ON t.project_id = p.id
        WHERE p.status != 'deleted'
        ORDER BY p.created_at DESC
    ''')
    projects = []
    for row in c.fetchall():
        proj = row_to_dict(row, c)
        import json
        try:
            proj['task_stats'] = json.loads(proj.pop('task_stats_json', '{}'))
        except:
            proj['task_stats'] = {}
        projects.append(proj)
    conn.close()
    return jsonify({'success': True, 'projects': projects})

@bp.route('/api/projects', methods=['POST'])
def create_project():
    """创建新项目"""
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '')
    goal = data.get('goal', '')
    priority = data.get('priority', 'medium')
    status = data.get('status', 'todo')

    if not name:
        return jsonify({'success': False, 'error': '项目名称不能为空'}), 400

    conn = get_db()
    c = conn.cursor()

    # 生成项目编号
    c.execute("SELECT COUNT(*) FROM projects")
    count = list(c.fetchone().values())[0] + 1
    number = f"P{count:03d}"

    c.execute('''
        INSERT INTO projects (number, name, description, goal, priority, status, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
    ''', (number, name, description, goal, priority, status))

    project_id = c.lastrowid
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'project_id': project_id, 'number': number})

@bp.route('/api/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """更新项目"""
    data = request.get_json()

    allowed_fields = ['name', 'description', 'goal', 'goal_id', 'status', 'priority']
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return jsonify({'success': False, 'error': '没有要更新的字段'}), 400

    conn = get_db()
    c = conn.cursor()

    set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
    set_clause += ", updated_at = NOW()"
    values = list(updates.values()) + [project_id]

    c.execute(f'UPDATE projects SET {set_clause} WHERE id = %s', values)
    
    # 如果终止项目，自动取消所有待执行任务
    if updates.get('status') in ('archived', 'stopped', 'cancelled'):
        c.execute('UPDATE tasks SET status = "cancelled", updated_at = NOW() WHERE project_id = %s AND status IN ("pending", "in_progress", "pending_review")', (project_id,))
    
    conn.commit()
    conn.close()

    return jsonify({'success': True})

@bp.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """获取项目详情"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM projects WHERE id = %s AND status != "deleted"', (project_id,))
    project = c.fetchone()
    conn.close()
    if not project:
        return jsonify({'error': 'Not found', 'success': False}), 404
    return jsonify({'success': True, 'project': project})


@bp.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """删除项目"""
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE projects SET status = %s WHERE id = %s', ('deleted', project_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})
# ============================================
# 项目文档管理 API
# ============================================

@bp.route('/api/projects/<int:project_id>/documents', methods=['GET'])
@bp.route('/api/projects/<int:project_id>/document', methods=['GET'])
def get_project_documents(project_id):
    """获取项目文档列表"""
    try:
        # 检查项目是否存在
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id FROM projects WHERE id = %s AND status != "deleted"', (project_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '项目不存在'}), 404
    
        # 获取文档列表
        c.execute('''
            SELECT id, project_id, file_name, original_name, file_path, 
                   file_size, mime_type, description, uploaded_by, uploaded_at
            FROM project_documents
            WHERE project_id = %s
            ORDER BY uploaded_at DESC
        ''', (project_id,))
    
        documents = []
        for row in c.fetchall():
            doc = row_to_dict(row, c)
            # 格式化文件大小
            size = doc.get('file_size', 0)
            if size < 1024:
                doc['file_size_formatted'] = f"{size} B"
            elif size < 1024 * 1024:
                doc['file_size_formatted'] = f"{size / 1024:.1f} KB"
            else:
                doc['file_size_formatted'] = f"{size / (1024 * 1024):.1f} MB"
            documents.append(doc)
    
        conn.close()
    
        return jsonify({
            'success': True,
            'documents': documents,
            'count': len(documents)
        })
    except Exception as e:
        logger.error(f"获取项目文档列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@bp.route('/api/projects/<int:project_id>/documents', methods=['POST'])
@bp.route('/api/projects/<int:project_id>/document', methods=['POST'])
def upload_project_document(project_id):
    """上传项目文档"""
    try:
        # 检查权限
        if not check_project_member_permission(project_id):
            return jsonify({'success': False, 'error': '无权访问此项目'}), 403
    
        # 检查项目是否存在
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id FROM projects WHERE id = %s AND status != "deleted"', (project_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '项目不存在'}), 404
    
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有文件'}), 400
    
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '没有选择文件'}), 400
    
        # 检查文件大小
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
    
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False, 
                'error': f'文件大小超过限制，最大允许 {MAX_FILE_SIZE / (1024*1024):.0f}MB'
            }), 413
    
        if file and allowed_file(file.filename):
            # 生成安全的文件名
            original_filename = file.filename
            file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
            safe_filename = f"{uuid.uuid4().hex}_{original_filename}"
        
            # 确定MIME类型
            mime_type = file.content_type or 'application/octet-stream'
        
            # 获取上传路径并保存文件
            upload_path = get_project_upload_path(project_id)
            file_path = os.path.join(upload_path, safe_filename)
            file.save(file_path)
        
            # 获取文件大小
            file_size = os.path.getsize(file_path)
        
            # 获取描述
            description = request.form.get('description', '')
            uploaded_by = request.form.get('uploaded_by', 'system')
        
            # 计算相对路径
            relative_path = os.path.join('projects', str(project_id), safe_filename)
        
            # 保存到数据库
            c.execute('''
                INSERT INTO project_documents 
                (project_id, file_name, original_name, file_path, file_size, 
                 mime_type, description, uploaded_by, uploaded_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ''', (project_id, safe_filename, original_filename, relative_path, 
                  file_size, mime_type, description, uploaded_by))
        
            doc_id = c.lastrowid
            conn.commit()
            conn.close()
        
            return jsonify({
                'success': True,
                'message': '文件上传成功',
                'document': {
                    'id': doc_id,
                    'project_id': project_id,
                    'file_name': safe_filename,
                    'original_name': original_filename,
                    'file_size': file_size,
                    'file_size_formatted': f"{file_size / (1024 * 1024):.1f} MB" if file_size >= 1024 * 1024 else f"{file_size / 1024:.1f} KB",
                    'mime_type': mime_type,
                    'description': description,
                    'uploaded_by': uploaded_by,
                    'uploaded_at': datetime.now().isoformat()
                }
            })
        else:
            return jsonify({
                'success': False, 
                'error': '不支持的文件类型。支持的类型: ' + ', '.join(ALLOWED_EXTENSIONS)
            }), 400
        
    except Exception as e:
        logger.error(f"上传项目文档失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/projects/<int:project_id>/document/<int:doc_id>/download', methods=['GET'])
def download_project_document(project_id, doc_id):
    """下载项目文档"""
    try:
        # 检查项目是否存在
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id FROM projects WHERE id = %s AND status != "deleted"', (project_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '项目不存在'}), 404
    
        # 获取文档信息
        c.execute('''
            SELECT file_name, original_name, file_path, mime_type
            FROM project_documents
            WHERE id = %s AND project_id = %s
        ''', (doc_id, project_id))
    
        row = c.fetchone()
        conn.close()
    
        if not row:
            return jsonify({'success': False, 'error': '文档不存在'}), 404
    
        # 构建完整文件路径
        file_path = os.path.join(UPLOAD_FOLDER, row['file_path'])
    
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': '文件不存在'}), 404
    
        # 发送文件
        return send_file(
            file_path,
            as_attachment=True,
            download_name=row['original_name'],
            mimetype=row['mime_type'] or 'application/octet-stream'
        )
    
    except Exception as e:
        logger.error(f"下载项目文档失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/projects/<int:project_id>/documents/<int:doc_id>', methods=['DELETE'])
@bp.route('/api/projects/<int:project_id>/document/<int:doc_id>', methods=['DELETE'])
def delete_project_document(project_id, doc_id):
    """删除项目文档"""
    try:
        # 检查项目是否存在
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id FROM projects WHERE id = %s AND status != "deleted"', (project_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '项目不存在'}), 404
    
        # 获取文档信息
        c.execute('''
            SELECT file_path FROM project_documents
            WHERE id = %s AND project_id = %s
        ''', (doc_id, project_id))
    
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'error': '文档不存在'}), 404
    
        # 删除物理文件
        file_path = os.path.join(UPLOAD_FOLDER, row['file_path'])
        if os.path.exists(file_path):
            os.remove(file_path)
    
        # 删除数据库记录
        c.execute('DELETE FROM project_documents WHERE id = %s', (doc_id,))
        conn.commit()
        conn.close()
    
        return jsonify({
            'success': True,
            'message': '文档已删除'
        })
    
    except Exception as e:
        logger.error(f"删除项目文档失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/projects/<int:project_id>/document/<int:doc_id>', methods=['PUT'])
@bp.route('/api/projects/<int:project_id>/documents/<int:doc_id>', methods=['PUT'])
def update_project_document(project_id, doc_id):
    """更新项目文档信息（仅元数据，不包括文件本身）"""
    try:
        data = request.get_json()
    
        # 检查项目是否存在
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id FROM projects WHERE id = %s AND status != "deleted"', (project_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '项目不存在'}), 404
    
        # 检查文档是否存在
        c.execute('SELECT id FROM project_documents WHERE id = %s AND project_id = %s', (doc_id, project_id))
        if not c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '文档不存在'}), 404
    
        # 允许更新的字段
        allowed_fields = ['description']
        updates = {k: v for k, v in data.items() if k in allowed_fields}
    
        if not updates:
            conn.close()
            return jsonify({'success': False, 'error': '没有要更新的字段'}), 400
    
        # 构建更新语句
        set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
        set_clause += ", updated_at = NOW()"
        values = list(updates.values()) + [doc_id]
    
        c.execute(f'UPDATE project_documents SET {set_clause} WHERE id = %s', values)
        conn.commit()
        conn.close()
    
        return jsonify({
            'success': True,
            'message': '文档信息已更新'
        })
    
    except Exception as e:
        logger.error(f"更新项目文档失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# 项目总结 API
# ============================================

@bp.route('/api/projects/<int:project_id>/summary', methods=['GET'])
def get_project_summary(project_id):
    """获取项目总结"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT summary FROM projects WHERE id = %s AND status != "deleted"', (project_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        return jsonify({'success': True, 'summary': row['summary'] or ''})
    except Exception as e:
        logger.error(f"获取项目总结失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/projects/<int:project_id>/summary', methods=['PUT'])
def update_project_summary(project_id):
    """手动更新项目总结"""
    try:
        data = request.get_json()
        summary = data.get('summary', '').strip()
        conn = get_db()
        c = conn.cursor()
        c.execute('UPDATE projects SET summary = %s, updated_at = NOW() WHERE id = %s', (summary, project_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '项目总结已更新'})
    except Exception as e:
        logger.error(f"更新项目总结失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/projects/<int:project_id>/generate-summary', methods=['POST'])
def generate_project_summary(project_id):
    """自动生成项目总结（基于任务数据 + 项目信息）"""
    try:
        conn = get_db()
        c = conn.cursor()

        # 获取项目信息
        c.execute('SELECT name, number, description, goal FROM projects WHERE id = %s AND status != "deleted"', (project_id,))
        project = c.fetchone()
        if not project:
            conn.close()
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        # 获取项目任务
        c.execute('''
            SELECT title, status, priority, created_at, updated_at, task_type, description
            FROM tasks
            WHERE project_id = %s AND status != 'deleted'
            ORDER BY created_at DESC
        ''', (project_id,))

        tasks = c.fetchall()
        conn.close()

        # 统计任务状态
        total = len(tasks)
        completed = sum(1 for t in tasks if t['status'] in ("completed", "done"))
        in_progress = sum(1 for t in tasks if t['status'] == "in_progress")
        todo = sum(1 for t in tasks if t['status'] in ("pending", "todo"))
        pending_review = sum(1 for t in tasks if t['status'] == 'pending_review')

        # 生成结构化总结
        lines = []
        lines.append(f'## 项目概览')
        lines.append(f'- **项目名称**: {project["name"]}')
        lines.append(f'- **项目编号**: {project["number"]}')
        lines.append(f'- **目标**: {project["goal"] or "未设定"}')
        lines.append(f'')

        # 进度概览
        progress_pct = round(completed / total * 100, 1) if total > 0 else 0
        lines.append(f'## 进度概览')
        lines.append(f'- **总任务数**: {total}')
        lines.append(f'- **已完成**: {completed} ({progress_pct}%)')
        lines.append(f'- **进行中**: {in_progress}')
        lines.append(f'- **待办**: {todo}')
        lines.append(f'- **待审核**: {pending_review}')

        if total > 0:
            remaining = total - completed
            lines.append(f'- **剩余任务**: {remaining}')
            if remaining > 0:
                lines.append(f'- **距目标**: 还需完成 {remaining} 个任务（{100 - progress_pct}%）')
            else:
                lines.append(f'- **距目标**: ✅ 全部完成')
        lines.append(f'')

        # 进行中任务列表
        if in_progress > 0:
            lines.append(f'## 当前进行中的任务')
            for t in tasks:
                if t['status'] == "in_progress":
                    lines.append(f'- {t["title"]}')
            lines.append(f'')

        # 最近完成的任务（前5个）
        recent_done = [t for t in tasks if t['status'] in ("completed", "done")][:5]
        if recent_done:
            lines.append(f'## 最近完成的任务')
            for t in recent_done:
                lines.append(f'- ✅ {t["title"]}')
            lines.append(f'')

        # 待办任务预览
        if todo > 0:
            todo_list = [t for t in tasks if t['status'] in ("pending", "todo")][:5]
            lines.append(f'## 下一步待办')
            for t in todo_list:
                lines.append(f'- {t["title"]}')
            if todo > 5:
                lines.append(f'- ... 及其他 {todo - 5} 个待办任务')
            lines.append(f'')

        summary = '\n'.join(lines)

        # 保存到数据库
        conn2 = get_db()
        c2 = conn2.cursor()
        c2.execute('UPDATE projects SET summary = %s, updated_at = NOW() WHERE id = %s', (summary, project_id))
        conn2.commit()
        conn2.close()

        return jsonify({
            'success': True,
            'summary': summary,
            'stats': {
                'total': total,
                'completed': completed,
                'in_progress': in_progress,
                'todo': todo,
                'pending_review': pending_review,
                'progress_pct': progress_pct
            }
        })

    except Exception as e:
        logger.error(f"生成项目总结失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

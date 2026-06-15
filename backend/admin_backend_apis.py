"""
管理员后台 API 扩展 - command/monitor/feedback/long-tasks
追加到 admin_routes.py 末尾
"""
import json, os, sys
from datetime import datetime, date, timedelta
from flask import request, jsonify, current_app

# ============================================
# 指挥台 API
# ============================================
@admin_bp.route("/command", methods=["POST"])
def admin_create_command():
    """从指挥台创建任务"""
    try:
        data = request.get_json() or {}
        command = data.get("command", "").strip()
        if not command:
            return jsonify({"success": False, "error": "指令不能为空"}), 400
        
        from database_config import get_db_connection
        import pymysql
        
        now = datetime.now()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 生成任务编号
            today = now.strftime("%Y%m%d")
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE created_date = CURDATE()")
            count = cursor.fetchone()[0] + 1
            number = f"CMD-{today}-{count:04d}"
            
            # 创建任务
            cursor.execute(
                """INSERT INTO tasks (number, title, description, status, priority, 
                   task_type, created_at, updated_at, created_date, execution_mode)
                   VALUES (%s, %s, %s, 'pending', 'high', 'admin_command',
                   NOW(), NOW(), CURDATE(), 'auto')""",
                (number, command[:200], command,)
            )
            conn.commit()
            task_id = cursor.lastrowid
        
        return jsonify({"success": True, "task_id": task_id, "number": number})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/command/history", methods=["GET"])
def admin_command_history():
    """获取指挥台指令历史"""
    try:
        from database_config import get_db_connection
        import pymysql
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                """SELECT id, number, title, status, created_at 
                   FROM tasks WHERE task_type = 'admin_command' 
                   ORDER BY created_at DESC LIMIT 20"""
            )
            commands = cursor.fetchall()
        return jsonify({"success": True, "commands": commands})
    except Exception as e:
        # Fallback: return empty
        return jsonify({"success": True, "commands": []})

# ============================================
# 监控台 API
# ============================================
@admin_bp.route("/monitor/status", methods=["GET"])
def admin_monitor_status():
    """获取监控台状态"""
    try:
        from database_config import get_db_connection
        import pymysql
        
        result = {
            "ai_state": "idle",
            "ai_sub": "",
            "stats": {"tasks_completed": 0, "tasks_created": 0, "active_tasks": 0},
            "running_tasks": [],
            "timeline": []
        }
        
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 今日统计
            cursor.execute(
                """SELECT 
                    SUM(CASE WHEN status = 'done' AND DATE(updated_at) = CURDATE() THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN DATE(created_at) = CURDATE() THEN 1 ELSE 0 END) as created,
                    SUM(CASE WHEN status NOT IN ('done','cancelled','archived') THEN 1 ELSE 0 END) as active
                   FROM tasks"""
            )
            row = cursor.fetchone()
            if row:
                result["stats"] = {
                    "tasks_completed": row["completed"] or 0,
                    "tasks_created": row["created"] or 0,
                    "active_tasks": row["active"] or 0
                }
            
            # 正在执行的任务
            cursor.execute(
                """SELECT id, number, title, status, current_stage, 
                          stage_history, overall_status, waiting_for_user 
                   FROM tasks 
                   WHERE status NOT IN ('done','cancelled','archived') 
                     AND (overall_status = 'running' OR waiting_for_user = 1)
                   ORDER BY updated_at DESC LIMIT 10"""
            )
            running = cursor.fetchall()
            result["running_tasks"] = []
            for t in running:
                stage_history = t.get("stage_history") or "[]"
                if isinstance(stage_history, str):
                    try: stages = json.loads(stage_history)
                    except: stages = []
                else: stages = stage_history or []
                
                total_stages = len(stages) or 1
                done_stages = sum(1 for s in stages if isinstance(s, dict) and s.get("status") == "done") if isinstance(stages, list) else 0
                progress = round(done_stages / total_stages * 100)
                
                result["running_tasks"].append({
                    "id": t["id"],
                    "number": t["number"],
                    "title": t["title"],
                    "status": t["status"],
                    "current_stage": t["current_stage"] or t.get("overall_status", ""),
                    "waiting_for_user": bool(t.get("waiting_for_user")),
                    "progress": progress
                })
            
            # 判断 AI 状态
            if result["running_tasks"]:
                waiting = any(t.get("waiting_for_user") for t in result["running_tasks"])
                result["ai_state"] = "waiting" if waiting else "working"
                result["ai_sub"] = f"{len(result['running_tasks'])} 个任务进行中"
            else:
                result["ai_state"] = "idle"
                result["ai_sub"] = "当前无活跃任务"
            
            # 最近活动时间线
            cursor.execute(
                """SELECT id, action, description, entity_type, created_at 
                   FROM activity_log 
                   ORDER BY created_at DESC LIMIT 20"""
            )
            timeline = cursor.fetchall()
            result["timeline"] = [
                {"time": str(a["created_at"]) if a.get("created_at") else "", 
                 "text": a.get("description") or a.get("action", "")}
                for a in timeline
            ]
        
        return jsonify({"success": True, "status": result})
    except Exception as e:
        return jsonify({"success": True, "status": {
            "ai_state": "idle",
            "ai_sub": "数据库查询异常: " + str(e),
            "stats": {"tasks_completed": 0, "tasks_created": 0, "active_tasks": 0},
            "running_tasks": [],
            "timeline": []
        }})

# ============================================
# 反馈台 API
# ============================================
@admin_bp.route("/feedback/pending", methods=["GET"])
def admin_feedback_pending():
    """获取待评价任务"""
    try:
        from database_config import get_db_connection
        import pymysql
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                """SELECT t.id, t.number, t.title, t.updated_at, t.completed_at, t.result_summary
                   FROM tasks t
                   LEFT JOIN feedback_ratings fr ON t.id = fr.task_id AND fr.stage IS NULL
                   WHERE t.status = 'done' AND fr.id IS NULL
                   ORDER BY t.updated_at DESC LIMIT 20"""
            )
            pending = cursor.fetchall()
        return jsonify({"success": True, "items": pending})
    except Exception as e:
        return jsonify({"success": True, "items": []})

@admin_bp.route("/feedback/history", methods=["GET"])
def admin_feedback_history():
    """获取已评价记录"""
    try:
        from database_config import get_db_connection
        import pymysql
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                """SELECT fr.id, fr.task_id, fr.rating, fr.comment, fr.created_at as feedback_time,
                          t.number, t.title, t.updated_at
                   FROM feedback_ratings fr
                   LEFT JOIN tasks t ON fr.task_id = t.id
                   WHERE fr.stage IS NULL
                   ORDER BY fr.created_at DESC LIMIT 30"""
            )
            history = cursor.fetchall()
        return jsonify({"success": True, "items": history})
    except Exception as e:
        return jsonify({"success": True, "items": []})

@admin_bp.route("/feedback", methods=["POST"])
def admin_submit_feedback():
    """提交反馈评价"""
    try:
        data = request.get_json() or {}
        task_id = data.get("task_id")
        rating = data.get("rating")
        comment = data.get("comment", "")
        
        if not task_id or rating is None:
            return jsonify({"success": False, "error": "缺少 task_id 或 rating"}), 400
        
        from database_config import get_db_connection
        import pymysql
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO feedback_ratings (task_id, rating, comment, created_by, created_at)
                   VALUES (%s, %s, %s, 'admin', NOW())""",
                (task_id, int(rating), comment)
            )
            conn.commit()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================
# 长程任务 API
# ============================================
@admin_bp.route("/long-tasks", methods=["GET"])
def admin_long_tasks_list():
    """获取长程任务列表"""
    try:
        from database_config import get_db_connection
        import pymysql
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                """SELECT t.id, t.number, t.title, t.description, t.status, 
                          t.current_stage, t.stage_history, t.created_at, t.updated_at,
                          t.overall_status
                   FROM tasks t
                   WHERE t.task_type IN ('long_task', 'long_running', 'multi_stage')
                      OR (t.stage_history IS NOT NULL AND t.stage_history != '')
                   ORDER BY t.updated_at DESC LIMIT 30"""
            )
            tasks = cursor.fetchall()
            
            result_tasks = []
            for t in tasks:
                stage_history = t.get("stage_history") or "[]"
                if isinstance(stage_history, str):
                    try: stages = json.loads(stage_history)
                    except: stages = []
                else: stages = stage_history or []
                
                result_tasks.append({
                    "id": t["id"],
                    "number": t["number"],
                    "title": t["title"],
                    "description": t["description"],
                    "status": t.get("overall_status") or t["status"],
                    "current_stage": t["current_stage"],
                    "stages": stages,
                    "created_at": str(t["created_at"]) if t.get("created_at") else "",
                    "updated_at": str(t["updated_at"]) if t.get("updated_at") else ""
                })
        
        return jsonify({"success": True, "tasks": result_tasks})
    except Exception as e:
        return jsonify({"success": True, "tasks": []})

@admin_bp.route("/long-tasks/<int:task_id>", methods=["GET"])
def admin_long_task_detail(task_id):
    """获取长程任务详情"""
    try:
        from database_config import get_db_connection
        import pymysql
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                """SELECT t.*, GROUP_CONCAT(
                          JSON_OBJECT('stage', ts.stage, 'status', ts.status, 
                                      'output', ts.output, 'started_at', ts.started_at,
                                      'completed_at', ts.completed_at)) as task_stages
                   FROM tasks t
                   LEFT JOIN task_stages ts ON t.id = ts.task_id
                   WHERE t.id = %s
                   GROUP BY t.id""",
                (task_id,)
            )
            task = cursor.fetchone()
            if not task:
                return jsonify({"success": False, "error": "任务不存在"}), 404
            
            # Parse stages from stage_history or task_stages
            stages = []
            stage_history = task.get("stage_history") or "[]"
            if isinstance(stage_history, str):
                try: stages_parsed = json.loads(stage_history)
                except: stages_parsed = []
            else: stages_parsed = stage_history or []
            
            if stages_parsed:
                for s in stages_parsed:
                    if isinstance(s, dict):
                        stages.append({
                            "stage": s.get("stage", s.get("name", "")),
                            "status": s.get("status", "waiting"),
                            "output": s.get("output", s.get("result", "")),
                            "started_at": s.get("started_at", ""),
                            "completed_at": s.get("completed_at", ""),
                            "done_by": s.get("done_by", s.get("assignee", "")),
                            "duration": s.get("duration", "")
                        })
            else:
                # Try task_stages
                cursor.execute(
                    """SELECT stage, status, output, started_at, completed_at
                       FROM task_stages WHERE task_id = %s ORDER BY stage_order""",
                    (task_id,)
                )
                db_stages = cursor.fetchall()
                for s in db_stages:
                    stages.append({
                        "stage": s["stage"],
                        "status": s["status"],
                        "output": s["output"],
                        "started_at": str(s["started_at"]) if s.get("started_at") else "",
                        "completed_at": str(s["completed_at"]) if s.get("completed_at") else "",
                        "done_by": "",
                        "duration": ""
                    })
            
            # Decisions from execution_log or review_feedback
            decisions = []
            exec_log = task.get("execution_log") or ""
            if exec_log:
                try: 
                    log_data = json.loads(exec_log)
                    if isinstance(log_data, list):
                        decisions = log_data
                    elif isinstance(log_data, dict):
                        decisions = [log_data]
                except:
                    pass
            
            result = {
                "id": task["id"],
                "number": task["number"],
                "title": task["title"],
                "description": task["description"],
                "status": task.get("overall_status") or task["status"],
                "stages": stages,
                "decisions": decisions,
                "created_at": str(task["created_at"]) if task.get("created_at") else "",
                "updated_at": str(task["updated_at"]) if task.get("updated_at") else ""
            }
        
        return jsonify({"success": True, "task": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================
# 任务详情 & JSON 描述编辑 API
# ============================================================

@admin_bp.route("/tasks/detail/<int:task_id>", methods=["GET"])
def admin_get_task_detail(task_id):
    """获取任务详情（含 execution_log for PhaseR）"""
    from database_config import get_db_connection
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("""
                SELECT t.*, p.name as project_name, g.title as goal_title
                FROM tasks t
                LEFT JOIN projects p ON t.project_id = p.id
                LEFT JOIN goals g ON p.goal_id = g.id
                WHERE t.id = %s
            """, (task_id,))
            task = cursor.fetchone()
            if not task:
                return jsonify({"success": False, "error": "任务不存在"}), 404
            
            # 转换datetime
            for k in ['created_at', 'updated_at', 'start_time']:
                if task.get(k):
                    task[k] = str(task[k])
            
            return jsonify({"success": True, "task": task})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/tasks/<int:task_id>/description", methods=["PUT"])
def admin_update_task_description(task_id):
    """更新任务 JSON 描述"""
    data = request.get_json()
    if not data or "description" not in data:
        return jsonify({"success": False, "error": "缺少 description 字段"}), 400
    
    from database_config import get_db_connection
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET description = %s, updated_at = NOW() WHERE id = %s",
                (data["description"], task_id)
            )
            conn.commit()
            return jsonify({"success": True, "message": "描述已更新"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# 附件管理 API
# ============================================================

@admin_bp.route("/attachments/<int:task_id>", methods=["GET"])
def admin_get_attachments(task_id):
    """获取任务附件列表"""
    from database_config import get_db_connection
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT id, filename, url, size, file_type, created_at FROM attachments WHERE entity_type='task' AND entity_id=%s ORDER BY created_at DESC",
                (task_id,))
            rows = cursor.fetchall()
            for r in rows:
                if r.get('created_at'):
                    r['created_at'] = str(r['created_at'])
            return jsonify({"success": True, "data": rows})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/attachments/<int:task_id>/add-url", methods=["POST"])
def admin_add_attachment_url(task_id):
    """通过URL添加附件"""
    data = request.get_json()
    url = (data or {}).get("url", "").strip()
    if not url:
        return jsonify({"success": False, "error": "请输入URL"}), 400
    
    filename = url.rsplit("/", 1)[-1] if "/" in url else url
    if not filename:
        filename = "file_" + str(task_id)
    
    from database_config import get_db_connection
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type, created_at) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
                ("task", task_id, filename, url, 0, "reference"))
            conn.commit()
            return jsonify({"success": True, "message": "附件已添加"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/attachments/<int:attach_id>", methods=["DELETE"])
def admin_delete_attachment(attach_id):
    """删除附件"""
    from database_config import get_db_connection
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM attachments WHERE id = %s", (attach_id,))
            conn.commit()
            return jsonify({"success": True, "message": "已删除"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/attachments/upload", methods=["POST"])
def admin_upload_attachment():
    """上传附件文件"""
    import os as _os
    from werkzeug.utils import secure_filename
    
    task_id = request.form.get("task_id", type=int)
    file = request.files.get("file")
    
    if not task_id:
        return jsonify({"success": False, "error": "缺少 task_id"}), 400
    if not file:
        return jsonify({"success": False, "error": "请选择文件"}), 400
    
    upload_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "uploads", "docs")
    _os.makedirs(upload_dir, exist_ok=True)
    
    filename = secure_filename(file.filename)
    if not filename:
        ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin"
        from datetime import datetime as _dt
        filename = f"upload_{_dt.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
    
    filepath = _os.path.join(upload_dir, filename)
    file.save(filepath)
    file_size = _os.path.getsize(filepath)
    url = f"/uploads/docs/{filename}"
    
    from database_config import get_db_connection
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type, created_at) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
                ("task", task_id, filename, url, file_size, "upload"))
            conn.commit()
            return jsonify({"success": True, "message": "文件已上传", "filename": filename, "url": url})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


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

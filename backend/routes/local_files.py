"""Routes: local_files"""
from flask import Blueprint, jsonify, request
import os
import json
from routes.helpers import get_db
from datetime import datetime

bp = Blueprint('routes_local_files', __name__)

@bp.route("/api/local-files", methods=["GET"])
def get_local_files():
    """获取 Mac mini Files 文件夹文件列表"""
    import json
    try:
        idx_path = "/opt/kanban-react/backend/local_files_index.json"
        if not os.path.exists(idx_path):
            return jsonify({"success": True, "files": [], "total": 0, "source": "none"})
        with open(idx_path, "r") as f:
            data = json.load(f)
        return jsonify({"success": True, **data})
    except:
        return jsonify({"success": True, "files": [], "total": 0, "source": "error"})


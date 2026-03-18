#!/usr/bin/env python3
# file_tree_api.py - 文件目录树 API
# 用途：扫描 Files 目录，生成树状结构 JSON

import os
import json
from datetime import datetime

BASE_DIR = "/Users/mettlyz/.openclaw/workspace/Files"

def scan_directory(path, base_path):
    """递归扫描目录，生成树状结构"""
    result = {
        "name": os.path.basename(path) or path,
        "path": os.path.relpath(path, base_path),
        "type": "directory",
        "children": [],
        "size": 0,
        "modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
    }
    
    try:
        for item in sorted(os.listdir(path)):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                child = scan_directory(item_path, base_path)
                result["children"].append(child)
                result["size"] += child["size"]
            else:
                stat = os.stat(item_path)
                result["children"].append({
                    "name": item,
                    "path": os.path.relpath(item_path, base_path),
                    "type": "file",
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "ext": os.path.splitext(item)[1]
                })
                result["size"] += stat.st_size
    except PermissionError:
        pass
    
    return result

def get_file_tree():
    """获取文件树"""
    if not os.path.exists(BASE_DIR):
        return {"error": "Files directory not found"}
    
    return scan_directory(BASE_DIR, BASE_DIR)

if __name__ == "__main__":
    tree = get_file_tree()
    print(json.dumps(tree, indent=2, ensure_ascii=False))

# API 端点 - 获取用户个人信息
@app.route('/api/user-profile', methods=['GET'])
def get_user_profile():
    """获取用户个人信息和公司信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取个人信息
        cursor.execute('SELECT * FROM user_profiles WHERE user_id = 1 LIMIT 1')
        profile_row = cursor.fetchone()
        
        profile = None
        if profile_row:
            profile = {
                'user_id': profile_row[1],
                'name': profile_row[2],
                'title': profile_row[3],
                'department': profile_row[4],
                'phone': profile_row[5],
                'email': profile_row[6],
                'avatar': profile_row[7],
                'bio': profile_row[8]
            }
        
        # 获取公司信息
        cursor.execute('SELECT * FROM company_info WHERE id = 1 LIMIT 1')
        company_row = cursor.fetchone()
        
        company = None
        if company_row:
            company = {
                'name': company_row[1],
                'short_name': company_row[2],
                'logo': company_row[3],
                'address': company_row[4],
                'phone': company_row[5],
                'email': company_row[6],
                'website': company_row[7],
                'description': company_row[8],
                'industry': company_row[9],
                'founded_year': company_row[10]
            }
        
        conn.close()
        
        return jsonify({
            'success': True,
            'profile': profile,
            'company': company
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API 端点 - 获取文件树
@app.route('/api/file-tree', methods=['GET'])
def get_file_tree():
    """获取文件资源库树状结构"""
    try:
        import os
        import json
        from datetime import datetime
        
        base_dir = '/opt/kanban-react/Files'
        
        def scan_directory(path, base_path):
            result = {
                'name': os.path.basename(path) or path,
                'path': os.path.relpath(path, base_path),
                'type': 'directory',
                'children': [],
                'size': 0,
                'modified': datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
            }
            
            try:
                for item in sorted(os.listdir(path)):
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        child = scan_directory(item_path, base_path)
                        result['children'].append(child)
                        result['size'] += child['size']
                    else:
                        stat = os.stat(item_path)
                        result['children'].append({
                            'name': item,
                            'path': os.path.relpath(item_path, base_path),
                            'type': 'file',
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'ext': os.path.splitext(item)[1]
                        })
                        result['size'] += stat.st_size
            except PermissionError:
                pass
            
            return result
        
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        
        tree = scan_directory(base_dir, base_dir)
        
        return jsonify({
            'success': True,
            'tree': tree
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API 端点 - 获取版本历史
@app.route('/api/versions', methods=['GET'])
def get_versions():
    """获取所有项目的版本历史"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取所有版本记录
        cursor.execute('''
            SELECT project, version, deployed_at, git_commit, notes
            FROM deployment_versions
            ORDER BY deployed_at DESC
            LIMIT 50
        ''')
        
        versions = []
        for row in cursor.fetchall():
            versions.append({
                'project': row[0],
                'version': row[1],
                'deployed_at': row[2],
                'git_commit': row[3],
                'notes': row[4]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'versions': versions
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API 端点 - 获取最新版本
@app.route('/api/versions/latest', methods=['GET'])
def get_latest_versions():
    """获取所有项目的最新版本"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取每个项目的最新版本
        cursor.execute('''
            SELECT project, version, deployed_at, git_commit, notes
            FROM deployment_versions dv1
            WHERE deployed_at = (
                SELECT MAX(deployed_at)
                FROM deployment_versions dv2
                WHERE dv2.project = dv1.project
            )
        ''')
        
        versions = {}
        for row in cursor.fetchall():
            versions[row[0]] = {
                'version': row[1],
                'deployed_at': row[2],
                'git_commit': row[3],
                'notes': row[4]
            }
        
        conn.close()
        
        return jsonify({
            'success': True,
            'versions': versions
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

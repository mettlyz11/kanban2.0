"""
工作流程架构图 API 路由
提供可编辑的 Dudu 工作流程架构图功能
"""

from flask import Blueprint, request, jsonify
import sqlite3
import os
import json
from datetime import datetime
from functools import wraps

workflow_arch_bp = Blueprint('workflow_arch', __name__)

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kanban_v5.db')
WORKSPACE_PATH = '/Users/mettlyz/.openclaw/workspace'

def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def save_version(nodes, connections, description="自动保存"):
    """保存版本历史"""
    conn = get_db()
    c = conn.cursor()
    
    # 获取当前最大版本号
    c.execute('SELECT MAX(version) FROM workflow_architecture_versions')
    max_version = c.fetchone()[0] or 0
    new_version = max_version + 1
    
    # 保存新版本
    c.execute('''
        INSERT INTO workflow_architecture_versions (version, nodes_json, connections_json, description)
        VALUES (?, ?, ?, ?)
    ''', (new_version, json.dumps(nodes, ensure_ascii=False), json.dumps(connections, ensure_ascii=False), description))
    
    conn.commit()
    conn.close()
    
    return new_version

@workflow_arch_bp.route('/api/workflow-architecture', methods=['GET'])
def get_workflow_architecture():
    """获取架构图数据"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 获取所有节点
        c.execute('SELECT * FROM workflow_architecture ORDER BY id')
        nodes = []
        for row in c.fetchall():
            nodes.append({
                'id': row['id'],
                'name': row['name'],
                'type': row['type'],
                'x': row['x'],
                'y': row['y'],
                'color': row['color'],
                'file_path': row['file_path'],
                'description': row['description'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
        
        # 获取所有连接
        c.execute('SELECT * FROM workflow_connections')
        connections = []
        for row in c.fetchall():
            connections.append({
                'id': row['id'],
                'from_node': row['from_node'],
                'to_node': row['to_node']
            })
        
        # 获取最新版本号
        c.execute('SELECT MAX(version) as version FROM workflow_architecture_versions')
        max_version = c.fetchone()[0] or 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'nodes': nodes,
                'connections': connections,
                'version': max_version
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@workflow_arch_bp.route('/api/workflow-architecture', methods=['PUT'])
def save_workflow_architecture():
    """保存架构图修改"""
    try:
        data = request.get_json()
        nodes = data.get('nodes', [])
        connections = data.get('connections', [])
        
        conn = get_db()
        c = conn.cursor()
        
        # 更新节点
        for node in nodes:
            c.execute('''
                UPDATE workflow_architecture 
                SET name=?, type=?, x=?, y=?, color=?, file_path=?, description=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (
                node.get('name'),
                node.get('type', 'node'),
                node.get('x', 0),
                node.get('y', 0),
                node.get('color'),
                node.get('file_path'),
                node.get('description'),
                node.get('id')
            ))
        
        # 清除旧连接并插入新连接
        c.execute('DELETE FROM workflow_connections')
        for conn_item in connections:
            c.execute('''
                INSERT INTO workflow_connections (from_node, to_node)
                VALUES (?, ?)
            ''', (conn_item.get('from_node'), conn_item.get('to_node')))
        
        conn.commit()
        conn.close()
        
        # 保存版本历史
        save_version(nodes, connections, "手动保存")
        
        return jsonify({
            'success': True,
            'message': '架构图已保存',
            'version': save_version(nodes, connections)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@workflow_arch_bp.route('/api/workflow-architecture/sync', methods=['POST'])
def sync_workflow_architecture():
    """从实际文件同步架构图"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 需要同步的文件列表
        files_to_sync = [
            'SOUL.md', 'USER.md', 'AGENTS.md', 'standards.md', 
            'MEMORY.md', 'HEARTBEAT.md', 'CHECKLIST.md'
        ]
        
        synced_files = []
        
        for filename in files_to_sync:
            filepath = os.path.join(WORKSPACE_PATH, filename)
            if os.path.exists(filepath):
                # 读取文件内容
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 提取关键信息（标题和描述）
                lines = content.split('\n')
                title = lines[0].replace('#', '').strip() if lines else filename
                description = lines[1].replace('#', '').strip() if len(lines) > 1 else ''
                
                # 更新数据库中的节点
                c.execute('''
                    UPDATE workflow_architecture 
                    SET description=?, updated_at=CURRENT_TIMESTAMP
                    WHERE file_path=?
                ''', (description, filename))
                
                if c.rowcount > 0:
                    synced_files.append(filename)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'已同步 {len(synced_files)} 个文件',
            'synced_files': synced_files
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@workflow_arch_bp.route('/api/workflow-architecture/versions', methods=['GET'])
def get_workflow_versions():
    """获取版本历史"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            SELECT id, version, created_at, description
            FROM workflow_architecture_versions
            ORDER BY version DESC
            LIMIT 50
        ''')
        
        versions = []
        for row in c.fetchall():
            versions.append({
                'id': row['id'],
                'version': row['version'],
                'created_at': row['created_at'],
                'description': row['description']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'versions': versions
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@workflow_arch_bp.route('/api/workflow-architecture/versions/<int:version_id>', methods=['GET'])
def get_workflow_version(version_id):
    """获取特定版本的架构图数据"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            SELECT nodes_json, connections_json, version, created_at, description
            FROM workflow_architecture_versions
            WHERE id=?
        ''', (version_id,))
        
        row = c.fetchone()
        
        if not row:
            return jsonify({'success': False, 'error': '版本不存在'}), 404
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'nodes': json.loads(row[0]),
                'connections': json.loads(row[1]),
                'version': row[2],
                'created_at': row[3],
                'description': row[4]
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@workflow_arch_bp.route('/api/workflow-architecture/versions/<int:version_id>/restore', methods=['POST'])
def restore_workflow_version(version_id):
    """恢复到指定版本"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 获取版本数据
        c.execute('''
            SELECT nodes_json, connections_json, version
            FROM workflow_architecture_versions
            WHERE id=?
        ''', (version_id,))
        
        row = c.fetchone()
        
        if not row:
            return jsonify({'success': False, 'error': '版本不存在'}), 404
        
        nodes = json.loads(row[0])
        connections = json.loads(row[1])
        old_version = row[2]
        
        # 恢复节点数据
        for node in nodes:
            c.execute('''
                UPDATE workflow_architecture 
                SET name=?, type=?, x=?, y=?, color=?, file_path=?, description=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (
                node.get('name'),
                node.get('type', 'node'),
                node.get('x', 0),
                node.get('y', 0),
                node.get('color'),
                node.get('file_path'),
                node.get('description'),
                node.get('id')
            ))
        
        # 恢复连接数据
        c.execute('DELETE FROM workflow_connections')
        for conn_item in connections:
            c.execute('''
                INSERT INTO workflow_connections (from_node, to_node)
                VALUES (?, ?)
            ''', (conn_item.get('from_node'), conn_item.get('to_node')))
        
        conn.commit()
        conn.close()
        
        # 保存为新版本
        new_version = save_version(nodes, connections, f"从版本 {old_version} 恢复")
        
        return jsonify({
            'success': True,
            'message': f'已恢复到版本 {old_version}',
            'new_version': new_version
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@workflow_arch_bp.route('/api/workflow-architecture/node', methods=['POST'])
def create_workflow_node():
    """创建新节点"""
    try:
        data = request.get_json()
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO workflow_architecture (name, type, x, y, color, file_path, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('name', '新节点'),
            data.get('type', 'node'),
            data.get('x', 0),
            data.get('y', 0),
            data.get('color', '#e3f2fd'),
            data.get('file_path', ''),
            data.get('description', '')
        ))
        
        node_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '节点已创建',
            'node_id': node_id
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@workflow_arch_bp.route('/api/workflow-architecture/node/<int:node_id>', methods=['DELETE'])
def delete_workflow_node(node_id):
    """删除节点"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 删除相关连接
        c.execute('DELETE FROM workflow_connections WHERE from_node=? OR to_node=?', (node_id, node_id))
        
        # 删除节点
        c.execute('DELETE FROM workflow_architecture WHERE id=?', (node_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '节点已删除'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@workflow_arch_bp.route('/api/workflow-architecture/connection', methods=['POST'])
def create_workflow_connection():
    """创建连接"""
    try:
        data = request.get_json()
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO workflow_connections (from_node, to_node)
            VALUES (?, ?)
        ''', (data.get('from_node'), data.get('to_node')))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '连接已创建'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@workflow_arch_bp.route('/api/workflow-architecture/connection/<int:conn_id>', methods=['DELETE'])
def delete_workflow_connection(conn_id):
    """删除连接"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('DELETE FROM workflow_connections WHERE id=?', (conn_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '连接已删除'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@workflow_arch_bp.route('/api/workflow-architecture/file/<path:filename>', methods=['GET'])
def get_file_content(filename):
    """获取 MD 文件内容"""
    try:
        # 安全限制：只允许访问特定的 MD 文件
        allowed_files = [
            'SOUL.md', 'USER.md', 'AGENTS.md', 'standards.md',
            'MEMORY.md', 'HEARTBEAT.md', 'CHECKLIST.md', 'TOOLS.md',
            'IDENTITY.md', 'WORKFLOW.md'
        ]
        
        if filename not in allowed_files:
            return jsonify({'success': False, 'error': '不允许访问的文件'}), 403
        
        filepath = os.path.join(WORKSPACE_PATH, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': '文件不存在'}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取元信息
        lines = content.split('\n')
        title = lines[0].replace('#', '').strip() if lines else filename
        description = ''
        
        for line in lines[:10]:
            line = line.strip()
            if line and not line.startswith('#'):
                description = line[:200]
                break
        
        return jsonify({
            'success': True,
            'data': {
                'filename': filename,
                'content': content,
                'title': title,
                'description': description,
                'size': len(content),
                'updated_at': datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@workflow_arch_bp.route('/api/workflow-architecture/file/<path:filename>', methods=['PUT'])
def update_file_content(filename):
    """更新 MD 文件内容"""
    try:
        # 安全限制：只允许访问特定的 MD 文件
        allowed_files = [
            'SOUL.md', 'USER.md', 'AGENTS.md', 'standards.md',
            'MEMORY.md', 'HEARTBEAT.md', 'CHECKLIST.md', 'TOOLS.md',
            'IDENTITY.md', 'WORKFLOW.md'
        ]
        
        if filename not in allowed_files:
            return jsonify({'success': False, 'error': '不允许访问的文件'}), 403
        
        data = request.get_json()
        content = data.get('content', '')
        
        filepath = os.path.join(WORKSPACE_PATH, filename)
        
        # 备份原文件
        if os.path.exists(filepath):
            backup_path = filepath + '.backup_' + datetime.now().strftime('%Y%m%d_%H%M%S')
            with open(filepath, 'r', encoding='utf-8') as f:
                original_content = f.read()
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            print(f"💾 已备份 {filename} -> {backup_path}")
        
        # 写入新内容
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 已更新文件：{filename}")
        
        # 同步更新架构图节点
        conn = get_db()
        c = conn.cursor()
        
        # 提取描述
        lines = content.split('\n')
        description = ''
        for line in lines[:10]:
            line = line.strip()
            if line and not line.startswith('#'):
                description = line[:200]
                break
        
        c.execute('''
            UPDATE workflow_architecture 
            SET description=?, updated_at=CURRENT_TIMESTAMP
            WHERE file_path=?
        ''', (description, filename))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'{filename} 已更新',
            'backup': backup_path if os.path.exists(filepath + '.backup_') else None
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

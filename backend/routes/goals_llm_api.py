"""Routes: goals_llm_api - 目标 + LLM配置 + Token用量"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db, row_to_dict
import os
from database_config import table_exists
import json
from datetime import datetime

bp = Blueprint("routes_goals_llm_api", __name__)
logger = __import__("logging").getLogger(__name__)

@bp.route('/api/metrics/history', methods=['GET'])
def get_metrics_history():
    """获取系统资源历史数据（用于趋势图）"""
    try:
        import datetime
        time_range = request.args.get('range', '24h')
        with get_db() as conn:
            c = conn.cursor()

            # 根据时间范围确定查询条件 (MySQL语法)
            time_condition = {
                '1h': "DATE_SUB(NOW(), INTERVAL 1 HOUR)",
                '6h': "DATE_SUB(NOW(), INTERVAL 6 HOUR)",
                '24h': "DATE_SUB(NOW(), INTERVAL 24 HOUR)",
                '48h': "DATE_SUB(NOW(), INTERVAL 48 HOUR)",
                '7d': "DATE_SUB(NOW(), INTERVAL 7 DAY)",
                '30d': "DATE_SUB(NOW(), INTERVAL 30 DAY)"
            }.get(time_range, "DATE_SUB(NOW(), INTERVAL 24 HOUR)")

            # 查询系统指标（修复：使用正确表 system_metrics，修复MySQL时间语法）
            # MySQL中timestamp可以直接和datetime字符串比较
            c.execute(f"""
                SELECT 
                    id,
                    cpu_percent as cpu,
                    memory_percent as memory,
                    memory_used_gb,
                    memory_total_gb,
                    disk_percent as disk,
                    running_projects as processes,
                    timestamp
                FROM system_metrics
                WHERE timestamp >= {time_condition}
                ORDER BY timestamp ASC
            """)

            # Fetch main query results first
            rows = c.fetchall()

            # Get latest disk details from monitoring_system_metrics
            disk_details = None
            try:
                c.execute('SELECT disk_percent, disk_used_gb, disk_total_gb FROM monitoring_system_metrics ORDER BY id DESC LIMIT 1')
                disk_row = c.fetchone()
                if disk_row:
                    if isinstance(disk_row, dict):
                        disk_details = (disk_row['disk_percent'], disk_row['disk_used_gb'], disk_row['disk_total_gb'])
                    else:
                        disk_details = (disk_row[0], disk_row[1], disk_row[2])
            except Exception:
                pass
            
            metrics = []
            for row in rows:
                # 将 Unix 时间戳转换为可读格式
                # get_db_connection uses pymysql with DictCursor → row is dict
                if isinstance(row, dict):
                    id_val = row['id']
                    cpu_val = row['cpu']
                    mem_val = row['memory']
                    disk_val = row['disk']
                    ts = row['timestamp']
                    processes_val = row.get('processes', None)
                else:
                    # 回退到 tuple 索引
                    id_val = row[0]
                    cpu_val = row['count'] if len(row) > 1 else None
                    mem_val = row[2] if len(row) > 2 else None
                    mem_used_t = row[3] if len(row) > 3 else None
                    mem_total_t = row[4] if len(row) > 4 else None
                    disk_val = row[5] if len(row) > 5 else None
                    processes_val = row[6] if len(row) > 6 else None
                    ts = row[7] if len(row) > 7 else row[5]
                try:
                    # 如果是 Unix 时间戳（数字）
                    if isinstance(ts, (int, float)):
                        dt = datetime.datetime.fromtimestamp(ts)
                    else:
                        # 如果已经是 datetime 对象或字符串
                        if hasattr(ts, 'strftime'):
                            dt = ts
                        else:
                            dt = datetime.datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
                except:
                    dt = datetime.datetime.now()
                # Also get the full detail from monitoring_system_metrics
                mem_used = row.get('memory_used_gb', None) if isinstance(row, dict) else None
                mem_total = row.get('memory_total_gb', None) if isinstance(row, dict) else None

                metrics.append({
                    "id": id_val,
                    "cpu": cpu_val,
                    "memory": mem_val,
                    "memory_used_gb": mem_used,
                    "memory_total_gb": mem_total,
                    "disk_percent": disk_details[0] if disk_details else None,
                    "disk_used_gb": disk_details[1] if disk_details else None,
                    "disk_total_gb": disk_details[2] if disk_details else None,
                    "disk": disk_val,
                    "processes": processes_val,
                    "timestamp": dt.isoformat()
                })

            return jsonify({
                "success": True,
                "metrics": metrics,
                "count": len(metrics)
            })
    except Exception as e:
        logger.error(f"获取系统监控数据失败: {e}")
        return jsonify({"success": False, "error": str(e)})
@bp.route('/api/goals/', methods=['GET'])
@bp.route('/api/goals', methods=['GET'])
def get_goals():
    """获取项目目标列表"""
    try:
        category = request.args.get('category', '')
        conn = get_db()
        c = conn.cursor()
    
        # 检查是否存在goals表
        if not table_exists("goals"):
            # 如果不存在，创建表
            c.execute('''
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT DEFAULT 'product',
                    progress INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'todo',
                    deadline DATE,
                    project_count INTEGER DEFAULT 0,
                    task_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS key_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal_id INTEGER,
                    description TEXT NOT NULL,
                    target_value REAL DEFAULT 100,
                    current_value REAL DEFAULT 0,
                    unit TEXT DEFAULT '%',
                    status TEXT DEFAULT 'todo',
                    FOREIGN KEY (goal_id) REFERENCES goals (id)
                )
            ''')
            conn.commit()
    
        # 查询目标
        query = 'SELECT * FROM goals WHERE 1=1'
        params = []
    
        if category:
            query += ' AND category = %s'
            params.append(category)
    
        query += ' ORDER BY progress DESC, created_at DESC'
    
        c.execute(query, tuple(params))
        goals = [row_to_dict(row, c) for row in c.fetchall()]
    
        # 动态计算每个目标下的项目数
        for goal in goals:
            try:
                c.execute('SELECT COUNT(*) as cnt FROM projects WHERE goal_id = %s AND status != "deleted"', (goal['id'],))
                row = c.fetchone()
                goal['project_count'] = int(row['cnt']) if row else 0
            except:
                goal['project_count'] = 0
        
        # 为每个目标加载关键结果
        for goal in goals:
            try:
                c.execute('''
                    SELECT id, description, target_value, current_value, unit, status
                    FROM key_results
                    WHERE goal_id = %s
                ''', (goal['id'],))
                goal['key_results'] = [row_to_dict(row, c) for row in c.fetchall()]
            except:
                goal['key_results'] = []
    
        conn.close()
        return jsonify({'success': True, 'goals': goals})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/goals', methods=['POST'])
def create_goal():
    """创建项目目标"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
    
        c.execute('''
            INSERT INTO goals (title, description, category, deadline, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
        ''', (
            data.get('title'),
            data.get('description'),
            data.get('category', 'product'),
            data.get('deadline')
        ))
    
        goal_id = c.lastrowid
    
        # 添加关键结果
        if data.get('key_results'):
            for kr in data['key_results']:
                c.execute('''
                    INSERT INTO key_results (goal_id, description, target_value, unit)
                    VALUES (%s, %s, %s, %s)
                ''', (goal_id, kr.get('description'), kr.get('target_value', 100), kr.get('unit', '%')))
    
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'goal_id': goal_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/llm/configs', methods=['GET'])
def get_llm_configs():
    """获取所有LLM配置（包含费用信息）"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, provider, name, model_name, is_active, is_default, temperature,
                   max_tokens, context_window, model_type, supports_vision, supports_reasoning,
                   description, input_cost, output_cost, tokens_used, actual_tokens_used,
                   last_used_at
            FROM llm_configs
            ORDER BY is_active DESC, is_default DESC, id
        ''')
        configs = []
        for row in rows:
            configs.append({
                'id': row['id'],
                'provider': row['provider'],
                'name': row['name'],
                'model_name': row['model_name'],
                'is_active': row['is_active'],
                'is_default': row['is_default'],
                'temperature': row['temperature'],
                'max_tokens': row['max_tokens'],
                'context_window': row['context_window'],
                'model_type': row['model_type'],
                'supports_vision': row['supports_vision'],
                'supports_reasoning': row['supports_reasoning'],
                'description': row['description'],
                'input_cost': row['input_cost'],
                'output_cost': row['output_cost'],
                'tokens_used': row['tokens_used'] or 0,
                'actual_tokens_used': row['actual_tokens_used'] or 0,
                'last_used_at': row['last_used_at'].isoformat() if row['last_used_at'] else None
            })
        conn.close()
        return jsonify({'success': True, 'configs': configs})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/llm/configs', methods=['POST'])
def add_llm_config():
    """添加LLM配置"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO llm_configs (name, provider, model, api_key, base_url, max_tokens, temperature, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
        ''', (data.get('name'), data.get('provider'), data.get('model'),
              data.get('api_key'), data.get('base_url'), 
              data.get('max_tokens', 4096), data.get('temperature', 0.7)))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '配置添加成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/llm/configs/<int:config_id>/activate', methods=['PUT'])
def activate_llm_config(config_id):
    """激活LLM配置"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('UPDATE llm_configs SET is_active = 0')
        c.execute('UPDATE llm_configs SET is_active = 1 WHERE id = %s', (config_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '配置已激活'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/llm/configs/<int:config_id>', methods=['DELETE'])
def delete_llm_config(config_id):
    """删除LLM配置"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM llm_configs WHERE id = %s', (config_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '配置已删除'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/llm/stats', methods=['GET'])
def get_llm_stats():
    """获取LLM使用统计（包含费用）"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        # 基础统计
        c.execute('SELECT COUNT(*) FROM llm_configs')
        total = list(c.fetchone().values())[0]
        c.execute('SELECT COUNT(*) FROM llm_configs WHERE is_active = 1')
        active = list(c.fetchone().values())[0]
    
        # Tokens统计
        c.execute('SELECT SUM(tokens_used) FROM llm_configs')
        tokens_used = list(c.fetchone().values())[0] or 0
    
        # 费用统计 (统一从 token_usage 表获取)
        c.execute('SELECT SUM(cost_usd) FROM token_usage')
        total_cost = list(c.fetchone().values())[0] or 0
    
        # 今日费用 (token_usage表使用timestamp字段和cost_usd)
        c.execute("SELECT SUM(cost_usd) FROM token_usage WHERE date(timestamp) = date('now')")
        today_cost = list(c.fetchone().values())[0] or 0
    
        # 本月费用
        c.execute("SELECT SUM(cost_usd) FROM token_usage WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')")
        month_cost = list(c.fetchone().values())[0] or 0
    
        # 按模型统计
        c.execute('''
            SELECT provider, model_name, SUM(tokens_used) as tokens, SUM(input_cost + output_cost) as cost
            FROM llm_configs
            GROUP BY provider, model_name
        ''')
        model_stats = [{'provider': r[0], 'model': r[1], 'tokens': r[2] or 0, 'cost': r[3] or 0} for r in c.fetchall()]
    
        conn.close()
        return jsonify({
            'success': True, 
            'stats': {
                'total': total, 
                'active': active, 
                'tokens_used': tokens_used,
                'total_cost': round(total_cost, 4),
                'today_cost': round(today_cost, 4),
                'month_cost': round(month_cost, 4),
                'model_stats': model_stats
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/llm/token-usage', methods=['GET'])
def get_token_usage():
    """获取Token使用明细"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        limit = request.args.get('limit', 100, type=int)
    
        c.execute('''
            SELECT id, provider, model, prompt_tokens, completion_tokens, 
                   total_tokens, cost_usd, timestamp
            FROM token_usage
            ORDER BY timestamp DESC
            LIMIT %s
        ''', (limit,))
    
        usage = []
        for row in rows:
            usage.append({
                'id': row[0],
                'provider': row['count'],
                'model': row[2],
                'input_tokens': row[3],
                'output_tokens': row[4],
                'total_tokens': row[5],
                'cost': row[6],
                'created_at': row[7]
            })
    
        conn.close()
        return jsonify({'success': True, 'usage': usage, 'count': len(usage)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/llm/token-usage/daily', methods=['GET'])
def get_daily_token_usage():
    """获取每日Token使用统计"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        days = request.args.get('days', 30, type=int)
    
        c.execute('''
            SELECT 
                date(timestamp) as date,
                SUM(total_tokens) as tokens,
                SUM(cost_usd) as cost,
                COUNT(*) as requests
            FROM token_usage
            WHERE timestamp >= date('now', '-{} days')
            GROUP BY date(timestamp)
            ORDER BY date DESC
        '''.format(days))
    
        daily = []
        for row in rows:
            daily.append({
                'date': row[0],
                'tokens': row['count'] or 0,
                'cost': round(row[2] or 0, 4),
                'requests': row[3]
            })
    
        conn.close()
        return jsonify({'success': True, 'daily': daily})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


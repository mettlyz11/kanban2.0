#!/usr/bin/env python3
"""LLM Usage API - Flask Blueprint"""
from flask import Blueprint, jsonify
from datetime import datetime
from .helpers import get_db

llm_usage_bp = Blueprint('llm_usage', __name__, url_prefix='/api/llm')

def _q(sql):
    """安全查询"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        out = []
        for r in rows:
            d = {}
            for k, v in r.items():
                if hasattr(v, 'isoformat'):
                    d[k] = v.isoformat()
                elif v.__class__.__name__ == 'Decimal':
                    d[k] = float(v)
                else:
                    d[k] = v
            out.append(d)
        return out
    except Exception as e:
        print('[LLM API] Query failed:', e)
        return []

@llm_usage_bp.route('/usage', methods=['GET'])
def get_llm_usage():
    """返回LLM使用量综合数据"""
    try:
        # 1. Token使用量 -> llm_call_log（有total_tokens字段）
        token_stats = _q('''
            SELECT provider, model,
                   COALESCE(SUM(prompt_tokens),0) AS total_prompt_tokens,
                   COALESCE(SUM(completion_tokens),0) AS total_completion_tokens,
                   COALESCE(SUM(total_tokens),0) AS total_tokens,
                   COUNT(*) AS total_calls,
                   COALESCE(SUM(cost_usd),0) AS total_cost
            FROM llm_call_log
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY provider, model
            ORDER BY total_tokens DESC
            LIMIT 20
        ''')

        # 2. 每日趋势 -> llm_call_log
        daily_stats = _q('''
            SELECT DATE(created_at) AS date,
                   COUNT(*) AS total_calls,
                   COALESCE(SUM(total_tokens),0) AS total_tokens,
                   COALESCE(SUM(cost_usd),0) AS total_cost
            FROM llm_call_log
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(created_at)
            ORDER BY date
        ''')

        # 3. 总览（近30天）
        overview = _q('''
            SELECT COUNT(*) AS total_calls,
                   COALESCE(SUM(total_tokens),0) AS total_tokens,
                   COALESCE(SUM(cost_usd),0) AS total_cost,
                   COUNT(DISTINCT provider) AS unique_providers,
                   COUNT(DISTINCT model) AS unique_models
            FROM llm_call_log
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        ''')

        # 4. 调用统计 -> llm_call_logs（有elapsed_ms/scenario）
        call_stats = _q('''
            SELECT provider, model, scenario,
                   COUNT(*) AS total_calls,
                   COALESCE(SUM(prompt_length),0) AS total_prompt_length,
                   COALESCE(AVG(elapsed_ms),0) AS avg_response_time
            FROM llm_call_logs
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY provider, model, scenario
            ORDER BY total_calls DESC
            LIMIT 20
        ''')

        # 5. Actor LLM调用统计
        actor_stats = _q('''
            SELECT COALESCE(source,'unknown') AS source,
                   COALESCE(method,'unknown') AS method,
                   COALESCE(SUM(llm_calls),0) AS total_calls
            FROM actor_llm_invocations
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY source, method
            ORDER BY total_calls DESC
            LIMIT 20
        ''')

        return jsonify({
            'success': True,
            'data': {
                'token_stats': token_stats,
                'call_stats': call_stats,
                'daily_stats': daily_stats,
                'overview': overview[0] if overview else {},
                'actor_stats': actor_stats,
            },
            'timestamp': datetime.now().isoformat(),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@llm_usage_bp.route('/record', methods=['POST'])
def record_llm_usage():
    from flask import request
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({'success': False, 'error': 'No data'}), 400
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO token_usage (provider, model, prompt_tokens, completion_tokens, 
                                     total_tokens, cost_usd)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            data.get('provider', ''),
            data.get('model', ''),
            int(data.get('prompt_tokens', 0)),
            int(data.get('completion_tokens', 0)),
            int(data.get('total_tokens', 0)),
            float(data.get('cost_usd', 0)),
        ))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@llm_usage_bp.route('/token-summary', methods=['GET'])
def get_token_summary():
    """Returns concise token summary for frontend"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 总 Tokens 和总费用
        c.execute('''
            SELECT COALESCE(SUM(total_tokens),0) AS total_tokens,
                   COALESCE(SUM(cost_usd),0) AS total_cost
            FROM token_usage
        ''')
        totals = c.fetchone()
        
        # 今日费用
        c.execute('''
            SELECT COALESCE(SUM(cost_usd),0) AS today_cost
            FROM token_usage
            WHERE DATE(timestamp) = CURDATE()
        ''')
        today = c.fetchone()
        
        # 本月费用
        c.execute('''
            SELECT COALESCE(SUM(cost_usd),0) AS month_cost
            FROM token_usage
            WHERE YEAR(timestamp) = YEAR(NOW()) AND MONTH(timestamp) = MONTH(NOW())
        ''')
        month = c.fetchone()
        
        # 按Provider统计
        c.execute('''
            SELECT provider,
                   COUNT(*) AS calls,
                   COALESCE(SUM(prompt_tokens),0) AS prompt_tokens,
                   COALESCE(SUM(completion_tokens),0) AS completion_tokens,
                   COALESCE(SUM(total_tokens),0) AS tokens,
                   COALESCE(SUM(cost_usd),0) AS cost
            FROM token_usage
            GROUP BY provider
            ORDER BY tokens DESC
            LIMIT 50
        ''')
        provider_rows = c.fetchall()

        # 按模型统计
        c.execute('''
            SELECT provider, model,
                   COALESCE(SUM(prompt_tokens),0) AS prompt_tokens,
                   COALESCE(SUM(completion_tokens),0) AS completion_tokens,
                   COALESCE(SUM(total_tokens),0) AS tokens,
                   COALESCE(SUM(cost_usd),0) AS cost
            FROM token_usage
            GROUP BY provider, model
            ORDER BY tokens DESC
            LIMIT 50
        ''')
        rows = c.fetchall()
        conn.close()
        
        by_provider = []
        for r in provider_rows:
            d = {}
            for k, v in r.items():
                if hasattr(v, 'isoformat'):
                    d[k] = v.isoformat()
                elif v.__class__.__name__ == 'Decimal':
                    d[k] = float(v)
                else:
                    d[k] = v
            by_provider.append(d)

        by_model = []
        for r in rows:
            d = {}
            for k, v in r.items():
                if hasattr(v, 'isoformat'):
                    d[k] = v.isoformat()
                elif v.__class__.__name__ == 'Decimal':
                    d[k] = float(v)
                else:
                    d[k] = v
            by_model.append(d)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_tokens': float(totals['total_tokens']),
                'total_cost': float(totals['total_cost']),
                'today_cost': float(today['today_cost']),
                'month_cost': float(month['month_cost']),
                'by_provider': by_provider,
                'by_model': by_model,
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

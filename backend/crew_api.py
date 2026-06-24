#!/usr/bin/env python3
import os, json, subprocess, time
from flask import Flask, jsonify, request, Response, stream_with_context
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_HOST = os.getenv('DB_HOST', 'rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com')
DB_USER = os.getenv('DB_USER', 'kanban')
DB_PASSWORD = os.getenv('DB_PASSWORD') or os.getenv('MYSQL_PASSWORD')
if not DB_PASSWORD:
    raise RuntimeError('DB_PASSWORD/MYSQL_PASSWORD environment variable is required')
DB_NAME = os.getenv('DB_NAME', 'kanban')
DB_PORT = int(os.getenv('DB_PORT', '3306'))

import pymysql
def _db():
    return pymysql.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

def _query(sql, args=None):
    conn = _db(); cur = conn.cursor(); cur.execute(sql, args or ()); rows = cur.fetchall(); cur.close(); conn.close(); return rows

def _execute(sql, args=None):
    conn = _db(); cur = conn.cursor(); n = cur.execute(sql, args or ()); conn.commit(); cur.close(); conn.close(); return n

@app.route('/api/crews/status', methods=['GET'])
def crew_status():
    crews = [
        {'name':'push_actor_filter','label':'\u5931\u8d25\u4efb\u52a1\u4fee\u590d','cron':'*/15 * * * *','status':'active'},
        {'name':'contact_reminder','label':'\u8054\u7cfb\u4eba\u63d0\u9192','cron':'0 9 * * *','status':'active'},
        {'name':'health_scan','label':'\u7cfb\u7edf\u5065\u5eb7\u626b\u63cf','cron':'0 */6 * * *','status':'active'},
        {'name':'llm_auditor','label':'LLM\u4ee3\u7801\u5ba1\u8ba1','cron':'0 3 * * *','status':'active'},
    ]
    esc = _query('SELECT id, crew_name, task_id, reason, status, created_at, resolved_at FROM crew_escalations ORDER BY created_at DESC LIMIT 30')
    runs = _query("SELECT id, title, status, result_summary, created_at, updated_at FROM tasks WHERE task_type='crew' OR title LIKE CONCAT('crew', ':%%') ORDER BY created_at DESC LIMIT 20")
    return jsonify({'ok': True, 'crews': crews, 'escalations': esc, 'recent_runs': runs})

@app.route('/api/crews/trigger', methods=['POST'])
def crew_trigger():
    data = request.get_json() or {}
    crew = (data.get('crew') or '').strip()
    allowed = ['push_actor_filter','contact_reminder','health_scan','llm_auditor']
    if crew not in allowed:
        return jsonify({'ok': False, 'error': 'unknown crew'}), 400
    log = '/tmp/crew_%s_%d.log' % (crew, int(time.time()))
    try:
        proc = subprocess.Popen(
            ['/opt/sds1/venv/bin/python3', '/opt/sds1/crews/crew_dispatcher.py', crew],
            stdout=open(log, 'w'), stderr=subprocess.STDOUT,
            cwd='/opt/sds1', env={**os.environ, 'DB_HOST': DB_HOST, 'DB_USER': DB_USER, 'DB_PASSWORD': DB_PASSWORD, 'DB_NAME': DB_NAME}
        )
        return jsonify({'ok': True, 'crew': crew, 'pid': proc.pid, 'log': log})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/crews/resolve', methods=['POST'])
def crew_resolve():
    data = request.get_json() or {}
    esc_id = data.get('escalation_id')
    action = data.get('action', 'resolved')
    if not esc_id:
        return jsonify({'ok': False, 'error': 'missing escalation_id'}), 400
    n = _execute('UPDATE crew_escalations SET status=%s, resolved_at=NOW() WHERE id=%s', (action, esc_id))
    return jsonify({'ok': True, 'updated': n})

@app.route('/api/crews/run/<run_id>', methods=['GET'])
def crew_run_detail(run_id):
    try:
        run = _query('SELECT id, title, status, result_summary, details, created_at, updated_at FROM tasks WHERE id=%s LIMIT 1', (run_id,))
        if run:
            return jsonify({'ok': True, 'run': run[0]})
        return jsonify({'ok': False, 'error': 'not found'}), 404
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/crews/log/<log_file>', methods=['GET'])
def crew_log_stream(log_file):
    # SSE endpoint - stream log file content
    from flask import Response, stream_with_context
    log_path = '/tmp/' + log_file
    import os, time, json
    if not os.path.exists(log_path):
        return jsonify({'ok': False, 'error': 'log not found'}), 404

    def generate():
        with open(log_path, 'r') as f:
            existing = f.read()
            if existing:
                yield 'data: ' + json.dumps({'type':'log','content':existing}) + '\n\n'
            while True:
                new_content = f.read()
                if new_content:
                    yield 'data: ' + json.dumps({'type':'log','content':new_content}) + '\n\n'
                time.sleep(0.5)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'}
    )

@app.route('/api/crews/resolve-batch', methods=['POST'])
def crew_resolve_batch():
    data = request.get_json() or {}
    ids = data.get('ids', [])
    action = data.get('action', 'resolved')
    if not ids or not isinstance(ids, list):
        return jsonify({'ok': False, 'error': 'missing ids array'}), 400
    try:
        placeholders = ','.join(['%s'] * len(ids))
        sql = f"UPDATE crew_escalations SET status=%s, resolved_at=NOW() WHERE id IN ({placeholders})"
        params = [action] + ids
        n = _execute(sql, tuple(params))
        return jsonify({'ok': True, 'updated': n})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/crews/stats', methods=['GET'])
def crew_stats():
    try:
        # Get stats for last 7 days
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        # Query daily stats
        sql = """
            SELECT
                DATE(created_at) as date,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as success,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM tasks
            WHERE (task_type = 'crew' OR title LIKE 'crew:%%')
            AND created_at >= %s
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            LIMIT 7
        """
        rows = _query(sql, (start_date.strftime('%Y-%m-%d'),))

        # Fill missing dates
        stats = []
        for i in range(7):
            date_str = (end_date - timedelta(days=i)).strftime('%Y-%m-%d')
            date_row = next((r for r in rows if str(r['date']) == date_str), None)
            if date_row:
                stats.append({
                    'date': date_str,
                    'total': int(date_row['total'] or 0),
                    'success': int(date_row['success'] or 0),
                    'failed': int(date_row['failed'] or 0)
                })
            else:
                stats.append({'date': date_str, 'total': 0, 'success': 0, 'failed': 0})

        # Overall stats
        overall_sql = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as success,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM tasks
            WHERE (task_type = 'crew' OR title LIKE 'crew:%%')
        """
        overall = _query(overall_sql)[0]

        return jsonify({
            'ok': True,
            'daily': list(reversed(stats)),
            'overall': {
                'total': int(overall['total'] or 0),
                'success': int(overall['success'] or 0),
                'failed': int(overall['failed'] or 0),
                'success_rate': round((overall['success'] or 0) / (overall['total'] or 1) * 100, 1)
            }
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/crews/health', methods=['GET'])
def crew_health():
    return jsonify({'ok': True, 'service': 'crew-api'})


# Cron config API
import os as cron_os, re as cron_re
CRON_CONFIG_FILE = '/opt/kanban-react/backend/data/cron_config.json'

def _load_cron_config():
    default = {
        'push_actor_filter': '*/15 * * * *',
        'contact_reminder': '0 9 * * *',
        'health_scan': '0 */6 * * *',
        'llm_auditor': '0 3 * * *'
    }
    if cron_os.path.exists(CRON_CONFIG_FILE):
        try:
            with open(CRON_CONFIG_FILE, 'r') as f:
                saved = json.load(f)
                default.update(saved)
        except:
            pass
    return default

def _save_cron_config(config):
    cron_os.makedirs(cron_os.path.dirname(CRON_CONFIG_FILE), exist_ok=True)
    with open(CRON_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

@app.route('/api/crews/cron-config', methods=['GET'])
def get_cron_config():
    try:
        config = _load_cron_config()
        return jsonify({'ok': True, 'config': config})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/crews/cron-config', methods=['POST'])
def update_cron_config():
    try:
        data = request.get_json() or {}
        crew = data.get('crew')
        cron = data.get('cron')
        if not crew or not cron:
            return jsonify({'ok': False, 'error': 'crew and cron required'}), 400
        if not cron_re.match(r'^[\d*/,-]+ [\d*/,-]+ [\d*/,-]+ [\d*/,-]+ [\d*/,-]+$', cron):
            return jsonify({'ok': False, 'error': 'invalid cron expression'}), 400
        config = _load_cron_config()
        config[crew] = cron
        _save_cron_config(config)
        return jsonify({'ok': True, 'config': config})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8090, debug=False, threaded=True)

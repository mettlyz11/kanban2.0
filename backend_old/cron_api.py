# Cron API 简化版 - 添加到app.py末尾

# ============================================
# Cron 任务 API
# ============================================

@app.route('/api/cron/tasks', methods=['GET'])
def get_cron_tasks():
    """获取所有Cron任务"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, name, description, schedule, command, status, 
                   last_run, next_run, fail_count, created_at
            FROM cron_tasks 
            ORDER BY created_at DESC
        ''')
        tasks = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'tasks': tasks})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cron/stats', methods=['GET'])
def get_cron_stats():
    """获取Cron统计"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM cron_tasks')
        total = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM cron_tasks WHERE status = 'active'")
        active = c.fetchone()[0]
        
        c.execute('SELECT SUM(fail_count) FROM cron_tasks')
        failed = c.fetchone()[0] or 0
        
        # 今日执行次数
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute("SELECT COUNT(*) FROM cron_history WHERE date(created_at) = ?", (today,))
        today_count = c.fetchone()[0] or 0
        
        conn.close()
        
        return jsonify({
            'success': True, 
            'stats': {
                'total': total,
                'active': active,
                'failed': failed,
                'today': today_count
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cron/add', methods=['POST'])
def add_cron_task():
    """添加Cron任务"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO cron_tasks (name, description, schedule, command, status, created_at)
            VALUES (?, ?, ?, ?, 'active', datetime('now'))
        ''', (data.get('name'), data.get('description'), data.get('schedule'), data.get('command')))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cron/delete/<int:task_id>', methods=['POST'])
def delete_cron_task(task_id):
    """删除Cron任务"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM cron_tasks WHERE id = ?', (task_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 股票 API
# ============================================

@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    """获取所有股票"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, code, name, type, shares, cost_price, current_price,
                   (shares * current_price) as market_value,
                   ((current_price - cost_price) / cost_price * 100) as return_rate
            FROM stocks
            ORDER BY type, code
        ''')
        stocks = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'stocks': stocks})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stocks/stats', methods=['GET'])
def get_stock_stats():
    """获取股票统计"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM stocks')
        count = c.fetchone()[0]
        
        c.execute('SELECT SUM(shares * cost_price) FROM stocks')
        total_cost = c.fetchone()[0] or 0
        
        c.execute('SELECT SUM(shares * current_price) FROM stocks')
        total_value = c.fetchone()[0] or 0
        
        total_profit = total_value - total_cost
        total_return = (total_profit / total_cost * 100) if total_cost > 0 else 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_value': total_value,
            'total_cost': total_cost,
            'total_profit': total_profit,
            'total_return': total_return,
            'count': count
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 手动审核 API
# ============================================

@app.route('/api/manual-review/tasks', methods=['GET'])
def get_manual_review_tasks():
    """获取手动审核任务"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, task_type, title, description, source, status, 
                   notes, created_at, completed_at
            FROM manual_review_tasks
            ORDER BY created_at DESC
        ''')
        tasks = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'tasks': tasks})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/manual-review/tasks/<int:task_id>/complete', methods=['POST'])
def complete_manual_review_task(task_id):
    """完成审核任务"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            UPDATE manual_review_tasks 
            SET status = ?, notes = ?, completed_at = datetime('now')
            WHERE id = ?
        ''', ('approved' if data.get('approved') else 'rejected', data.get('notes'), task_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 技能库 API
# ============================================

@app.route('/api/skills', methods=['GET'])
def get_skills():
    """获取所有技能"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, name, description, category, command, icon, version, status
            FROM skills
            ORDER BY category, name
        ''')
        skills = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'skills': skills})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

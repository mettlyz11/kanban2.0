"""Routes: cockpit"""
from flask import Blueprint, jsonify, request
import os
import json
from routes.helpers import get_db
from datetime import datetime

bp = Blueprint('routes_cockpit', __name__)

import re as _re

@bp.route("/api/cockpit/generate-instruction", methods=["GET"])
def generate_cockpit_instruction():
    task_id = request.args.get("task_id", type=int)
    if not task_id:
        return jsonify({"success": False, "error": "No task_id"})
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT title,status,task_summary,execution_log,result_summary,strategic_goal, remaining_issues FROM tasks WHERE id = %s", (task_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return jsonify({"success": True, "instruction": "该任务在数据库中未找到"})

        title = (row["title"] or "").strip()
        status = row["status"] or ""
        goal = row["strategic_goal"] or ""
        summary = (row["task_summary"] or "").strip()
        log = (row["execution_log"] or "").strip()
        issues = (row["remaining_issues"] or "").strip() if "remaining_issues" in row else ""
        result = (row["result_summary"] or "").strip()

        # Clean up: remove timestamps, emoji, separator lines from logs
        def clean_text(t):
            t = _re.sub(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]', '', t)
            t = _re.sub(r'[=]{10,}', '', t)
            t = _re.sub(r'[\U0001F300-\U0001F9FF]', '', t)
            t = _re.sub(r'\n{3,}', '\n\n', t)
            return t.strip()[:300]

        # Extract key action items from execution log
        action_items = []
        for keyword in ["需要", "待办", "请", "后续", "建议", "产出", "已完成"]:
            for match in _re.finditer(rf'[^。]*{keyword}[^。]*。', log[:1000]):
                item = match.group().strip()
                if len(item) > 10 and item not in action_items:
                    action_items.append(item)

        # Build clean instruction
        parts = []

        # 1. What happened
        parts.append(f"### 任务说明\nSDS已执行任务「{title}」。")
        if goal:
            parts.append(f"属于战略目标「{goal}」。当前状态：{status}。")

        # 2. Why user's input is needed
        clean_issues = clean_text(issues) if issues else ''
        need_reason = "因为该任务需要人工判断和决策，SDS无法自动完成。"
        if clean_issues and len(clean_issues) > 10:
            need_reason = f"SDS缺少以下关键信息，需要您补充：\n{clean_issues}\n\n请在下方输入框中补充以上信息，SDS将根据您提供的信息重新执行。"
        elif "pending_review" in status:
            need_reason = "SDS已初步完成任务，但需要您提供具体判断。请在下方输入框中说明您的意见。"
        parts.append(f"\n### 需要您提供\n{need_reason}")

        # 3. What was done (clean, analyzed)
        clean_summary = clean_text(summary)
        if clean_summary and len(clean_summary) > 20:
            parts.append(f"\n### SDS已完成的工作\n{clean_summary}")
        else:
            clean_result = clean_text(result)
            if clean_result:
                parts.append(f"\n### SDS已完成的工作\n{clean_result}")





        txt = "\n".join(parts)
        detail = {"task_id":task_id,"title":title,"status":status,"goal":goal}
        return jsonify({"success": True, "instruction": txt, "task_detail": detail})
    except Exception as e:
        return jsonify({"success": True, "instruction": f"请关注任务 #{task_id}，输入决策指令"})

@bp.route('/api/cockpit/create-alert', methods=['POST'])
def create_cockpit_alert():
    """创建驾驶舱警报（供SDS调用）"""
    data = request.get_json() or {}
    task_id = data.get('task_id')
    alert_level = data.get('alert_level', 'warning')
    alert_type = data.get('alert_type', 'decision_required')
    title = data.get('title', '')
    description = data.get('description', '')
    context = data.get('context', {})
    
    if not task_id or not title:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''INSERT INTO cockpit_alerts (task_id, alert_level, alert_type, title, description, context, status, created_at)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())''',
              (task_id, alert_level, alert_type, title, description, json.dumps(context), 'pending'))
    alert_id = c.lastrowid
    
    # 更新任务的cockpit_alert_id
    c.execute('UPDATE tasks SET cockpit_alert_id = %s WHERE id = %s', (alert_id, task_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'alert_id': alert_id,
        'task_id': task_id,
        'message': '驾驶舱警报已创建'
    })





@bp.route('/api/cockpit/interactions', methods=['GET'])
def get_cockpit_interactions():
    """获取驾驶舱交互历史"""
    task_id = request.args.get('task_id', type=int)
    alert_id = request.args.get('alert_id', type=int)
    limit = int(request.args.get('limit', 50))
    
    conn = get_db()
    c = conn.cursor()
    
    query = '''SELECT id, task_id, alert_id, speaker, message, intent_analysis, action_taken, created_at 
               FROM cockpit_interactions WHERE 1=1'''
    params = []
    
    if task_id:
        query += ' AND task_id = %s'
        params.append(task_id)
    if alert_id:
        query += ' AND alert_id = %s'
        params.append(alert_id)
    
    query += ' ORDER BY created_at DESC LIMIT %s'
    params.append(limit)
    
    c.execute(query, params)
    interactions = []
    for row in c.fetchall():
        interactions.append({
            'id': row['id'],
            'task_id': row['task_id'],
            'alert_id': row['alert_id'],
            'speaker': row['speaker'],
            'message': row['message'],
            'intent_analysis': json.loads(row['intent_analysis']) if row['intent_analysis'] else None,
            'action_taken': row['action_taken'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None
        })
    
    conn.close()
    
    return jsonify({
        'success': True,
        'interactions': interactions,
        'total': len(interactions)
    })

@bp.route('/api/cockpit/resolve', methods=['POST'])
def cockpit_resolve():
    """解决驾驶舱警报"""
    data = request.get_json() or {}
    alert_id = data.get('alert_id')
    resolution = data.get('resolution')
    notes = data.get('notes', '')
    
    if not alert_id or not resolution:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    # 获取警报信息
    c.execute('SELECT task_id, status FROM cockpit_alerts WHERE id = %s', (alert_id,))
    alert = c.fetchone()
    if not alert:
        conn.close()
        return jsonify({'success': False, 'error': '警报不存在'}), 404
    
    # 更新警报状态
    c.execute('''UPDATE cockpit_alerts 
                 SET status = %s, resolved_by = %s, resolved_at = NOW() 
                 WHERE id = %s''',
              ('resolved', 'user', alert_id))
    
    # 根据resolution更新任务状态
    task_id = alert['task_id']
    if resolution == 'approve':
        c.execute('UPDATE tasks SET status = %s, updated_at = NOW() WHERE id = %s', ('completed', task_id))
    elif resolution == 'reject':
        c.execute('UPDATE tasks SET status = %s, updated_at = NOW() WHERE id = %s', ('pending', task_id))
    elif resolution == 'feedback':
        c.execute('UPDATE tasks SET status = %s, review_feedback = %s, updated_at = NOW() WHERE id = %s', 
                  ('review_feedback', notes, task_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '警报已解决',
        'resolution': resolution,
        'task_id': task_id
    })

@bp.route('/api/cockpit/interact', methods=['POST'])
def cockpit_interact():
    """驾驶舱交互 - 自然语言对话"""
    data = request.get_json() or {}
    task_id = data.get('task_id')
    alert_id = data.get('alert_id')
    message = data.get('message', '')
    
    if not task_id or not message:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    # 检查任务是否存在
    c.execute('SELECT id, title, status FROM tasks WHERE id = %s', (task_id,))
    task = c.fetchone()
    if not task:
        conn.close()
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    # 记录用户消息
    c.execute('''INSERT INTO cockpit_interactions (task_id, alert_id, speaker, message, created_at)
                 VALUES (%s, %s, %s, %s, NOW())''',
              (task_id, alert_id, 'user', message))
    
    # TODO: 这里应该调用LLM理解用户意图
    # 简化版：基于关键词判断
    message_lower = message.lower()
    
    if any(kw in message_lower for kw in ['通过', '同意', '可以', 'ok', '好']):
        # 用户同意/通过
        c.execute('UPDATE tasks SET status = %s, updated_at = NOW() WHERE id = %s', ('completed', task_id))
        if alert_id:
            c.execute('UPDATE cockpit_alerts SET status = %s, resolved_at = NOW() WHERE id = %s', ('resolved', alert_id))
        response = '✅ 已确认通过，任务已标记为完成。'
        action_taken = 'approve'
        
    elif any(kw in message_lower for kw in ['驳回', '重做', '重新', '不对']):
        # 用户驳回
        c.execute('UPDATE tasks SET status = %s, updated_at = NOW() WHERE id = %s', ('pending', task_id))
        if alert_id:
            c.execute('UPDATE cockpit_alerts SET status = %s, resolved_at = NOW() WHERE id = %s', ('resolved', alert_id))
        response = '❌ 已驳回，任务将重新执行。'
        action_taken = 'reject'
        
    elif any(kw in message_lower for kw in ['修改', '调整', '补充', '改']):
        # 用户补充信息或要求修改 → 记录反馈并重新排队执行
        c.execute('UPDATE tasks SET status = %s, review_feedback = %s, remaining_issues = NULL, updated_at = NOW() WHERE id = %s', 
                  ('pending', message, task_id))
        if alert_id:
            c.execute('UPDATE cockpit_alerts SET status = %s, resolved_at = NOW() WHERE id = %s', ('resolved', alert_id))
        response = '💬 已记录您的补充信息，SDS将重新执行该任务。'
        action_taken = 'feedback'
        
    else:
        # 默认：信息查询或一般对话
        response = f'🤖 收到您的消息："{message[:50]}..."\n\nSDS已记录，将在后续处理中考虑您的意见。'
        action_taken = 'acknowledge'
    
    # 记录系统回复
    c.execute('''INSERT INTO cockpit_interactions (task_id, alert_id, speaker, message, action_taken, created_at)
                 VALUES (%s, %s, %s, %s, %s, NOW())''',
              (task_id, alert_id, 'sds', response, action_taken))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'response': response,
        'analysis': {
            'intent': action_taken,
            'confidence': 0.85
        },
        'task_id': task_id,
        'alert_id': alert_id
    })

@bp.route('/api/cockpit/alerts', methods=['GET'])
def get_cockpit_alerts():
    """获取驾驶舱警报列表"""
    level = request.args.get('level', '')
    status = request.args.get('status', 'pending')
    limit = int(request.args.get('limit', 50))
    
    conn = get_db()
    c = conn.cursor()
    
    query = '''SELECT id, task_id, alert_level, alert_type, title, description, context, status, created_at 
               FROM cockpit_alerts WHERE 1=1'''
    params = []
    
    if status:
        query += ' AND status = %s'
        params.append(status)
    if level:
        query += ' AND alert_level = %s'
        params.append(level)
    
    query += ' ORDER BY created_at DESC LIMIT %s'
    params.append(limit)
    
    c.execute(query, params)
    alerts = []
    for row in c.fetchall():
        alerts.append({
            'id': row['id'],
            'task_id': row['task_id'],
            'alert_level': row['alert_level'],
            'alert_type': row['alert_type'],
            'title': row['title'],
            'description': row['description'],
            'context': json.loads(row['context']) if row['context'] else None,
            'status': row['status'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None
        })
    
    conn.close()
    
    return jsonify({
        'success': True,
        'alerts': alerts,
        'total': len(alerts)
    })

@bp.route('/api/cockpit/status', methods=['GET'])
def get_cockpit_status():
    """获取驾驶舱状态统计"""
    conn = get_db()
    c = conn.cursor()
    
    # 统计各级别警报
    c.execute('''SELECT alert_level, COUNT(*) as cnt FROM cockpit_alerts WHERE status = 'pending' GROUP BY alert_level''')
    alert_stats = {row['alert_level']: row['cnt'] for row in c.fetchall()}
    
    # 最近5个警报
    c.execute('''SELECT id, task_id, alert_level, alert_type, title, status, created_at 
                 FROM cockpit_alerts ORDER BY created_at DESC LIMIT 5''')
    recent_alerts = []
    for row in c.fetchall():
        recent_alerts.append({
            'id': row['id'],
            'task_id': row['task_id'],
            'alert_level': row['alert_level'],
            'alert_type': row['alert_type'],
            'title': row['title'],
            'status': row['status'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None
        })
    
    # 最近5个交互
    c.execute('''SELECT ci.id, ci.task_id, ci.speaker, ci.message, ci.created_at, ca.title as alert_title
                 FROM cockpit_interactions ci
                 LEFT JOIN cockpit_alerts ca ON ci.alert_id = ca.id
                 ORDER BY ci.created_at DESC LIMIT 5''')
    recent_interactions = []
    for row in c.fetchall():
        recent_interactions.append({
            'id': row['id'],
            'task_id': row['task_id'],
            'speaker': row['speaker'],
            'message': row['message'][:100] + '...' if row['message'] and len(row['message']) > 100 else row['message'],
            'alert_title': row['alert_title'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None
        })
    
    conn.close()
    
    return jsonify({
        'success': True,
        'stats': {
            'critical': alert_stats.get('critical', 0),
            'warning': alert_stats.get('warning', 0),
            'info': alert_stats.get('info', 0),
            'total_pending': sum(alert_stats.values())
        },
        'recent_alerts': recent_alerts,
        'recent_interactions': recent_interactions
    })


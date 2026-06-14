"""Routes: health"""
from flask import Blueprint, jsonify, request
import json
import os
from routes.helpers import get_db, row_to_dict
from datetime import datetime

bp = Blueprint('routes_health', __name__)

@bp.route('/api/health/checkups', methods=['GET'])
def get_health_checkups():
    """获取体检数据列表"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, person_name, checkup_date, hospital, age, height, weight,
                   blood_pressure_sys, blood_pressure_dia, heart_rate, lvef,
                   lung_capacity, vision_right, vision_left, hemoglobin, dc_value,
                   checkup_items, notes, created_at
            FROM health_checkups
            ORDER BY checkup_date DESC
        ''')
        checkups = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'checkups': checkups})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/health/records', methods=['GET'])
def get_health_records():
    """获取日常健康记录"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, record_date, weight, sleep_hours, exercise_minutes,
                   water_intake, mood, notes, created_at
            FROM health_records
            ORDER BY record_date DESC
        ''')
        records = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'records': records})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/health/checkups', methods=['POST'])
def add_health_checkup():
    """添加体检记录"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO health_checkups (checkup_date, hospital, checkup_items, notes)
            VALUES (%s, %s, %s, %s)
        ''', (
            data.get('checkup_date'),
            data.get('hospital'),
            data.get('checkup_items'),
            data.get('notes')
        ))
        conn.commit()
        checkup_id = c.lastrowid
        conn.close()
        return jsonify({'success': True, 'id': checkup_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 公司信息 API
# ============================================



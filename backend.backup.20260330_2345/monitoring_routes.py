#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P049-T041: 监控告警系统 API 路由
与 Flask app 集成 - 纯 MySQL 版本

作者：OpenClaw Subagent
创建时间：2026-03-10
修改时间：2026-03-18 (移除 SQLite，使用 MySQL)
"""

from flask import Blueprint, request, jsonify
from database_config import get_db_connection, execute_query, execute_update
import json
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 创建蓝图
monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api/monitoring')

# ============================================
# 系统监控 API
# ============================================

@monitoring_bp.route('/system-metrics', methods=['GET'])
def get_system_metrics():
    """获取系统指标"""
    try:
        hours = request.args.get('hours', 24, type=int)
        since = time.time() - (hours * 3600)
        
        # 获取最新指标
        sql = """
            SELECT cpu_percent, memory_percent, memory_used_gb, memory_total_gb,
                   disk_percent, disk_used_gb, disk_total_gb, timestamp
            FROM monitoring_system_metrics
            ORDER BY timestamp DESC
            LIMIT 1
        """
        latest_rows = execute_query(sql)
        latest = latest_rows[0] if latest_rows else None
        
        # 获取统计数据
        sql = """
            SELECT 
                AVG(cpu_percent) as avg_cpu,
                MAX(cpu_percent) as max_cpu,
                AVG(memory_percent) as avg_memory,
                MAX(memory_percent) as max_memory,
                AVG(disk_percent) as avg_disk,
                MAX(disk_percent) as max_disk
            FROM monitoring_system_metrics
            WHERE timestamp >= %s
        """
        stats_rows = execute_query(sql, (since,))
        stats = stats_rows[0] if stats_rows else {}
        
        return jsonify({
            "success": True,
            "data": {
                "latest": latest,
                "stats": stats,
                "period_hours": hours
            }
        })
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return jsonify({"success": False, "error": str(e)})

@monitoring_bp.route('/system-metrics/history', methods=['GET'])
def get_system_metrics_history():
    """获取系统指标历史"""
    try:
        hours = request.args.get('hours', 24, type=int)
        since = time.time() - (hours * 3600)
        
        sql = """
            SELECT cpu_percent, memory_percent, disk_percent, timestamp
            FROM monitoring_system_metrics
            WHERE timestamp >= %s
            ORDER BY timestamp ASC
        """
        rows = execute_query(sql, (since,))
        
        return jsonify({
            "success": True,
            "data": {
                "metrics": rows,
                "period_hours": hours
            }
        })
    except Exception as e:
        logger.error(f"Error getting system metrics history: {e}")
        return jsonify({"success": False, "error": str(e)})

@monitoring_bp.route('/api-metrics', methods=['GET'])
def get_api_metrics():
    """获取 API 指标"""
    try:
        hours = request.args.get('hours', 24, type=int)
        since = time.time() - (hours * 3600)
        
        # 获取统计数据
        sql = """
            SELECT 
                COUNT(*) as total_requests,
                AVG(response_time_ms) as avg_response_time,
                MAX(response_time_ms) as max_response_time,
                SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) as error_count
            FROM monitoring_api_metrics
            WHERE timestamp >= %s
        """
        stats_rows = execute_query(sql, (since,))
        stats = stats_rows[0] if stats_rows else {}
        
        # 获取慢 API
        sql = """
            SELECT endpoint, method, AVG(response_time_ms) as avg_time, COUNT(*) as count
            FROM monitoring_api_metrics
            WHERE timestamp >= %s AND response_time_ms > 1000
            GROUP BY endpoint, method
            ORDER BY avg_time DESC
            LIMIT 10
        """
        slow_rows = execute_query(sql, (since,))
        
        return jsonify({
            "success": True,
            "data": {
                "stats": stats,
                "slow_endpoints": slow_rows,
                "period_hours": hours
            }
        })
    except Exception as e:
        logger.error(f"Error getting API metrics: {e}")
        return jsonify({"success": False, "error": str(e)})

@monitoring_bp.route('/alert-rules', methods=['GET'])
def get_alert_rules():
    """获取告警规则"""
    try:
        sql = "SELECT * FROM monitoring_alert_rules ORDER BY priority, id"
        rows = execute_query(sql)
        
        return jsonify({
            "success": True,
            "data": {"rules": rows}
        })
    except Exception as e:
        logger.error(f"Error getting alert rules: {e}")
        return jsonify({"success": False, "error": str(e)})

@monitoring_bp.route('/alert-rules', methods=['POST'])
def create_alert_rule():
    """创建告警规则"""
    try:
        data = request.get_json()
        sql = """
            INSERT INTO monitoring_alert_rules 
            (name, metric, condition, threshold, priority, enabled, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """
        execute_update(sql, (
            data.get('name'),
            data.get('metric'),
            data.get('condition'),
            data.get('threshold'),
            data.get('priority', 50),
            data.get('enabled', True)
        ))
        
        return jsonify({"success": True, "message": "Alert rule created"})
    except Exception as e:
        logger.error(f"Error creating alert rule: {e}")
        return jsonify({"success": False, "error": str(e)})

@monitoring_bp.route('/notifications', methods=['GET'])
def get_notifications():
    """获取通知"""
    try:
        limit = request.args.get('limit', 50, type=int)
        sql = """
            SELECT * FROM monitoring_notifications
            ORDER BY created_at DESC
            LIMIT %s
        """
        rows = execute_query(sql, (limit,))
        
        return jsonify({
            "success": True,
            "data": {"notifications": rows}
        })
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        return jsonify({"success": False, "error": str(e)})

@monitoring_bp.route('/logs', methods=['GET'])
def get_logs():
    """获取监控日志"""
    try:
        hours = request.args.get('hours', 24, type=int)
        limit = request.args.get('limit', 100, type=int)
        since = time.time() - (hours * 3600)
        
        sql = """
            SELECT * FROM monitoring_logs
            WHERE timestamp >= %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        rows = execute_query(sql, (since, limit))
        
        return jsonify({
            "success": True,
            "data": {
                "logs": rows,
                "period_hours": hours
            }
        })
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({"success": False, "error": str(e)})

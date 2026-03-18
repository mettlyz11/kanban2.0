#!/usr/bin/env python3
"""
任务审核API路由 (Task Audit API Routes)

为看板系统添加审核相关的API端点
"""

import os
import sys
import json
from datetime import datetime

# 导入Flask相关模块
from flask import Blueprint, request, jsonify

# 导入审核系统
from task_audit_system import task_audit_system, TaskSource
from gear_system_enhanced import gear_manager
from supervisor_system_enhanced import supervisor

# 创建蓝图
audit_bp = Blueprint('audit', __name__, url_prefix='/api/audit')


# =============================================================================
# 任务审核API
# =============================================================================

@audit_bp.route('/tasks/pending', methods=['GET'])
def get_pending_audits():
    """获取待审核任务列表"""
    try:
        source = request.args.get('source')
        
        # 转换source参数
        task_source = None
        if source:
            try:
                task_source = TaskSource(source)
            except ValueError:
                pass
        
        audits = task_audit_system.get_pending_audits(task_source)
        
        return jsonify({
            'success': True,
            'count': len(audits),
            'audits': audits
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@audit_bp.route('/tasks/<int:audit_id>/approve', methods=['POST'])
def approve_audit(audit_id):
    """批准任务"""
    try:
        data = request.get_json() or {}
        reviewer = data.get('reviewer', 'system')
        notes = data.get('notes', '')
        
        result = task_audit_system.approve_task(audit_id, reviewer, notes)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@audit_bp.route('/tasks/<int:audit_id>/reject', methods=['POST'])
def reject_audit(audit_id):
    """拒绝任务"""
    try:
        data = request.get_json() or {}
        reviewer = data.get('reviewer', 'system')
        reason = data.get('reason', '')
        
        result = task_audit_system.reject_task(audit_id, reviewer, reason)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@audit_bp.route('/tasks/stats', methods=['GET'])
def get_audit_stats():
    """获取审核统计"""
    try:
        stats = task_audit_system.get_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# 任务执行前检查API
# =============================================================================

@audit_bp.route('/tasks/<int:task_id>/check', methods=['GET'])
def check_task_before_exec(task_id):
    """检查任务是否可以执行"""
    try:
        result = task_audit_system.check_before_execution(task_id)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'can_execute': result['can_execute'],
            'status': result['status'],
            'message': result['message']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# 齿轮系统API
# =============================================================================

@audit_bp.route('/gear/execute', methods=['POST'])
def execute_gear():
    """执行齿轮 - 带审核检查"""
    try:
        data = request.get_json() or {}
        task_id = data.get('task_id')
        gear_name = data.get('gear_name')
        
        if not task_id or not gear_name:
            return jsonify({
                'success': False,
                'error': '缺少task_id或gear_name参数'
            }), 400
        
        # 检查审核状态
        audit_check = gear_manager.check_task_audit_status(task_id)
        
        if not audit_check['can_execute']:
            return jsonify({
                'success': False,
                'error': audit_check['message'],
                'audit_status': audit_check['status'],
                'requires_audit': True
            }), 403
        
        # 执行齿轮（这里需要根据实际齿轮逻辑实现）
        # result = gear_manager.execute_gear(task_id, gear_name, actual_func)
        
        return jsonify({
            'success': True,
            'message': '审核通过，可以执行',
            'task_id': task_id,
            'gear_name': gear_name
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@audit_bp.route('/gear/pending', methods=['GET'])
def get_pending_gear_tasks():
    """获取待审核的齿轮任务"""
    try:
        audits = task_audit_system.get_pending_audits(TaskSource.GEAR_SYSTEM)
        
        return jsonify({
            'success': True,
            'count': len(audits),
            'tasks': audits
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# 监督系统API
# =============================================================================

@audit_bp.route('/supervisor/enforce', methods=['POST'])
def enforce_audit_policy():
    """强制执行审核策略"""
    try:
        data = request.get_json() or {}
        task_id = data.get('task_id')
        
        if not task_id:
            return jsonify({
                'success': False,
                'error': '缺少task_id参数'
            }), 400
        
        result = supervisor.enforce_audit_policy(task_id)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'allowed': result['allowed'],
            'action': result['action'],
            'message': result['message'],
            'audit_status': result['audit_status']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@audit_bp.route('/supervisor/scan', methods=['POST'])
def scan_unaudited_tasks():
    """扫描未审核任务并创建审核请求"""
    try:
        result = supervisor.auto_create_audit_requests()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@audit_bp.route('/supervisor/report', methods=['GET'])
def get_supervisor_report():
    """获取监督报告"""
    try:
        report = supervisor.generate_audit_report()
        
        return jsonify({
            'success': True,
            'report': {
                'report_time': report.report_time,
                'total_tasks': report.total_tasks,
                'pending_audit': report.pending_audit,
                'approved': report.approved,
                'rejected': report.rejected,
                'executing': report.executing,
                'completed': report.completed,
                'failed': report.failed,
                'avg_audit_time_hours': report.avg_audit_time_hours,
                'critical_tasks': report.critical_tasks,
                'recommendations': report.recommendations
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@audit_bp.route('/supervisor/notify', methods=['POST'])
def notify_pending_audits():
    """发送待审核任务提醒"""
    try:
        result = supervisor.notify_pending_audits()
        
        return jsonify({
            'success': True,
            'notification': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@audit_bp.route('/supervisor/stats', methods=['GET'])
def get_supervisor_stats():
    """获取监督系统统计"""
    try:
        stats = supervisor.get_execution_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# 综合API
# =============================================================================

@audit_bp.route('/dashboard', methods=['GET'])
def get_audit_dashboard():
    """获取审核仪表板数据"""
    try:
        # 1. 获取审核统计
        audit_stats = task_audit_system.get_stats()
        
        # 2. 获取监督统计
        supervisor_stats = supervisor.get_execution_stats()
        
        # 3. 获取待审核任务
        pending_audits = task_audit_system.get_pending_audits()
        
        # 4. 按来源分组
        by_source = {}
        for source in TaskSource:
            by_source[source.value] = len(task_audit_system.get_pending_audits(source))
        
        return jsonify({
            'success': True,
            'dashboard': {
                'summary': {
                    'total_pending': audit_stats.get('pending', 0),
                    'total_approved': audit_stats.get('approved', 0),
                    'total_rejected': audit_stats.get('rejected', 0),
                    'by_source': by_source
                },
                'supervisor_stats': supervisor_stats.get('stats', {}),
                'recent_pending': pending_audits[:10],
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# 注册到主应用
# =============================================================================

def register_audit_routes(app):
    """注册审核路由到Flask应用"""
    app.register_blueprint(audit_bp)
    print("✅ 任务审核API路由已注册")


if __name__ == '__main__':
    print("=" * 60)
    print("任务审核API路由")
    print("=" * 60)
    print("\n可用端点:")
    print("  GET  /api/audit/tasks/pending       - 获取待审核任务")
    print("  POST /api/audit/tasks/<id>/approve  - 批准任务")
    print("  POST /api/audit/tasks/<id>/reject   - 拒绝任务")
    print("  GET  /api/audit/tasks/stats         - 获取统计")
    print("  GET  /api/audit/tasks/<id>/check    - 检查任务执行权限")
    print("  POST /api/audit/gear/execute        - 执行齿轮")
    print("  POST /api/audit/supervisor/enforce  - 强制执行审核")
    print("  POST /api/audit/supervisor/scan     - 扫描未审核任务")
    print("  GET  /api/audit/supervisor/report   - 获取监督报告")
    print("  GET  /api/audit/dashboard           - 获取仪表板")

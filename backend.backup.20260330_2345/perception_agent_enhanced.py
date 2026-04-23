#!/usr/bin/env python3
"""
增强型感知Agent (Enhanced Perception Agent)

修改内容:
1. 所有通过感知事件触发的任务创建都经过审核系统
2. 使用 TaskAuditSystem 注册所有自动生成的任务
3. 保持原有的事件监听功能
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# 导入原感知Agent的类和函数
from perception_agent import (
    PerceptionAgent, PerceptionEvent, EventType, SeverityLevel,
    LogListener, MetricListener, BehaviorListener
)

# 导入任务审核系统
from task_audit_system import task_audit_system, TaskSource

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('EnhancedPerceptionAgent')


class EnhancedPerceptionAgent(PerceptionAgent):
    """
    增强型感知Agent - 所有生成的任务都需要审核
    """
    
    def __init__(self, config_path: str = None):
        super().__init__(config_path)
        self.name = "EnhancedPerceptionAgent"
        
    def handle_event(self, event: PerceptionEvent):
        """
        处理感知事件 - 增强版
        
        当事件需要创建任务时，通过审核系统注册
        """
        logger.info(f"🎯 处理事件: {event.type} - {event.severity}")
        
        # 根据事件类型和严重程度决定是否创建任务
        if event.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]:
            self._create_task_from_event(event)
        
        # 调用父类的处理方法
        super().handle_event(event)
    
    def _create_task_from_event(self, event: PerceptionEvent):
        """
        从事件创建任务 - 必须经过审核
        """
        # 根据事件类型确定任务信息
        if event.type == EventType.API_ERROR:
            title = f"处理API错误: {event.source}"
            description = f"""
检测到API错误:
- 来源: {event.source}
- 消息: {event.message}
- 时间: {event.timestamp}
- 数据: {json.dumps(event.data, ensure_ascii=False, indent=2)}

建议操作:
1. 检查API日志
2. 分析错误原因
3. 修复相关问题
4. 验证修复效果
"""
            priority = 'high'
            
        elif event.type == EventType.METRIC_ALERT:
            metric_name = event.data.get('metric_name', 'unknown')
            title = f"处理指标告警: {metric_name}"
            description = f"""
检测到性能指标告警:
- 指标: {metric_name}
- 当前值: {event.data.get('current_value')}%
- 阈值: {event.data.get('threshold')}%
- 持续时间: {event.data.get('duration')}秒
- 时间: {event.timestamp}

建议操作:
1. 检查系统资源使用情况
2. 分析性能瓶颈
3. 优化相关配置
4. 监控优化效果
"""
            priority = 'high'
            
        elif event.type == EventType.LOG_ERROR:
            title = f"处理日志错误: {event.source}"
            description = f"""
检测到日志错误:
- 来源: {event.source}
- 消息: {event.message}
- 时间: {event.timestamp}

建议操作:
1. 查看详细日志
2. 分析错误原因
3. 修复相关问题
"""
            priority = 'medium'
            
        elif event.type == EventType.BEHAVIOR_PATTERN:
            title = f"处理行为模式: {event.source}"
            description = f"""
检测到用户行为模式:
- 来源: {event.source}
- 消息: {event.message}
- 时间: {event.timestamp}
- 数据: {json.dumps(event.data, ensure_ascii=False, indent=2)}

建议操作:
1. 分析用户行为
2. 评估优化机会
3. 考虑UI/UX改进
"""
            priority = 'low'
            
        else:
            title = f"处理感知事件: {event.type}"
            description = f"""
感知事件:
- 类型: {event.type}
- 严重程度: {event.severity}
- 来源: {event.source}
- 消息: {event.message}
- 时间: {event.timestamp}
"""
            priority = 'low'
        
        # 通过审核系统注册任务
        result = task_audit_system.register_task_generation(
            title=title,
            description=description,
            source=TaskSource.PERCEPTION_AGENT,
            priority=priority,
            suggested_action=f"处理{event.type}事件"
        )
        
        if result['success']:
            logger.info(f"✅ 已创建任务 {result['task_number']} 并提交审核")
        else:
            logger.error(f"❌ 创建任务失败: {result['message']}")
    
    def trigger_long_thinking(self, reason: str, context: Dict = None):
        """
        触发长思考 - 生成需要审核的任务
        """
        logger.info(f"🧠 触发长思考: {reason}")
        
        # 创建长思考任务
        result = task_audit_system.register_task_generation(
            title=f"长思考分析: {reason}",
            description=f"""
感知Agent触发了长思考:
- 原因: {reason}
- 上下文: {json.dumps(context or {}, ensure_ascii=False, indent=2)}
- 触发时间: {datetime.now().isoformat()}

需要执行:
1. 系统全面分析
2. 问题诊断
3. 生成改进任务
4. 提交审核
""",
            source=TaskSource.PERCEPTION_AGENT,
            priority='high',
            suggested_action='执行长思考分析'
        )
        
        if result['success']:
            logger.info(f"✅ 已创建长思考任务 {result['task_number']}")
        
        return result


def run_enhanced_perception_agent():
    """运行增强型感知Agent"""
    logger.info("🚀 启动增强型感知Agent...")
    
    # 创建配置
    config = {
        'database': {
            'path': '/opt/kanban-react/backend/kanban_v5.db'
        },
        'listeners': {
            'log_listener': {
                'enabled': True,
                'files': [
                    '/opt/kanban-react/backend/flask.log'
                ],
                'patterns': [
                    {'pattern': 'ERROR', 'severity': 'high'},
                    {'pattern': 'CRITICAL', 'severity': 'critical'},
                    {'pattern': 'Exception', 'severity': 'high'}
                ]
            },
            'metric_listener': {
                'enabled': True,
                'interval': 60,
                'metrics': [
                    {'name': 'cpu_usage', 'threshold': 80, 'duration': 300},
                    {'name': 'memory_usage', 'threshold': 85, 'duration': 300},
                    {'name': 'disk_usage', 'threshold': 90, 'duration': 600}
                ]
            },
            'behavior_listener': {
                'enabled': True,
                'patterns': []
            }
        },
        'long_thinking': {
            'enabled': True,
            'trigger_on_critical': True,
            'trigger_on_high': True,
            'min_interval_minutes': 30
        }
    }
    
    # 创建并启动Agent
    agent = EnhancedPerceptionAgent()
    
    # 配置监听器
    if config['listeners']['log_listener']['enabled']:
        log_listener = LogListener(config['listeners']['log_listener'])
        log_listener.on_event(agent.handle_event)
        agent.register_listener(log_listener)
    
    if config['listeners']['metric_listener']['enabled']:
        metric_listener = MetricListener(config['listeners']['metric_listener'])
        metric_listener.on_event(agent.handle_event)
        agent.register_listener(metric_listener)
    
    if config['listeners']['behavior_listener']['enabled']:
        behavior_listener = BehaviorListener(config['listeners']['behavior_listener'])
        behavior_listener.on_event(agent.handle_event)
        agent.register_listener(behavior_listener)
    
    # 启动Agent
    agent.start()
    
    logger.info("✅ 增强型感知Agent已启动，所有生成的任务都需要审核")
    
    return agent


if __name__ == '__main__':
    print("=" * 60)
    print("增强型感知Agent - 所有任务需要审核")
    print("=" * 60)
    
    agent = run_enhanced_perception_agent()
    
    try:
        # 保持运行
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 停止感知Agent...")
        agent.stop()

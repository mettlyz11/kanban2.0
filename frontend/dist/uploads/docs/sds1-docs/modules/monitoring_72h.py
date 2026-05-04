#!/usr/bin/env python3
"""
SDS 72小时无人值守监控与自愈系统
功能：连续监控系统状态，自动检测异常，执行自愈操作
"""

import os
import sys
import json
import time
import logging
import psutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Callable

# 添加lib路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from lib.db_connector import get_db_connection, execute_query, execute_update
from config_loader import get_config

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(get_config('paths.logs') + '/sds-72h-monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('72hMonitor')


class MonitoringAlert:
    """告警级别"""
    INFO = 'info'
    WARNING = 'warning'
    CRITICAL = 'critical'
    AUTO_HEALED = 'auto_healed'


class AnomalyDetector:
    """异常检测器 - 识别各类系统异常"""
    
    def __init__(self):
        self.conn = None
        self.alerts = []
    
    def connect(self):
        """连接数据库"""
        try:
            self.conn = get_db_connection()
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
    
    def check_system_resources(self) -> List[Dict]:
        """检查系统资源使用情况"""
        alerts = []
        
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                alerts.append({
                    'type': 'high_cpu',
                    'level': MonitoringAlert.CRITICAL,
                    'message': f"CPU使用率过高: {cpu_percent}%",
                    'value': cpu_percent,
                    'threshold': 90
                })
            elif cpu_percent > 70:
                alerts.append({
                    'type': 'high_cpu',
                    'level': MonitoringAlert.WARNING,
                    'message': f"CPU使用率偏高: {cpu_percent}%",
                    'value': cpu_percent,
                    'threshold': 70
                })
            
            # 内存使用率
            memory = psutil.virtual_memory()
            mem_percent = memory.percent
            if mem_percent > 90:
                alerts.append({
                    'type': 'high_memory',
                    'level': MonitoringAlert.CRITICAL,
                    'message': f"内存使用率过高: {mem_percent}%",
                    'value': mem_percent,
                    'threshold': 90
                })
            elif mem_percent > 75:
                alerts.append({
                    'type': 'high_memory',
                    'level': MonitoringAlert.WARNING,
                    'message': f"内存使用率偏高: {mem_percent}%",
                    'value': mem_percent,
                    'threshold': 75
                })
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            if disk_percent > 90:
                alerts.append({
                    'type': 'high_disk',
                    'level': MonitoringAlert.CRITICAL,
                    'message': f"磁盘使用率过高: {disk_percent}%",
                    'value': disk_percent,
                    'threshold': 90
                })
            elif disk_percent > 80:
                alerts.append({
                    'type': 'high_disk',
                    'level': MonitoringAlert.WARNING,
                    'message': f"磁盘使用率偏高: {disk_percent}%",
                    'value': disk_percent,
                    'threshold': 80
                })
            
        except Exception as e:
            logger.error(f"检查系统资源失败: {e}")
        
        return alerts
    
    def check_database_health(self) -> List[Dict]:
        """检查数据库健康状态"""
        alerts = []
        
        try:
            # 测试连接
            start_time = time.time()
            result = execute_query("SELECT 1 as test")
            query_time = (time.time() - start_time) * 1000
            
            if not result:
                alerts.append({
                    'type': 'db_connection',
                    'level': MonitoringAlert.CRITICAL,
                    'message': "数据库连接失败",
                    'value': 0,
                    'threshold': 0
                })
            elif query_time > 20000:
                alerts.append({
                    'type': 'slow_query',
                    'level': MonitoringAlert.WARNING,
                    'message': f"数据库查询响应慢: {query_time:.0f}ms",
                    'value': query_time,
                    'threshold': 20000
                })
            
            # 检查表损坏（简化检查）- 排除 VIEW 类型
            sql = """
                SELECT COUNT(*) as count FROM information_schema.tables 
                WHERE TABLE_SCHEMA = 'kanban' 
                  AND TABLE_ROWS IS NULL 
                  AND TABLE_TYPE = 'BASE TABLE'
            """
            result = execute_query(sql)
            if result and result[0]['count'] > 0:
                alerts.append({
                    'type': 'table_corruption',
                    'level': MonitoringAlert.CRITICAL,
                    'message': f"发现 {result[0]['count']} 个表可能损坏",
                    'value': result[0]['count'],
                    'threshold': 0
                })
            
        except Exception as e:
            alerts.append({
                'type': 'db_exception',
                'level': MonitoringAlert.CRITICAL,
                'message': f"数据库异常: {str(e)}",
                'value': 0,
                'threshold': 0
            })
        
        return alerts
    
    def check_sds_components(self) -> List[Dict]:
        """检查SDS各组件运行状态"""
        alerts = []
        
        try:
            # SDS v4.6+ 使用统一主日志，检查主日志是否在更新
            main_log = get_config('paths.logs') + '/sds-main.log'
            if os.path.exists(main_log):
                mtime = datetime.fromtimestamp(os.path.getmtime(main_log))
                hours_since = (datetime.now() - mtime).total_seconds() / 3600
                
                if hours_since > 2:
                    alerts.append({
                        'type': 'component_inactive',
                        'level': MonitoringAlert.CRITICAL,
                        'message': f"SDS 主进程可能已停止（主日志超过{hours_since:.1f}小时未更新）",
                        'value': hours_since,
                        'threshold': 2
                    })
                elif hours_since > 1:
                    alerts.append({
                        'type': 'component_inactive',
                        'level': MonitoringAlert.WARNING,
                        'message': f"SDS 主日志更新较慢（超过{hours_since:.1f}小时未更新）",
                        'value': hours_since,
                        'threshold': 1
                    })
            else:
                alerts.append({
                    'type': 'missing_log',
                    'level': MonitoringAlert.CRITICAL,
                    'message': "SDS 主日志文件不存在",
                    'value': 0,
                    'threshold': 0
                })
            
            # 检查 SDS 主进程是否存活
            # 修复：使用多种方法检测，避免误报
            import subprocess
            sds_process_found = False
            
            # 方法1：pgrep
            try:
                result = subprocess.run(['pgrep', '-f', 'sds_main.py'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    sds_process_found = True
                    logger.debug(f"pgrep 检测到 SDS 进程: {result.stdout.strip()}")
            except Exception as e:
                logger.warning(f"pgrep 检测失败: {e}")
            
            # 方法2：psutil（如果方法1失败）
            if not sds_process_found:
                try:
                    import psutil
                    for proc in psutil.process_iter(['pid', 'cmdline']):
                        try:
                            cmdline = ' '.join(proc.info['cmdline'] or [])
                            if 'sds_main.py' in cmdline:
                                sds_process_found = True
                                logger.debug(f"psutil 检测到 SDS 进程 PID: {proc.info['pid']}")
                                break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                except Exception as e:
                    logger.warning(f"psutil 检测失败: {e}")
            
            # 方法3：ps命令（最后回退）
            if not sds_process_found:
                try:
                    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
                    for line in result.stdout.split('\n'):
                        if 'sds_main.py' in line and 'grep' not in line:
                            sds_process_found = True
                            logger.debug(f"ps 检测到 SDS 进程: {line[:80]}")
                            break
                except Exception as e:
                    logger.warning(f"ps 检测失败: {e}")
            
            if not sds_process_found:
                alerts.append({
                    'type': 'process_dead',
                    'level': MonitoringAlert.CRITICAL,
                    'message': "SDS 主进程未运行",
                    'value': 0,
                    'threshold': 0
                })
            
            # 检查长时间运行的任务（可能卡住）
            sql = """
                SELECT id, number, title, 
                       TIMESTAMPDIFF(HOUR, updated_at, NOW()) as hours_running
                FROM tasks
                WHERE status = 'in_progress'
                  AND TIMESTAMPDIFF(HOUR, updated_at, NOW()) > 12
            """
            stuck_tasks = execute_query(sql)
            
            for task in stuck_tasks:
                alerts.append({
                    'type': 'stuck_task',
                    'level': MonitoringAlert.WARNING,
                    'message': f"任务可能卡住: #{task['id']} - {task['title'][:50]} ({task['hours_running']}小时)",
                    'task_id': task['id'],
                    'hours_running': task['hours_running'],
                    'threshold': 12
                })
        
        except Exception as e:
            logger.error(f"检查SDS组件失败: {e}")
        
        return alerts
    
    def check_task_throughput(self) -> List[Dict]:
        """检查任务吞吐量异常"""
        alerts = []
        
        try:
            # 检查24小时内完成的任务数
            sql = """
                SELECT COUNT(*) as count
                FROM tasks
                WHERE status = 'completed'
                  AND updated_at >= NOW() - INTERVAL 24 HOUR
            """
            result = execute_query(sql)
            completed_24h = result[0]['count'] if result else 0
            
            if completed_24h == 0:
                alerts.append({
                    'type': 'no_throughput',
                    'level': MonitoringAlert.CRITICAL,
                    'message': "24小时内没有任务完成，系统可能已停滞",
                    'value': 0,
                    'threshold': 1
                })
            elif completed_24h < 3:
                alerts.append({
                    'type': 'low_throughput',
                    'level': MonitoringAlert.WARNING,
                    'message': f"任务吞吐量偏低: 24小时内仅完成{completed_24h}个任务",
                    'value': completed_24h,
                    'threshold': 3
                })
        
        except Exception as e:
            logger.error(f"检查任务吞吐量失败: {e}")
        
        return alerts
    
    def run_detection(self) -> Dict:
        """运行完整异常检测"""
        logger.info("开始异常检测...")
        
        if not self.connect():
            return {'error': '数据库连接失败'}
        
        try:
            all_alerts = []
            
            # 执行各项检查
            all_alerts.extend(self.check_system_resources())
            all_alerts.extend(self.check_database_health())
            all_alerts.extend(self.check_sds_components())
            all_alerts.extend(self.check_task_throughput())
            
            # 统计告警
            critical_count = sum(1 for a in all_alerts if a['level'] == MonitoringAlert.CRITICAL)
            warning_count = sum(1 for a in all_alerts if a['level'] == MonitoringAlert.WARNING)
            
            detection_result = {
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_alerts': len(all_alerts),
                    'critical': critical_count,
                    'warning': warning_count,
                    'info': len(all_alerts) - critical_count - warning_count
                },
                'alerts': all_alerts
            }
            
            # 记录告警
            for alert in all_alerts:
                logger.log(
                    logging.CRITICAL if alert['level'] == MonitoringAlert.CRITICAL 
                    else logging.WARNING,
                    f"[{alert['level'].upper()}] {alert['message']}"
                )
            
            return detection_result
            
        finally:
            self.close()


class SelfHealingEngine:
    """自愈引擎 - 自动处理检测到的异常"""
    
    def __init__(self):
        self.healing_actions = []
        
        # 自愈策略映射
        self.healing_strategies = {
            'high_memory': self._heal_high_memory,
            'stuck_task': self._heal_stuck_task,
            'no_throughput': self._heal_no_throughput,
            'component_inactive': self._heal_component_inactive
        }
    
    def _heal_high_memory(self, alert: Dict) -> bool:
        """处理高内存使用"""
        logger.info("执行高内存自愈操作...")
        
        try:
            # 清理Python缓存
            import shutil
            cache_dirs = [
                '/Users/mettlyz/.openclaw/workspace/__pycache__',
                '/Users/mettlyz/.openclaw/workspace/scripts/lib/__pycache__'
            ]
            
            for cache_dir in cache_dirs:
                if os.path.exists(cache_dir):
                    shutil.rmtree(cache_dir)
                    logger.info(f"已清理缓存: {cache_dir}")
            
            # 清理临时文件
            tmp_dir = '/Users/mettlyz/.openclaw/workspace/tmp'
            if os.path.exists(tmp_dir):
                for f in os.listdir(tmp_dir):
                    fpath = os.path.join(tmp_dir, f)
                    if os.path.isfile(fpath) and time.time() - os.path.getmtime(fpath) > 86400:
                        os.remove(fpath)
                        logger.info(f"已清理临时文件: {f}")
            
            self._record_healing_action(alert, True, "清理了Python缓存和过期临时文件")
            return True
            
        except Exception as e:
            logger.error(f"高内存自愈失败: {e}")
            self._record_healing_action(alert, False, str(e))
            return False
    
    def _heal_stuck_task(self, alert: Dict) -> bool:
        """处理卡住的任务"""
        logger.info(f"执行卡住任务自愈: 任务 #{alert.get('task_id')}")
        
        try:
            task_id = alert.get('task_id')
            if not task_id:
                return False
            
            # 重置任务状态为pending，增加重试计数
            cursor = get_db_connection().cursor()
            cursor.execute("""
                UPDATE tasks
                SET status = 'pending',
                    retry_count = COALESCE(retry_count, 0) + 1,
                    execution_log = CONCAT(COALESCE(execution_log, ''), %s),
                    updated_at = NOW()
                WHERE id = %s
            """, (
                f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] SDS自愈: 任务疑似卡住，已重置为pending状态\n",
                task_id
            ))
            get_db_connection().commit()
            
            self._record_healing_action(alert, True, f"已重置任务 #{task_id} 为pending状态")
            return True
            
        except Exception as e:
            logger.error(f"卡住任务自愈失败: {e}")
            self._record_healing_action(alert, False, str(e))
            return False
    
    def _heal_no_throughput(self, alert: Dict) -> bool:
        """处理无任务吞吐量"""
        logger.info("执行无吞吐量自愈操作...")
        
        try:
            # 运行任务分析器和生成器，创建新任务
            from modules.task_analyzer import TaskAnalyzer
            from auto_task_generator import AutoTaskGenerator
            
            analyzer = TaskAnalyzer()
            analysis = analyzer.run_full_analysis()
            
            if 'error' not in analysis:
                generator = AutoTaskGenerator()
                result = generator.run_generation(analysis)
                
                self._record_healing_action(
                    alert, True, 
                    f"已运行分析器和生成器，创建了 {result.get('tasks_created', 0)} 个新任务"
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"无吞吐量自愈失败: {e}")
            self._record_healing_action(alert, False, str(e))
            return False
    
    def _heal_component_inactive(self, alert: Dict) -> bool:
        """处理组件不活跃"""
        logger.info("执行组件激活自愈操作...")
        
        try:
            # 运行一次完整调度周期来激活组件
            from modules.subagent_scheduler import run_scheduler_cycle
            run_scheduler_cycle()
            
            self._record_healing_action(alert, True, "已运行调度周期激活组件")
            return True
            
        except Exception as e:
            logger.error(f"组件激活自愈失败: {e}")
            self._record_healing_action(alert, False, str(e))
            return False
    
    def _record_healing_action(self, alert: Dict, success: bool, details: str):
        """记录自愈操作"""
        action = {
            'timestamp': datetime.now().isoformat(),
            'alert_type': alert.get('type'),
            'alert_message': alert.get('message'),
            'success': success,
            'details': details
        }
        self.healing_actions.append(action)
        
        level = MonitoringAlert.AUTO_HEALED if success else MonitoringAlert.CRITICAL
        logger.log(
            logging.INFO if success else logging.ERROR,
            f"[AUTO-HEAL {'SUCCESS' if success else 'FAILED'}] {details}"
        )
    
    def heal(self, alerts: List[Dict]) -> Dict:
        """执行自愈操作"""
        logger.info(f"开始处理 {len(alerts)} 个告警...")
        
        healed = 0
        failed = 0
        
        for alert in alerts:
            alert_type = alert.get('type')
            strategy = self.healing_strategies.get(alert_type)
            
            if strategy and alert['level'] != MonitoringAlert.INFO:
                try:
                    if strategy(alert):
                        healed += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"自愈策略执行异常: {e}")
                    failed += 1
            else:
                logger.info(f"无自愈策略或无需处理: {alert_type}")
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'total_alerts': len(alerts),
            'healed': healed,
            'failed': failed,
            'actions': self.healing_actions
        }
        
        logger.info(f"自愈完成: 成功 {healed}, 失败 {failed}")
        return result


class _72hMonitor:
    """72小时无人值守监控主类"""
    
    def __init__(self):
        self.detector = AnomalyDetector()
        self.healer = SelfHealingEngine()
        self.start_time = datetime.now()
        self.check_interval = 300  # 5分钟检查一次
        self.max_runtime = 72 * 3600  # 72小时
        
        # 状态文件
        self.state_file = Path(get_config('paths.logs') + "/sds-72h-state.json")
        self.load_state()
    
    def load_state(self):
        """加载监控状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
                    logger.info(f"已加载监控状态: 运行中 {self.state.get('total_checks', 0)} 次检查")
            except:
                self.state = self._init_state()
        else:
            self.state = self._init_state()
    
    def _init_state(self) -> Dict:
        """初始化状态"""
        return {
            'monitor_start_time': self.start_time.isoformat(),
            'total_checks': 0,
            'total_alerts': 0,
            'total_healed': 0,
            'consecutive_normal_checks': 0,
            'uptime_seconds': 0,
            'last_check_time': None,
            'check_history': []
        }
    
    def save_state(self):
        """保存监控状态"""
        self.state['uptime_seconds'] = (datetime.now() - self.start_time).total_seconds()
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
    
    def run_check_cycle(self) -> Dict:
        """运行一次检查周期"""
        logger.info("=" * 60)
        logger.info(f"72h监控检查周期 #{self.state['total_checks'] + 1}")
        logger.info("=" * 60)
        
        # 1. 异常检测
        try:
            detection = self.detector.run_detection()
        except Exception as e:
            logger.error(f"异常检测失败: {e}", exc_info=True)
            detection = {'alerts': [], 'system_health': 'unknown'}
        
        # 2. 自愈处理（只处理CRITICAL和WARNING）
        critical_alerts = [a for a in detection.get('alerts', []) 
                          if a['level'] in [MonitoringAlert.CRITICAL, MonitoringAlert.WARNING]]
        
        try:
            healing_result = self.healer.heal(critical_alerts)
        except Exception as e:
            logger.error(f"自愈引擎执行失败: {e}", exc_info=True)
            healing_result = {'total_alerts': len(critical_alerts), 'healed': 0, 'failed': len(critical_alerts), 'actions': []}
        
        # 3. 更新状态
        self.state['total_checks'] += 1
        self.state['total_alerts'] += len(critical_alerts)
        self.state['total_healed'] += healing_result['healed']
        self.state['last_check_time'] = datetime.now().isoformat()
        
        if len(critical_alerts) == 0:
            self.state['consecutive_normal_checks'] += 1
        else:
            self.state['consecutive_normal_checks'] = 0
        
        # 记录检查历史（保留最近100条）
        history_entry = {
            'check_time': datetime.now().isoformat(),
            'alerts_count': len(critical_alerts),
            'healed_count': healing_result['healed']
        }
        self.state['check_history'].append(history_entry)
        if len(self.state['check_history']) > 100:
            self.state['check_history'] = self.state['check_history'][-100:]
        
        self.save_state()
        
        # 4. 生成报告
        cycle_report = {
            'check_number': self.state['total_checks'],
            'timestamp': datetime.now().isoformat(),
            'uptime_hours': self.state['uptime_seconds'] / 3600,
            'detection': detection,
            'healing': healing_result,
            'consecutive_normal': self.state['consecutive_normal_checks']
        }
        
        # 保存周期报告
        report_file = Path(get_config('paths.logs') + f"/sds-72h-check-{self.state['total_checks']}.json")
        with open(report_file, 'w') as f:
            json.dump(cycle_report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"检查周期完成，连续正常: {self.state['consecutive_normal_checks']}")
        return cycle_report
    
    def run_continuous_monitoring(self):
        """运行连续监控（72小时）"""
        logger.info("=" * 60)
        logger.info("SDS 72小时无人值守监控启动")
        logger.info(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"检查间隔: {self.check_interval}秒")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        try:
            while True:
                elapsed = time.time() - start_time
                
                if elapsed >= self.max_runtime:
                    logger.info("已达到72小时运行时长，监控结束")
                    break
                
                # 运行检查周期
                self.run_check_cycle()
                
                # 显示运行进度
                elapsed_hours = elapsed / 3600
                progress = (elapsed / self.max_runtime) * 100
                logger.info(f"运行进度: {elapsed_hours:.1f}h / 72h ({progress:.1f}%)")
                
                # 等待下一次检查
                time.sleep(self.check_interval)
        
        except KeyboardInterrupt:
            logger.info("用户中断，监控停止")
        except Exception as e:
            logger.error(f"监控异常: {e}")
        finally:
            self.generate_final_report()
    
    def generate_final_report(self):
        """生成最终监控报告"""
        logger.info("生成72小时监控最终报告...")
        
        final_report = {
            'monitor_start_time': self.state['monitor_start_time'],
            'monitor_end_time': datetime.now().isoformat(),
            'total_runtime_hours': self.state['uptime_seconds'] / 3600,
            'total_checks': self.state['total_checks'],
            'total_alerts': self.state['total_alerts'],
            'total_healed': self.state['total_healed'],
            'max_consecutive_normal': max(
                [h.get('consecutive_normal', 0) for h in self.state['check_history']] + [0]
            ),
            'summary': "SDS 72小时无人值守监控完成，系统运行正常" if self.state['consecutive_normal_checks'] >= 10 
                      else "SDS 72小时监控完成，存在需要关注的问题"
        }
        
        report_file = Path(get_config('paths.output') + "/task-1570/72h-monitoring-final-report.json")
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(final_report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"最终报告已保存到: {report_file}")
        logger.info(json.dumps(final_report, indent=2, ensure_ascii=False))
        
        return final_report


if __name__ == "__main__":
    monitor = _72hMonitor()
    
    # 如果带 --once 参数，只运行一次检查
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        monitor.run_check_cycle()
    else:
        # 运行连续监控
        monitor.run_continuous_monitoring()

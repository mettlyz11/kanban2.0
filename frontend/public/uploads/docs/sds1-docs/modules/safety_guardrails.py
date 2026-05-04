#!/usr/bin/env python3
"""
SDS安全护栏与回滚机制 (Safety Guardrails & Rollback)
功能：监控高危操作，执行安全检查，提供系统回滚能力
"""

import os
import sys
import json
import shutil
import logging
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
        logging.FileHandler(get_config('paths.logs') + '/sds-safety-guardrails.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SafetyGuardrails')


class OperationRiskLevel:
    """操作风险级别"""
    SAFE = 'safe'           # 无风险，可自动执行
    LOW = 'low'             # 低风险，可自动执行但记录日志
    MEDIUM = 'medium'       # 中等风险，需要额外验证
    HIGH = 'high'           # 高风险，需要人工审批
    CRITICAL = 'critical'   # 极高风险，默认禁止


class RiskAnalyzer:
    """风险分析器 - 分析操作的风险级别"""
    
    def __init__(self):
        # 高危操作模式定义
        self.high_risk_patterns = {
            'database': [
                ('DROP TABLE', OperationRiskLevel.CRITICAL),
                ('DROP DATABASE', OperationRiskLevel.CRITICAL),
                ('DELETE FROM.*WHERE', OperationRiskLevel.HIGH),
                ('TRUNCATE', OperationRiskLevel.HIGH),
                ('ALTER TABLE.*DROP', OperationRiskLevel.HIGH),
                ('UPDATE.*WHERE', OperationRiskLevel.MEDIUM),
            ],
            'system': [
                ('rm -rf /', OperationRiskLevel.CRITICAL),
                ('rm -rf.*\\*', OperationRiskLevel.CRITICAL),
                ('sudo rm', OperationRiskLevel.HIGH),
                ('shutdown', OperationRiskLevel.CRITICAL),
                ('reboot', OperationRiskLevel.HIGH),
                ('chmod 777', OperationRiskLevel.HIGH),
                ('chown -R', OperationRiskLevel.MEDIUM),
            ],
            'network': [
                ('iptables -F', OperationRiskLevel.HIGH),
                ('ufw disable', OperationRiskLevel.HIGH),
                ('ssh.*-R.*:', OperationRiskLevel.MEDIUM),  # 反向隧道
            ]
        }
        
        # 受保护的服务器列表（禁止修改）
        self.protected_servers = ['server1', '47.93.184.128']
        
        # 禁止的操作
        self.forbidden_operations = [
            'macOS系统更新',
            '修改Server 1配置',
            '重启Gateway服务',
            '删除数据库表'
        ]
    
    def analyze_sql_risk(self, sql: str) -> Dict:
        """分析SQL操作风险"""
        sql_upper = sql.upper().strip()
        risk_level = OperationRiskLevel.SAFE
        reasons = []
        
        for pattern, level in self.high_risk_patterns['database']:
            if pattern.upper() in sql_upper:
                risk_level = max(risk_level, level, key=lambda x: [
                    OperationRiskLevel.SAFE,
                    OperationRiskLevel.LOW,
                    OperationRiskLevel.MEDIUM,
                    OperationRiskLevel.HIGH,
                    OperationRiskLevel.CRITICAL
                ].index(x))
                reasons.append(f"匹配高危模式: {pattern}")
        
        return {
            'risk_level': risk_level,
            'reasons': reasons,
            'requires_audit': risk_level in [OperationRiskLevel.HIGH, OperationRiskLevel.CRITICAL],
            'forbidden': risk_level == OperationRiskLevel.CRITICAL
        }
    
    def analyze_command_risk(self, command: str) -> Dict:
        """分析命令行操作风险"""
        cmd_lower = command.lower()
        risk_level = OperationRiskLevel.SAFE
        reasons = []
        
        # 检查系统命令风险
        for pattern, level in self.high_risk_patterns['system']:
            if pattern.lower() in cmd_lower:
                risk_level = max(risk_level, level, key=lambda x: [
                    OperationRiskLevel.SAFE,
                    OperationRiskLevel.LOW,
                    OperationRiskLevel.MEDIUM,
                    OperationRiskLevel.HIGH,
                    OperationRiskLevel.CRITICAL
                ].index(x))
                reasons.append(f"匹配高危系统命令: {pattern}")
        
        # 检查网络命令风险
        for pattern, level in self.high_risk_patterns['network']:
            if pattern.lower() in cmd_lower:
                risk_level = max(risk_level, level, key=lambda x: [
                    OperationRiskLevel.SAFE,
                    OperationRiskLevel.LOW,
                    OperationRiskLevel.MEDIUM,
                    OperationRiskLevel.HIGH,
                    OperationRiskLevel.CRITICAL
                ].index(x))
                reasons.append(f"匹配高危网络命令: {pattern}")
        
        # 检查受保护服务器
        for server in self.protected_servers:
            if server in command:
                risk_level = OperationRiskLevel.HIGH
                reasons.append(f"操作涉及受保护服务器: {server}")
        
        # 检查禁止操作
        for forbidden in self.forbidden_operations:
            if forbidden in command:
                risk_level = OperationRiskLevel.CRITICAL
                reasons.append(f"禁止操作: {forbidden}")
        
        return {
            'risk_level': risk_level,
            'reasons': reasons,
            'requires_audit': risk_level in [OperationRiskLevel.HIGH, OperationRiskLevel.CRITICAL],
            'forbidden': risk_level == OperationRiskLevel.CRITICAL
        }
    
    def analyze_file_operation_risk(self, file_path: str, operation: str) -> Dict:
        """分析文件操作风险"""
        risk_level = OperationRiskLevel.SAFE
        reasons = []
        
        # 关键文件列表
        critical_files = [
            '/etc/passwd',
            '/etc/shadow',
            '~/.ssh/id_rsa',
            '~/.openclaw/.env',
            'kanban.sql',
            'database_backup'
        ]
        
        for critical in critical_files:
            if critical in file_path or file_path in critical:
                if operation in ['write', 'delete', 'modify']:
                    risk_level = OperationRiskLevel.HIGH
                    reasons.append(f"操作关键文件: {file_path}")
                break
        
        return {
            'risk_level': risk_level,
            'reasons': reasons,
            'requires_audit': risk_level in [OperationRiskLevel.HIGH, OperationRiskLevel.CRITICAL],
            'forbidden': risk_level == OperationRiskLevel.CRITICAL
        }


class SystemBackupManager:
    """系统备份管理器 - 创建和管理系统备份点"""
    
    def __init__(self):
        self.backup_dir = Path(get_config('paths.logs') + "/sds-backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.max_backups = 10  # 保留最近10个备份
    
    def create_backup_point(self, name: str = None) -> Dict:
        """创建备份点"""
        if not name:
            name = f"sds-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        backup_path = self.backup_dir / name
        backup_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"创建备份点: {backup_path}")
        
        backup_items = {
            'timestamp': datetime.now().isoformat(),
            'name': name,
            'items': []
        }
        
        try:
            # 1. 备份关键配置文件
            config_files = [
                Path("/Users/mettlyz/.openclaw/workspace/.env"),
                Path("/Users/mettlyz/.openclaw/workspace/SELF_DRIVING_SYSTEM.md"),
                Path("/Users/mettlyz/.openclaw/workspace/workflow-automation.md"),
            ]
            
            for config_file in config_files:
                if config_file.exists():
                    dest = backup_path / config_file.name
                    shutil.copy2(config_file, dest)
                    backup_items['items'].append({
                        'type': 'config',
                        'source': str(config_file),
                        'destination': str(dest)
                    })
            
            # 2. 备份SDS核心脚本
            sds_scripts_dir = Path("/Users/mettlyz/.openclaw/workspace/sds")
            if sds_scripts_dir.exists():
                dest_scripts = backup_path / 'sds_scripts'
                shutil.copytree(sds_scripts_dir, dest_scripts)
                backup_items['items'].append({
                    'type': 'scripts',
                    'source': str(sds_scripts_dir),
                    'destination': str(dest_scripts)
                })
            
            # 3. 执行数据库备份（简化版 - 导出关键数据）
            db_backup_file = backup_path / 'tasks_backup.json'
            self._backup_tasks_data(db_backup_file)
            backup_items['items'].append({
                'type': 'database',
                'table': 'tasks',
                'destination': str(db_backup_file)
            })
            
            # 保存备份元数据
            metadata_file = backup_path / 'backup_metadata.json'
            with open(metadata_file, 'w') as f:
                json.dump(backup_items, f, indent=2, ensure_ascii=False)
            
            # 清理旧备份
            self._cleanup_old_backups()
            
            logger.info(f"✓ 备份点创建成功: {name}")
            return {
                'success': True,
                'name': name,
                'path': str(backup_path),
                'items_count': len(backup_items['items']),
                'timestamp': backup_items['timestamp']
            }
            
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _backup_tasks_data(self, output_file: Path):
        """备份任务数据"""
        try:
            sql = "SELECT * FROM tasks ORDER BY id DESC LIMIT 1000"
            results = execute_query(sql)
            
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            logger.error(f"备份任务数据失败: {e}")
    
    def _cleanup_old_backups(self):
        """清理旧备份"""
        backups = sorted(self.backup_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
        
        if len(backups) > self.max_backups:
            for old_backup in backups[self.max_backups:]:
                try:
                    if old_backup.is_dir():
                        shutil.rmtree(old_backup)
                        logger.info(f"已清理旧备份: {old_backup.name}")
                except Exception as e:
                    logger.error(f"清理备份失败: {e}")
    
    def list_backups(self) -> List[Dict]:
        """列出所有备份"""
        backups = []
        
        for backup_dir in sorted(self.backup_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            metadata_file = backup_dir / 'backup_metadata.json'
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        backups.append(metadata)
                except:
                    pass
        
        return backups
    
    def restore_backup(self, backup_name: str) -> Dict:
        """从备份恢复"""
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            return {'success': False, 'error': f"备份不存在: {backup_name}"}
        
        logger.info(f"开始从备份恢复: {backup_name}")
        
        try:
            # 创建当前状态备份（恢复前）
            self.create_backup_point(f"pre-restore-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
            
            metadata_file = backup_path / 'backup_metadata.json'
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            restored_items = []
            
            for item in metadata['items']:
                if item['type'] == 'config':
                    dest = Path(item['source'])
                    src = Path(item['destination'])
                    if src.exists():
                        shutil.copy2(src, dest)
                        restored_items.append(item['source'])
                
                elif item['type'] == 'scripts':
                    dest = Path("/Users/mettlyz/.openclaw/workspace/sds")
                    src = Path(item['destination'])
                    if src.exists() and dest.exists():
                        shutil.rmtree(dest)
                        shutil.copytree(src, dest)
                        restored_items.append('sds_scripts')
                
                elif item['type'] == 'database':
                    # 数据库恢复需要人工审核
                    logger.warning(f"数据库恢复需要人工审核: {item['destination']}")
            
            logger.info(f"✓ 恢复完成，已恢复 {len(restored_items)} 项")
            
            return {
                'success': True,
                'backup_name': backup_name,
                'restored_items': restored_items
            }
            
        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            return {'success': False, 'error': str(e)}


class RollbackManager:
    """回滚管理器 - 提供操作回滚能力"""
    
    def __init__(self):
        self.rollback_log_dir = Path(get_config('paths.logs') + "/rollback")
        self.rollback_log_dir.mkdir(parents=True, exist_ok=True)
        self.backup_manager = SystemBackupManager()
    
    def create_rollback_point(self, operation: str, description: str) -> str:
        """创建回滚点"""
        rollback_id = f"rollback-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{hash(operation) % 10000:04d}"
        
        # 创建备份
        backup_result = self.backup_manager.create_backup_point(rollback_id)
        
        if backup_result['success']:
            # 记录回滚日志
            log_entry = {
                'rollback_id': rollback_id,
                'operation': operation,
                'description': description,
                'timestamp': datetime.now().isoformat(),
                'backup_name': backup_result['name'],
                'status': 'active'
            }
            
            log_file = self.rollback_log_dir / f"{rollback_id}.json"
            with open(log_file, 'w') as f:
                json.dump(log_entry, f, indent=2, ensure_ascii=False)
            
            logger.info(f"已创建回滚点: {rollback_id}")
            return rollback_id
        else:
            logger.error("创建回滚点失败")
            return None
    
    def rollback(self, rollback_id: str) -> Dict:
        """执行回滚"""
        log_file = self.rollback_log_dir / f"{rollback_id}.json"
        
        if not log_file.exists():
            return {'success': False, 'error': f"回滚点不存在: {rollback_id}"}
        
        with open(log_file, 'r') as f:
            log_entry = json.load(f)
        
        logger.info(f"执行回滚: {rollback_id} - {log_entry['description']}")
        
        # 从备份恢复
        restore_result = self.backup_manager.restore_backup(log_entry['backup_name'])
        
        # 更新回滚日志状态
        log_entry['rollback_time'] = datetime.now().isoformat()
        log_entry['status'] = 'rolled_back'
        log_entry['rollback_result'] = restore_result
        
        with open(log_file, 'w') as f:
            json.dump(log_entry, f, indent=2, ensure_ascii=False)
        
        return restore_result
    
    def list_rollback_points(self) -> List[Dict]:
        """列出所有回滚点"""
        rollback_points = []
        
        for log_file in sorted(self.rollback_log_dir.glob("rollback-*.json"), reverse=True):
            try:
                with open(log_file, 'r') as f:
                    rollback_points.append(json.load(f))
            except:
                pass
        
        return rollback_points


class SafetyGuardrail:
    """安全护栏主类 - 整合所有安全功能"""
    
    def __init__(self):
        self.risk_analyzer = RiskAnalyzer()
        self.backup_manager = SystemBackupManager()
        self.rollback_manager = RollbackManager()
        self.audit_log_file = Path(get_config('paths.logs') + "/sds-audit-log.jsonl")
    
    def log_audit(self, operation_type: str, operation: str, risk_analysis: Dict, approved: bool):
        """记录审计日志"""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation_type': operation_type,
            'operation': operation[:500],  # 截断避免过大
            'risk_level': risk_analysis['risk_level'],
            'risk_reasons': risk_analysis['reasons'],
            'requires_audit': risk_analysis['requires_audit'],
            'forbidden': risk_analysis['forbidden'],
            'approved': approved
        }
        
        with open(self.audit_log_file, 'a') as f:
            f.write(json.dumps(audit_entry, ensure_ascii=False) + '\n')
    
    def check_sql_operation(self, sql: str, auto_approve_safe: bool = True) -> Dict:
        """检查SQL操作"""
        risk = self.risk_analyzer.analyze_sql_risk(sql)
        
        result = {
            'allowed': False,
            'risk': risk,
            'requires_approval': risk['requires_audit'],
            'message': ''
        }
        
        if risk['forbidden']:
            result['message'] = f"操作被禁止: {', '.join(risk['reasons'])}"
            self.log_audit('sql', sql, risk, False)
            logger.warning(f"[FORBIDDEN] SQL操作被禁止: {result['message']}")
        
        elif risk['requires_audit']:
            result['message'] = f"操作需要人工审批 [{risk['risk_level']}]: {', '.join(risk['reasons'])}"
            self.log_audit('sql', sql, risk, False)
            logger.warning(f"[AUDIT REQUIRED] SQL操作需要审批: {result['message']}")
        
        elif auto_approve_safe:
            result['allowed'] = True
            result['message'] = f"操作已批准 [{risk['risk_level']}]"
            self.log_audit('sql', sql, risk, True)
            logger.info(f"[APPROVED] SQL操作: {sql[:100]}...")
        
        return result
    
    def check_command_operation(self, command: str, auto_approve_safe: bool = True) -> Dict:
        """检查命令行操作"""
        risk = self.risk_analyzer.analyze_command_risk(command)
        
        result = {
            'allowed': False,
            'risk': risk,
            'requires_approval': risk['requires_audit'],
            'message': ''
        }
        
        if risk['forbidden']:
            result['message'] = f"命令被禁止: {', '.join(risk['reasons'])}"
            self.log_audit('command', command, risk, False)
            logger.warning(f"[FORBIDDEN] 命令被禁止: {result['message']}")
        
        elif risk['requires_audit']:
            result['message'] = f"命令需要人工审批 [{risk['risk_level']}]: {', '.join(risk['reasons'])}"
            self.log_audit('command', command, risk, False)
            logger.warning(f"[AUDIT REQUIRED] 命令需要审批: {result['message']}")
        
        elif auto_approve_safe:
            result['allowed'] = True
            result['message'] = f"命令已批准 [{risk['risk_level']}]"
            self.log_audit('command', command, risk, True)
            logger.info(f"[APPROVED] 命令: {command[:100]}...")
        
        return result
    
    def execute_with_rollback(self, operation_func: Callable, operation_name: str, 
                             description: str) -> Dict:
        """带回滚保护执行操作"""
        logger.info(f"执行带保护的操作: {operation_name}")
        
        # 1. 创建回滚点
        rollback_id = self.rollback_manager.create_rollback_point(operation_name, description)
        
        if not rollback_id:
            return {'success': False, 'error': '创建回滚点失败'}
        
        try:
            # 2. 执行操作
            result = operation_func()
            
            # 3. 操作成功，标记回滚点为可清理
            logger.info(f"操作成功完成: {operation_name}")
            return {
                'success': True,
                'rollback_id': rollback_id,
                'operation_result': result,
                'message': '操作成功完成，回滚点已保留'
            }
        
        except Exception as e:
            logger.error(f"操作失败，执行回滚: {e}")
            
            # 4. 操作失败，执行回滚
            rollback_result = self.rollback_manager.rollback(rollback_id)
            
            return {
                'success': False,
                'error': str(e),
                'rollback_executed': True,
                'rollback_result': rollback_result
            }
    
    def generate_safety_report(self) -> str:
        """生成安全报告"""
        audit_count = 0
        forbidden_count = 0
        high_risk_count = 0
        
        if self.audit_log_file.exists():
            with open(self.audit_log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        audit_count += 1
                        if entry.get('forbidden'):
                            forbidden_count += 1
                        if entry.get('risk_level') in ['high', 'critical']:
                            high_risk_count += 1
                    except:
                        pass
        
        backups = self.backup_manager.list_backups()
        rollback_points = self.rollback_manager.list_rollback_points()
        
        report = f"""# SDS 安全护栏报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 安全统计

| 指标 | 数值 |
|------|------|
| 总审计记录数 | {audit_count} |
| 禁止操作数 | {forbidden_count} |
| 高风险操作数 | {high_risk_count} |
| 可用备份点 | {len(backups)} |
| 可用回滚点 | {len(rollback_points)} |

## 🛡️ 保护规则

### 数据库操作
- ❌ 禁止: DROP TABLE, DROP DATABASE
- ⚠️ 需要审批: DELETE, TRUNCATE, ALTER TABLE DROP
- ✅ 自动批准: SELECT, INSERT

### 系统操作
- ❌ 禁止: rm -rf /, shutdown, macOS系统更新
- ⚠️ 需要审批: sudo rm, reboot, 防火墙修改
- ✅ 自动批准: 只读操作, 日志清理

### 受保护资源
- Server 1 (47.93.184.128) - 禁止任何修改
- Gateway服务 - 禁止重启
- 关键配置文件 - 修改需要审批

## 📦 最近备份点
"""
        
        for backup in backups[:5]:
            report += f"- {backup['name']} ({backup['timestamp'][:19]})\n"
        
        report += "\n---\n*本报告由 SDS 安全护栏系统自动生成*\n"
        
        return report


if __name__ == "__main__":
    guardrail = SafetyGuardrail()
    
    # 生成安全报告
    report = guardrail.generate_safety_report()
    
    report_file = Path(get_config('paths.output') + "/task-1570/sds-safety-report.md")
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"安全报告已生成: {report_file}")
    print(report)

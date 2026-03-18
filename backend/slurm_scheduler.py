#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLURM 作业调度模块

为 T109 项目提供 SLURM 作业提交、状态检查、取消等功能
支持 Gaussian/ORCA/PSI4 等计算化学软件

功能:
1. submit_job() - 提交 SLURM 作业
2. check_job_status() - 检查作业状态
3. cancel_job() - 取消作业
4. 生成 SLURM 脚本模板（支持 Gaussian/ORCA/PSI4）
5. 作业依赖和队列管理
6. 错误处理和重试机制

作者：Dudu (AI Assistant)
创建时间：2026-03-11
"""

import subprocess
import json
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from enum import Enum
import re
import shutil

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """作业状态枚举"""
    PENDING = "PENDING"  # 等待中
    RUNNING = "RUNNING"  # 运行中
    COMPLETED = "COMPLETED"  # 已完成
    FAILED = "FAILED"  # 失败
    CANCELLED = "CANCELLED"  # 已取消
    TIMEOUT = "TIMEOUT"  # 超时
    NODE_FAIL = "NODE_FAIL"  # 节点故障
    UNKNOWN = "UNKNOWN"  # 未知状态


class SoftwareType(Enum):
    """支持的软件类型"""
    GAUSSIAN = "gaussian"
    ORCA = "orca"
    PSI4 = "psi4"
    CUSTOM = "custom"


class SLURMScheduler:
    """
    SLURM 作业调度器
    
    提供完整的 SLURM 作业管理功能，包括提交、监控、取消等
    """
    
    def __init__(self, 
                 default_partition: str = "compute",
                 default_qos: Optional[str] = None,
                 max_retries: int = 3,
                 retry_delay: int = 60):
        """
        初始化 SLURM 调度器
        
        Args:
            default_partition: 默认分区名称
            default_qos: 默认 QoS (服务质量)
            max_retries: 最大重试次数
            retry_delay: 重试延迟 (秒)
        """
        self.default_partition = default_partition
        self.default_qos = default_qos
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # 作业历史记录
        self.job_history: Dict[str, Dict] = {}
        
        # 检查 SLURM 命令是否可用
        self._check_slurm_installation()
        
        logger.info(f"SLURM 调度器初始化完成 (分区：{default_partition})")
    
    def _check_slurm_installation(self) -> bool:
        """检查 SLURM 命令是否已安装"""
        required_commands = ['sbatch', 'squeue', 'scancel', 'scontrol', 'sacct']
        missing = []
        
        for cmd in required_commands:
            if not shutil.which(cmd):
                missing.append(cmd)
        
        if missing:
            logger.warning(f"SLURM 命令未完全安装，缺失：{', '.join(missing)}")
            logger.warning("请确保在 SLURM 集群环境中运行")
            return False
        
        logger.debug("SLURM 命令检查通过")
        return True
    
    def _run_command(self, command: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """
        运行 SLURM 命令
        
        Args:
            command: 命令列表
            timeout: 超时时间 (秒)
            
        Returns:
            CompletedProcess 对象
            
        Raises:
            subprocess.TimeoutExpired: 命令超时
            FileNotFoundError: 命令不存在
        """
        logger.debug(f"执行命令：{' '.join(command)}")
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=os.environ.copy()
            )
            
            if result.returncode != 0:
                logger.error(f"命令执行失败：{result.stderr}")
            
            return result
            
        except subprocess.TimeoutExpired:
            logger.error(f"命令超时：{' '.join(command)}")
            raise
        except FileNotFoundError as e:
            logger.error(f"命令未找到：{command[0]}")
            raise
    
    # ==================== 作业提交 ====================
    
    def submit_job(self,
                   script_path: str,
                   job_name: Optional[str] = None,
                   partition: Optional[str] = None,
                   nodes: int = 1,
                   ntasks_per_node: int = 1,
                   cpus_per_task: int = 1,
                   memory: Optional[str] = None,
                   time_limit: Optional[str] = None,
                   output_file: Optional[str] = None,
                   error_file: Optional[str] = None,
                   working_dir: Optional[str] = None,
                   dependencies: Optional[List[str]] = None,
                   qos: Optional[str] = None,
                   account: Optional[str] = None,
                   mail_user: Optional[str] = None,
                   mail_type: Optional[List[str]] = None,
                   custom_params: Optional[Dict[str, str]] = None,
                   dry_run: bool = False) -> Dict[str, Any]:
        """
        提交 SLURM 作业
        
        Args:
            script_path: SLURM 脚本路径
            job_name: 作业名称
            partition: 分区名称
            nodes: 节点数
            ntasks_per_node: 每节点任务数
            cpus_per_task: 每任务 CPU 数
            memory: 内存需求 (如 "4G", "8192M")
            time_limit: 时间限制 (格式："HH:MM:SS" 或 "D-HH:MM:SS")
            output_file: 标准输出文件
            error_file: 错误输出文件
            working_dir: 工作目录
            dependencies: 依赖作业 ID 列表
            qos: 服务质量
            account: 账户
            mail_user: 邮件通知用户
            mail_type: 邮件通知类型 (如 ["BEGIN", "END", "FAIL"])
            custom_params: 自定义参数
            dry_run: 是否仅生成脚本而不提交
            
        Returns:
            包含作业信息的字典：
            {
                'success': bool,
                'job_id': str or None,
                'message': str,
                'script_path': str,
                'submit_time': str
            }
        """
        try:
            # 验证脚本路径
            script_path = os.path.abspath(script_path)
            if not os.path.exists(script_path):
                return {
                    'success': False,
                    'job_id': None,
                    'message': f"脚本文件不存在：{script_path}",
                    'script_path': script_path,
                    'submit_time': datetime.now().isoformat()
                }
            
            # 构建 sbatch 命令
            sbatch_cmd = ['sbatch']
            
            # 作业名称
            if job_name:
                sbatch_cmd.extend(['--job-name', job_name])
            
            # 分区
            sbatch_cmd.extend(['--partition', partition or self.default_partition])
            
            # 资源需求
            sbatch_cmd.extend(['--nodes', str(nodes)])
            sbatch_cmd.extend(['--ntasks-per-node', str(ntasks_per_node)])
            sbatch_cmd.extend(['--cpus-per-task', str(cpus_per_task)])
            
            # 内存
            if memory:
                sbatch_cmd.extend(['--mem', memory])
            
            # 时间限制
            if time_limit:
                sbatch_cmd.extend(['--time', time_limit])
            
            # 输出文件
            if output_file:
                sbatch_cmd.extend(['--output', output_file])
            
            # 错误文件
            if error_file:
                sbatch_cmd.extend(['--error', error_file])
            
            # 工作目录
            if working_dir:
                sbatch_cmd.extend(['--chdir', working_dir])
            
            # 依赖关系
            if dependencies:
                dep_str = ':'.join(dependencies)
                sbatch_cmd.extend(['--dependency', f'afterok:{dep_str}'])
            
            # QoS
            if qos or self.default_qos:
                sbatch_cmd.extend(['--qos', qos or self.default_qos])
            
            # 账户
            if account:
                sbatch_cmd.extend(['--account', account])
            
            # 邮件通知
            if mail_user:
                sbatch_cmd.extend(['--mail-user', mail_user])
                if mail_type:
                    sbatch_cmd.extend(['--mail-type', ','.join(mail_type)])
            
            # 自定义参数
            if custom_params:
                for key, value in custom_params.items():
                    sbatch_cmd.extend([key, value])
            
            # 添加脚本路径
            sbatch_cmd.append(script_path)
            
            # Dry run 模式
            if dry_run:
                logger.info(f"[DRY RUN] 将执行：{' '.join(sbatch_cmd)}")
                return {
                    'success': True,
                    'job_id': None,
                    'message': f"DRY RUN - 将执行：{' '.join(sbatch_cmd)}",
                    'script_path': script_path,
                    'submit_time': datetime.now().isoformat(),
                    'command': ' '.join(sbatch_cmd)
                }
            
            # 执行提交
            logger.info(f"提交作业：{script_path}")
            result = self._run_command(sbatch_cmd, timeout=60)
            
            if result.returncode == 0:
                # 解析作业 ID
                job_id_match = re.search(r'Submitted batch job (\d+)', result.stdout)
                if job_id_match:
                    job_id = job_id_match.group(1)
                    
                    # 记录作业历史
                    self.job_history[job_id] = {
                        'script_path': script_path,
                        'job_name': job_name,
                        'submit_time': datetime.now().isoformat(),
                        'status': JobStatus.PENDING.value,
                        'resources': {
                            'nodes': nodes,
                            'cpus_per_task': cpus_per_task,
                            'memory': memory,
                            'time_limit': time_limit
                        }
                    }
                    
                    logger.info(f"作业提交成功：{job_id}")
                    return {
                        'success': True,
                        'job_id': job_id,
                        'message': f"作业 {job_id} 提交成功",
                        'script_path': script_path,
                        'submit_time': datetime.now().isoformat()
                    }
                else:
                    logger.error(f"无法解析作业 ID：{result.stdout}")
                    return {
                        'success': False,
                        'job_id': None,
                        'message': f"无法解析作业 ID：{result.stdout}",
                        'script_path': script_path,
                        'submit_time': datetime.now().isoformat()
                    }
            else:
                logger.error(f"作业提交失败：{result.stderr}")
                return {
                    'success': False,
                    'job_id': None,
                    'message': f"提交失败：{result.stderr}",
                    'script_path': script_path,
                    'submit_time': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"提交作业时发生异常：{str(e)}", exc_info=True)
            return {
                'success': False,
                'job_id': None,
                'message': f"异常：{str(e)}",
                'script_path': script_path,
                'submit_time': datetime.now().isoformat()
            }
    
    def submit_job_with_retry(self,
                              script_path: str,
                              **kwargs) -> Dict[str, Any]:
        """
        带重试机制的作业提交
        
        Args:
            script_path: SLURM 脚本路径
            **kwargs: 传递给 submit_job 的参数
            
        Returns:
            作业提交结果
        """
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            logger.info(f"尝试提交作业 (第 {attempt}/{self.max_retries} 次)")
            
            result = self.submit_job(script_path, **kwargs)
            
            if result['success']:
                logger.info(f"作业提交成功 (尝试 {attempt}/{self.max_retries})")
                result['retry_count'] = attempt
                return result
            
            last_error = result['message']
            
            if attempt < self.max_retries:
                logger.warning(f"提交失败，{self.retry_delay}秒后重试...")
                time.sleep(self.retry_delay)
        
        logger.error(f"作业提交失败，已尝试 {self.max_retries} 次")
        return {
            'success': False,
            'job_id': None,
            'message': f"多次重试后仍失败：{last_error}",
            'script_path': script_path,
            'submit_time': datetime.now().isoformat(),
            'retry_count': self.max_retries
        }
    
    # ==================== 作业状态检查 ====================
    
    def check_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        检查作业状态
        
        Args:
            job_id: 作业 ID
            
        Returns:
            作业状态信息：
            {
                'success': bool,
                'job_id': str,
                'status': JobStatus,
                'details': dict,
                'message': str
            }
        """
        try:
            # 使用 squeue 检查当前状态
            squeue_cmd = ['squeue', '-j', str(job_id), '-o', 
                         '%i|%j|%P|%T|%M|%N|%C']
            
            result = self._run_command(squeue_cmd, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                # 作业在队列中
                lines = result.stdout.strip().split('\n')
                
                # 跳过标题行
                for line in lines:
                    if '|' not in line or line.startswith('JOBID'):
                        continue
                    
                    parts = line.split('|')
                    if len(parts) >= 7:
                        status_str = parts[3].strip()
                        
                        # 解析状态
                        status = self._parse_slurm_status(status_str)
                        
                        return {
                            'success': True,
                            'job_id': job_id,
                            'status': status,
                            'details': {
                                'job_name': parts[1].strip(),
                                'partition': parts[2].strip(),
                                'status_raw': status_str,
                                'time': parts[4].strip(),
                                'node': parts[5].strip(),
                                'cpus': parts[6].strip()
                            },
                            'message': f"作业状态：{status.value}"
                        }
            
            # 作业不在队列中，使用 sacct 检查历史
            logger.debug(f"作业 {job_id} 不在队列中，检查历史记录...")
            return self._check_job_history(job_id)
            
        except Exception as e:
            logger.error(f"检查作业状态时发生异常：{str(e)}", exc_info=True)
            return {
                'success': False,
                'job_id': job_id,
                'status': JobStatus.UNKNOWN,
                'details': {},
                'message': f"异常：{str(e)}"
            }
    
    def _parse_slurm_status(self, status_str: str) -> JobStatus:
        """
        解析 SLURM 状态字符串
        
        Args:
            status_str: SLURM 状态字符串
            
        Returns:
            JobStatus 枚举值
        """
        status_map = {
            'PENDING': JobStatus.PENDING,
            'RUNNING': JobStatus.RUNNING,
            'COMPLETED': JobStatus.COMPLETED,
            'FAILED': JobStatus.FAILED,
            'CANCELLED': JobStatus.CANCELLED,
            'TIMEOUT': JobStatus.TIMEOUT,
            'NODE_FAIL': JobStatus.NODE_FAIL,
            'BOOT_FAIL': JobStatus.NODE_FAIL,
            'DEADLINE': JobStatus.TIMEOUT,
            'OUT_OF_MEMORY': JobStatus.FAILED,
        }
        
        # 处理带后缀的状态 (如 COMPLETED+)
        base_status = status_str.split('+')[0].strip()
        
        return status_map.get(base_status, JobStatus.UNKNOWN)
    
    def _check_job_history(self, job_id: str) -> Dict[str, Any]:
        """
        检查作业历史记录 (使用 sacct)
        
        Args:
            job_id: 作业 ID
            
        Returns:
            作业历史信息
        """
        try:
            sacct_cmd = ['sacct', '-j', str(job_id), '--format',
                        'JobID,JobName,State,ExitCode,Elapsed,Start,End',
                        '--noheader']
            
            result = self._run_command(sacct_cmd, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                
                # 取主作业 (不含 .batch 等子作业)
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 7 and parts[0] == str(job_id):
                        state = parts[2]
                        exit_code = parts[3]
                        
                        status = self._parse_slurm_status(state)
                        
                        # 判断是否成功
                        success = (status == JobStatus.COMPLETED and 
                                  exit_code == '0:0')
                        
                        return {
                            'success': True,
                            'job_id': job_id,
                            'status': status,
                            'details': {
                                'job_name': parts[1],
                                'state_raw': state,
                                'exit_code': exit_code,
                                'elapsed': parts[4],
                                'start': parts[5],
                                'end': parts[6],
                                'completed_successfully': success
                            },
                            'message': f"作业已完成，状态：{status.value}"
                        }
                
                return {
                    'success': True,
                    'job_id': job_id,
                    'status': JobStatus.UNKNOWN,
                    'details': {},
                    'message': "未找到作业历史记录"
                }
            else:
                return {
                    'success': True,
                    'job_id': job_id,
                    'status': JobStatus.UNKNOWN,
                    'details': {},
                    'message': "作业不存在或无历史记录"
                }
                
        except Exception as e:
            logger.error(f"检查作业历史时发生异常：{str(e)}")
            return {
                'success': False,
                'job_id': job_id,
                'status': JobStatus.UNKNOWN,
                'details': {},
                'message': f"异常：{str(e)}"
            }
    
    def check_multiple_jobs(self, job_ids: List[str]) -> Dict[str, Dict]:
        """
        批量检查多个作业状态
        
        Args:
            job_ids: 作业 ID 列表
            
        Returns:
            作业状态字典 {job_id: status_info}
        """
        results = {}
        
        for job_id in job_ids:
            results[job_id] = self.check_job_status(job_id)
        
        return results
    
    # ==================== 作业取消 ====================
    
    def cancel_job(self, job_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        取消作业
        
        Args:
            job_id: 作业 ID
            reason: 取消原因
            
        Returns:
            取消结果：
            {
                'success': bool,
                'job_id': str,
                'message': str
            }
        """
        try:
            # 构建 scancel 命令
            scancel_cmd = ['scancel', str(job_id)]
            
            # 添加原因 (如果提供)
            if reason:
                # 注意：scancel 本身不支持 reason 参数
                # 但我们可以记录日志
                logger.info(f"取消作业 {job_id}，原因：{reason}")
            
            logger.info(f"取消作业：{job_id}")
            result = self._run_command(scancel_cmd, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"作业 {job_id} 已成功取消")
                return {
                    'success': True,
                    'job_id': job_id,
                    'message': f"作业 {job_id} 已成功取消"
                }
            else:
                logger.error(f"取消作业失败：{result.stderr}")
                return {
                    'success': False,
                    'job_id': job_id,
                    'message': f"取消失败：{result.stderr}"
                }
                
        except Exception as e:
            logger.error(f"取消作业时发生异常：{str(e)}", exc_info=True)
            return {
                'success': False,
                'job_id': job_id,
                'message': f"异常：{str(e)}"
            }
    
    def cancel_multiple_jobs(self, job_ids: List[str]) -> Dict[str, Dict]:
        """
        批量取消多个作业
        
        Args:
            job_ids: 作业 ID 列表
            
        Returns:
            取消结果 {job_id: result}
        """
        results = {}
        
        for job_id in job_ids:
            results[job_id] = self.cancel_job(job_id)
        
        return results
    
    def cancel_jobs_by_name(self, job_name: str, user: Optional[str] = None) -> Dict[str, Any]:
        """
        根据作业名称取消作业
        
        Args:
            job_name: 作业名称
            user: 用户名 (可选，默认当前用户)
            
        Returns:
            取消结果
        """
        try:
            # 查找作业
            squeue_cmd = ['squeue', '--name', job_name, '-o', '%i']
            
            if user:
                squeue_cmd.extend(['--user', user])
            
            result = self._run_command(squeue_cmd, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                job_ids = [line.strip() for line in result.stdout.strip().split('\n') 
                          if line.strip().isdigit()]
                
                if not job_ids:
                    return {
                        'success': False,
                        'message': f"未找到作业：{job_name}",
                        'cancelled_count': 0
                    }
                
                # 批量取消
                cancel_results = self.cancel_multiple_jobs(job_ids)
                
                success_count = sum(1 for r in cancel_results.values() if r['success'])
                
                return {
                    'success': True,
                    'message': f"已取消 {success_count}/{len(job_ids)} 个作业",
                    'cancelled_count': success_count,
                    'total_found': len(job_ids),
                    'job_ids': job_ids,
                    'details': cancel_results
                }
            else:
                return {
                    'success': False,
                    'message': f"未找到作业：{job_name}",
                    'cancelled_count': 0
                }
                
        except Exception as e:
            logger.error(f"按名称取消作业时发生异常：{str(e)}")
            return {
                'success': False,
                'message': f"异常：{str(e)}",
                'cancelled_count': 0
            }
    
    # ==================== SLURM 脚本模板生成 ====================
    
    def generate_script_template(self,
                                 software: SoftwareType,
                                 input_file: str,
                                 output_file: Optional[str] = None,
                                 nodes: int = 1,
                                 cpus_per_task: int = 1,
                                 memory: str = "4G",
                                 time_limit: str = "24:00:00",
                                 partition: Optional[str] = None,
                                 job_name: Optional[str] = None,
                                 working_dir: Optional[str] = None,
                                 queue_type: str = "normal",
                                 additional_commands: Optional[List[str]] = None) -> str:
        """
        生成 SLURM 脚本模板
        
        Args:
            software: 软件类型 (Gaussian/ORCA/PSI4)
            input_file: 输入文件路径
            output_file: 输出文件路径
            nodes: 节点数
            cpus_per_task: 每任务 CPU 数
            memory: 内存需求
            time_limit: 时间限制
            partition: 分区
            job_name: 作业名称
            working_dir: 工作目录
            queue_type: 队列类型 ("normal", "high", "low")
            additional_commands: 额外命令
            
        Returns:
            SLURM 脚本内容
        """
        # 默认值
        if not job_name:
            job_name = Path(input_file).stem
        
        if not output_file:
            output_file = f"{job_name}.out"
        
        if not partition:
            partition = self.default_partition
        
        # SLURM 头部
        script_lines = [
            "#!/bin/bash",
            f"#SBATCH --job-name={job_name}",
            f"#SBATCH --partition={partition}",
            f"#SBATCH --nodes={nodes}",
            f"#SBATCH --ntasks-per-node=1",
            f"#SBATCH --cpus-per-task={cpus_per_task}",
            f"#SBATCH --mem={memory}",
            f"#SBATCH --time={time_limit}",
            f"#SBATCH --output={output_file}",
            f"#SBATCH --error={job_name}.err",
        ]
        
        # 根据队列类型添加 QoS
        if queue_type == "high":
            script_lines.append("#SBATCH --qos=high")
        elif queue_type == "low":
            script_lines.append("#SBATCH --qos=low")
        
        # 工作目录
        if working_dir:
            script_lines.append(f"#SBATCH --chdir={working_dir}")
            script_lines.append(f"cd {working_dir}")
        else:
            script_lines.append("cd $SLURM_SUBMIT_DIR")
        
        script_lines.append("")
        script_lines.append("# 加载模块")
        
        # 根据软件类型生成命令
        if software == SoftwareType.GAUSSIAN:
            script_lines.extend(self._generate_gaussian_commands(
                input_file, cpus_per_task, memory))
        elif software == SoftwareType.ORCA:
            script_lines.extend(self._generate_orca_commands(
                input_file, cpus_per_task))
        elif software == SoftwareType.PSI4:
            script_lines.extend(self._generate_psi4_commands(
                input_file, cpus_per_task))
        elif software == SoftwareType.CUSTOM:
            script_lines.append("# 自定义命令")
            script_lines.append("# 请在此处添加您的命令")
        
        # 添加额外命令
        if additional_commands:
            script_lines.append("")
            script_lines.append("# 额外命令")
            script_lines.extend(additional_commands)
        
        return '\n'.join(script_lines)
    
    def _generate_gaussian_commands(self, 
                                    input_file: str,
                                    cpus: int,
                                    memory: str) -> List[str]:
        """生成 Gaussian 计算命令"""
        # 解析内存
        mem_match = re.match(r'(\d+)([GMK]?)', memory, re.IGNORECASE)
        if mem_match:
            mem_value = int(mem_match.group(1))
            mem_unit = mem_match.group(2).upper()
            
            if mem_unit == 'G':
                mem_mb = mem_value * 1024
            elif mem_unit == 'M':
                mem_mb = mem_value
            else:
                mem_mb = 4000  # 默认
        else:
            mem_mb = 4000
        
        return [
            "# Gaussian 模块",
            "module load gaussian  # 根据实际环境调整",
            "",
            "# 设置 Gaussian 环境变量",
            f"export GAUSSIAN_CPUS={cpus}",
            f"export GAUSSIAN_MEM={mem_mb}MB",
            "",
            "# 运行 Gaussian",
            f"g16 < {input_file}",
        ]
    
    def _generate_orca_commands(self,
                                input_file: str,
                                cpus: int) -> List[str]:
        """生成 ORCA 计算命令"""
        return [
            "# ORCA 模块",
            "module load orca  # 根据实际环境调整",
            "",
            "# 运行 ORCA",
            f"orca {input_file} --nt {cpus}",
        ]
    
    def _generate_psi4_commands(self,
                                input_file: str,
                                cpus: int) -> List[str]:
        """生成 PSI4 计算命令"""
        return [
            "# PSI4 模块",
            "module load psi4  # 根据实际环境调整",
            "",
            "# 运行 PSI4",
            f"psi4 --nthread {cpus} {input_file}",
        ]
    
    def save_script_template(self,
                            script_content: str,
                            output_path: str,
                            make_executable: bool = True) -> Dict[str, Any]:
        """
        保存 SLURM 脚本模板到文件
        
        Args:
            script_content: 脚本内容
            output_path: 输出路径
            make_executable: 是否设置为可执行
            
        Returns:
            保存结果
        """
        try:
            # 创建目录 (如果需要)
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # 写入文件
            with open(output_path, 'w') as f:
                f.write(script_content)
            
            # 设置可执行权限
            if make_executable:
                os.chmod(output_path, 0o755)
            
            logger.info(f"脚本已保存：{output_path}")
            
            return {
                'success': True,
                'path': output_path,
                'message': f"脚本已保存到 {output_path}"
            }
            
        except Exception as e:
            logger.error(f"保存脚本时发生异常：{str(e)}")
            return {
                'success': False,
                'path': output_path,
                'message': f"保存失败：{str(e)}"
            }
    
    # ==================== 队列管理 ====================
    
    def get_queue_info(self, partition: Optional[str] = None) -> Dict[str, Any]:
        """
        获取队列信息
        
        Args:
            partition: 分区名称 (可选)
            
        Returns:
            队列信息
        """
        try:
            sinfo_cmd = ['sinfo', '-o', '%P|%N|%T|%D|%C|%m|%f']
            
            if partition:
                sinfo_cmd = ['sinfo', '-p', partition, '-o', '%P|%N|%T|%D|%C|%m|%f']
            
            result = self._run_command(sinfo_cmd, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                
                partitions = []
                for line in lines:
                    if '|' not in line or line.startswith('PARTITION'):
                        continue
                    
                    parts = line.split('|')
                    if len(parts) >= 7:
                        partitions.append({
                            'name': parts[0].strip(),
                            'nodes': parts[1].strip(),
                            'state': parts[2].strip(),
                            'slurm_nodes': parts[3].strip(),
                            'cpus': parts[4].strip(),
                            'memory': parts[5].strip(),
                            'features': parts[6].strip()
                        })
                
                return {
                    'success': True,
                    'partitions': partitions,
                    'message': f"获取到 {len(partitions)} 个分区信息"
                }
            else:
                return {
                    'success': False,
                    'partitions': [],
                    'message': f"获取队列信息失败：{result.stderr}"
                }
                
        except Exception as e:
            logger.error(f"获取队列信息时发生异常：{str(e)}")
            return {
                'success': False,
                'partitions': [],
                'message': f"异常：{str(e)}"
            }
    
    def get_user_jobs(self, user: Optional[str] = None) -> List[Dict]:
        """
        获取用户作业列表
        
        Args:
            user: 用户名 (可选，默认当前用户)
            
        Returns:
            作业列表
        """
        try:
            squeue_cmd = ['squeue', '-o', 
                         '%i|%j|%P|%T|%M|%N|%C|%u', '--noheader']
            
            if user:
                squeue_cmd.extend(['--user', user])
            
            result = self._run_command(squeue_cmd, timeout=30)
            
            jobs = []
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                
                for line in lines:
                    if '|' not in line:
                        continue
                    
                    parts = line.split('|')
                    if len(parts) >= 8:
                        jobs.append({
                            'job_id': parts[0].strip(),
                            'job_name': parts[1].strip(),
                            'partition': parts[2].strip(),
                            'status': parts[3].strip(),
                            'time': parts[4].strip(),
                            'node': parts[5].strip(),
                            'cpus': parts[6].strip(),
                            'user': parts[7].strip()
                        })
            
            return jobs
            
        except Exception as e:
            logger.error(f"获取用户作业列表时发生异常：{str(e)}")
            return []
    
    # ==================== 作业依赖管理 ====================
    
    def submit_dependent_job(self,
                            script_path: str,
                            dependency_job_ids: List[str],
                            dependency_type: str = "afterok",
                            **kwargs) -> Dict[str, Any]:
        """
        提交依赖作业
        
        Args:
            script_path: SLURM 脚本路径
            dependency_job_ids: 依赖作业 ID 列表
            dependency_type: 依赖类型
                - "afterok": 依赖作业成功后执行
                - "afternotok": 依赖作业失败后执行
                - "after": 依赖作业完成后执行 (无论成功失败)
                - "afterany": 依赖作业任意状态后执行
            **kwargs: 传递给 submit_job 的参数
            
        Returns:
            作业提交结果
        """
        # 验证依赖作业状态
        valid_deps = []
        for dep_id in dependency_job_ids:
            status_info = self.check_job_status(dep_id)
            
            if status_info['success']:
                if dependency_type == "afterok":
                    # 只依赖成功的作业
                    if status_info['status'] == JobStatus.COMPLETED:
                        valid_deps.append(dep_id)
                    else:
                        logger.warning(f"依赖作业 {dep_id} 尚未完成，状态：{status_info['status'].value}")
                else:
                    valid_deps.append(dep_id)
            else:
                logger.warning(f"依赖作业 {dep_id} 状态检查失败")
        
        if not valid_deps and dependency_job_ids:
            return {
                'success': False,
                'job_id': None,
                'message': "没有有效的依赖作业",
                'script_path': script_path,
                'submit_time': datetime.now().isoformat()
            }
        
        # 构建依赖字符串
        dep_str = ':'.join(valid_deps)
        dependency = f"{dependency_type}:{dep_str}"
        
        # 添加到 custom_params
        if 'custom_params' not in kwargs:
            kwargs['custom_params'] = {}
        
        kwargs['custom_params']['--dependency'] = dependency
        
        # 提交作业
        return self.submit_job(script_path, **kwargs)
    
    def create_job_chain(self,
                        scripts: List[Dict]) -> Dict[str, Any]:
        """
        创建作业链 (顺序执行)
        
        Args:
            scripts: 脚本列表，每个元素包含：
                {
                    'script_path': str,
                    'job_name': str,
                    ...其他 submit_job 参数
                }
            
        Returns:
            作业链信息：
            {
                'success': bool,
                'job_ids': List[str],
                'message': str
            }
        """
        if not scripts:
            return {
                'success': False,
                'job_ids': [],
                'message': "脚本列表为空"
            }
        
        job_ids = []
        prev_job_id = None
        
        for i, script_info in enumerate(scripts):
            script_path = script_info.get('script_path')
            if not script_path:
                logger.error(f"第 {i+1} 个脚本缺少 script_path")
                continue
            
            # 设置依赖
            if prev_job_id:
                script_info['dependencies'] = [prev_job_id]
            
            # 提交作业
            result = self.submit_job(script_path, **script_info)
            
            if result['success']:
                job_ids.append(result['job_id'])
                prev_job_id = result['job_id']
                logger.info(f"作业链 {i+1}/{len(scripts)}: {result['job_id']} 提交成功")
            else:
                logger.error(f"作业链 {i+1}/{len(scripts)} 提交失败：{result['message']}")
                return {
                    'success': False,
                    'job_ids': job_ids,
                    'message': f"作业链在第 {i+1} 步失败：{result['message']}",
                    'failed_at': i
                }
        
        return {
            'success': True,
            'job_ids': job_ids,
            'message': f"作业链创建成功，共 {len(job_ids)} 个作业"
        }
    
    # ==================== 工具函数 ====================
    
    def wait_for_job(self,
                    job_id: str,
                    interval: int = 30,
                    timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        等待作业完成
        
        Args:
            job_id: 作业 ID
            interval: 检查间隔 (秒)
            timeout: 超时时间 (秒，None 表示不超时)
            
        Returns:
            最终作业状态
        """
        start_time = time.time()
        
        logger.info(f"开始等待作业 {job_id} 完成...")
        
        while True:
            # 检查超时
            if timeout and (time.time() - start_time) > timeout:
                logger.error(f"等待作业 {job_id} 超时")
                return {
                    'success': False,
                    'job_id': job_id,
                    'status': JobStatus.TIMEOUT,
                    'message': f"等待超时 ({timeout}秒)"
                }
            
            # 检查状态
            status_info = self.check_job_status(job_id)
            
            if not status_info['success']:
                logger.error(f"检查作业状态失败：{status_info['message']}")
                return status_info
            
            current_status = status_info['status']
            
            # 检查是否完成
            if current_status in [JobStatus.COMPLETED, JobStatus.FAILED, 
                                 JobStatus.CANCELLED, JobStatus.TIMEOUT,
                                 JobStatus.NODE_FAIL]:
                logger.info(f"作业 {job_id} 完成，状态：{current_status.value}")
                return status_info
            
            # 等待
            logger.debug(f"作业 {job_id} 当前状态：{current_status.value}, 继续等待...")
            time.sleep(interval)
    
    def get_job_statistics(self, 
                          job_ids: Optional[List[str]] = None,
                          user: Optional[str] = None,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取作业统计信息
        
        Args:
            job_ids: 作业 ID 列表 (可选)
            user: 用户名 (可选)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            统计信息
        """
        try:
            sacct_cmd = ['sacct', '--format',
                        'JobID,JobName,State,Elapsed,Start,End,MaxRSS,NCPU',
                        '--noheader']
            
            if job_ids:
                sacct_cmd.extend(['-j', ','.join(job_ids)])
            
            if user:
                sacct_cmd.extend(['--user', user])
            
            if start_date:
                sacct_cmd.extend(['-S', start_date])
            
            if end_date:
                sacct_cmd.extend(['-E', end_date])
            
            result = self._run_command(sacct_cmd, timeout=60)
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                
                stats = {
                    'total_jobs': 0,
                    'completed': 0,
                    'failed': 0,
                    'cancelled': 0,
                    'pending': 0,
                    'running': 0,
                    'total_cpu_time': 0,
                    'avg_cpu_time': 0,
                }
                
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 6:
                        stats['total_jobs'] += 1
                        
                        state = parts[2]
                        if state == 'COMPLETED':
                            stats['completed'] += 1
                        elif state in ['FAILED', 'TIMEOUT', 'NODE_FAIL']:
                            stats['failed'] += 1
                        elif state == 'CANCELLED':
                            stats['cancelled'] += 1
                        elif state == 'PENDING':
                            stats['pending'] += 1
                        elif state == 'RUNNING':
                            stats['running'] += 1
                
                # 计算成功率
                if stats['total_jobs'] > 0:
                    stats['success_rate'] = (stats['completed'] / stats['total_jobs']) * 100
                else:
                    stats['success_rate'] = 0
                
                return {
                    'success': True,
                    'statistics': stats,
                    'message': f"统计了 {stats['total_jobs']} 个作业"
                }
            else:
                return {
                    'success': True,
                    'statistics': {},
                    'message': "无作业数据"
                }
                
        except Exception as e:
            logger.error(f"获取作业统计时发生异常：{str(e)}")
            return {
                'success': False,
                'statistics': {},
                'message': f"异常：{str(e)}"
            }


# ==================== 便捷函数 ====================

def submit_job(script_path: str, **kwargs) -> Dict[str, Any]:
    """
    便捷函数：提交 SLURM 作业
    
    Args:
        script_path: SLURM 脚本路径
        **kwargs: 传递给 SLURMScheduler.submit_job 的参数
        
    Returns:
        作业提交结果
    """
    scheduler = SLURMScheduler()
    return scheduler.submit_job(script_path, **kwargs)


def check_job_status(job_id: str) -> Dict[str, Any]:
    """
    便捷函数：检查作业状态
    
    Args:
        job_id: 作业 ID
        
    Returns:
        作业状态信息
    """
    scheduler = SLURMScheduler()
    return scheduler.check_job_status(job_id)


def cancel_job(job_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """
    便捷函数：取消作业
    
    Args:
        job_id: 作业 ID
        reason: 取消原因
        
    Returns:
        取消结果
    """
    scheduler = SLURMScheduler()
    return scheduler.cancel_job(job_id, reason)


def generate_gaussian_script(input_file: str, **kwargs) -> str:
    """
    便捷函数：生成 Gaussian SLURM 脚本
    
    Args:
        input_file: Gaussian 输入文件
        **kwargs: 传递给 generate_script_template 的参数
        
    Returns:
        SLURM 脚本内容
    """
    scheduler = SLURMScheduler()
    return scheduler.generate_script_template(
        SoftwareType.GAUSSIAN, input_file, **kwargs
    )


def generate_orca_script(input_file: str, **kwargs) -> str:
    """
    便捷函数：生成 ORCA SLURM 脚本
    
    Args:
        input_file: ORCA 输入文件
        **kwargs: 传递给 generate_script_template 的参数
        
    Returns:
        SLURM 脚本内容
    """
    scheduler = SLURMScheduler()
    return scheduler.generate_script_template(
        SoftwareType.ORCA, input_file, **kwargs
    )


def generate_psi4_script(input_file: str, **kwargs) -> str:
    """
    便捷函数：生成 PSI4 SLURM 脚本
    
    Args:
        input_file: PSI4 输入文件
        **kwargs: 传递给 generate_script_template 的参数
        
    Returns:
        SLURM 脚本内容
    """
    scheduler = SLURMScheduler()
    return scheduler.generate_script_template(
        SoftwareType.PSI4, input_file, **kwargs
    )


# ==================== 示例用法 ====================

if __name__ == "__main__":
    # 示例：创建调度器
    scheduler = SLURMScheduler(default_partition="compute")
    
    # 示例：生成 Gaussian 脚本
    gaussian_script = scheduler.generate_script_template(
        software=SoftwareType.GAUSSIAN,
        input_file="molecule.com",
        job_name="gaussian_test",
        nodes=1,
        cpus_per_task=8,
        memory="16G",
        time_limit="12:00:00"
    )
    
    print("=== Gaussian SLURM 脚本模板 ===")
    print(gaussian_script)
    print()
    
    # 示例：生成 ORCA 脚本
    orca_script = scheduler.generate_script_template(
        software=SoftwareType.ORCA,
        input_file="molecule.inp",
        job_name="orca_test",
        nodes=1,
        cpus_per_task=4,
        memory="8G"
    )
    
    print("=== ORCA SLURM 脚本模板 ===")
    print(orca_script)
    print()
    
    # 示例：生成 PSI4 脚本
    psi4_script = scheduler.generate_script_template(
        software=SoftwareType.PSI4,
        input_file="molecule.py",
        job_name="psi4_test",
        nodes=1,
        cpus_per_task=16,
        memory="32G"
    )
    
    print("=== PSI4 SLURM 脚本模板 ===")
    print(psi4_script)
    print()
    
    # 示例：提交作业 (需要在 SLURM 环境中)
    # result = scheduler.submit_job(
    #     script_path="test_job.sh",
    #     job_name="test",
    #     nodes=1,
    #     cpus_per_task=4,
    #     memory="8G",
    #     time_limit="01:00:00"
    # )
    # print(f"提交结果：{result}")
    
    # 示例：检查作业状态
    # status = scheduler.check_job_status("12345")
    # print(f"作业状态：{status}")
    
    # 示例：取消作业
    # cancel_result = scheduler.cancel_job("12345")
    # print(f"取消结果：{cancel_result}")

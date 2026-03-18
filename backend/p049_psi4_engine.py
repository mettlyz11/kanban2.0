#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P049-T0-1: PSI4计算引擎生产级完善

核心组件:
1. EngineAdapter - 引擎适配器基类
2. PSI4Adapter - PSI4引擎适配器实现
3. OutputParsers - 输出解析器（能量、几何、频率）
4. ErrorHandling - 错误处理和重试机制
5. Performance - 性能优化（并行、内存）

作者: OpenClaw Subagent
创建时间: 2026-03-11
"""

import os
import re
import json
import time
import shutil
import logging
import tempfile
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
from enum import Enum
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import threading
from collections import defaultdict
import hashlib

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== 数据模型 ====================

class CalculationType(Enum):
    """计算类型"""
    SINGLE_POINT = "single_point"
    GEOMETRY_OPTIMIZATION = "geometry_optimization"
    FREQUENCY = "frequency"
    TRANSITION_STATE = "transition_state"
    IRC = "irc"
    SCAN = "scan"


class CalculationStatus(Enum):
    """计算状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class CalculationResult:
    """计算结果数据类"""
    # 基本信息
    success: bool = False
    status: CalculationStatus = CalculationStatus.PENDING
    error_message: str = ""
    
    # 能量信息
    total_energy: Optional[float] = None
    scf_energy: Optional[float] = None
    correlation_energy: Optional[float] = None
    
    # 几何信息
    final_geometry: Optional[List[Dict[str, Any]]] = None
    initial_geometry: Optional[List[Dict[str, Any]]] = None
    
    # 频率信息
    frequencies: Optional[List[float]] = None
    normal_modes: Optional[List[List[float]]] = None
    ir_intensities: Optional[List[float]] = None
    raman_activities: Optional[List[float]] = None
    zero_point_energy: Optional[float] = None
    thermal_correction: Optional[float] = None
    entropy: Optional[float] = None
    
    # Hessian信息
    hessian_matrix: Optional[List[List[float]]] = None
    
    # 收敛信息
    converged: bool = False
    scf_converged: bool = False
    geometry_converged: bool = False
    n_iterations: int = 0
    
    # 性能信息
    wall_time: float = 0.0
    cpu_time: float = 0.0
    memory_used_mb: float = 0.0
    
    # 原始输出
    raw_output: str = ""
    output_file: str = ""
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=indent, default=str)


@dataclass
class CalculationConfig:
    """计算配置"""
    # 分子信息
    charge: int = 0
    multiplicity: int = 1
    geometry: str = ""  # XYZ格式或Z-matrix
    
    # 方法参数
    method: str = "B3LYP"
    basis: str = "6-31G(d)"
    
    # 计算类型
    calculation_type: CalculationType = CalculationType.SINGLE_POINT
    
    # SCF参数
    scf_type: str = "DF"  # DF, DIRECT, PK, OUT_OF_CORE, MEM_DF
    scf_convergence: float = 1e-6
    max_scf_iterations: int = 100
    guess: str = "SAD"  # SAD, CORE, GWH, READ
    
    # 几何优化参数
    opt_type: str = "MIN"  # MIN, TS, IRC
    opt_convergence: str = "GAU_TIGHT"  # GAU_LOOSE, GAU, GAU_TIGHT
    max_opt_cycles: int = 50
    
    # 频率参数
    temperature: float = 298.15
    pressure: float = 101325.0  # Pa
    
    # 溶剂参数
    solvent: Optional[str] = None
    solvent_model: str = "PCM"  # PCM, CPCM, SMD
    
    # 资源参数
    memory: str = "4 GB"
    num_threads: int = 4
    
    # PSI4特定参数
    psi4_options: Dict[str, Any] = field(default_factory=dict)
    
    # 重试参数
    max_retries: int = 3
    retry_delay: float = 5.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['calculation_type'] = self.calculation_type.value
        return data


# ==================== 异常类 ====================

class EngineError(Exception):
    """引擎错误基类"""
    pass


class CalculationError(EngineError):
    """计算错误"""
    def __init__(self, message: str, error_type: str = "unknown", 
                 recoverable: bool = False, suggestions: List[str] = None):
        super().__init__(message)
        self.error_type = error_type
        self.recoverable = recoverable
        self.suggestions = suggestions or []


class SCFConvergenceError(CalculationError):
    """SCF不收敛错误"""
    def __init__(self, message: str, last_energy: float = None, 
                 n_iterations: int = 0):
        super().__init__(
            message, 
            error_type="scf_convergence",
            recoverable=True,
            suggestions=[
                "尝试不同的初始猜测 (GWH, READ)",
                "增加SCF迭代次数",
                "使用更小的基组",
                "尝试不同的SCF算法 (DIIS, SOSCF)",
                "检查分子几何结构"
            ]
        )
        self.last_energy = last_energy
        self.n_iterations = n_iterations


class GeometryConvergenceError(CalculationError):
    """几何优化不收敛错误"""
    def __init__(self, message: str, max_cycles: int = 0):
        super().__init__(
            message,
            error_type="geometry_convergence",
            recoverable=True,
            suggestions=[
                "增加最大优化循环次数",
                "放松收敛标准",
                "检查初始几何结构",
                "尝试不同的优化算法"
            ]
        )
        self.max_cycles = max_cycles


class ResourceError(EngineError):
    """资源错误"""
    pass


class TimeoutError(EngineError):
    """超时错误"""
    pass


# ==================== 引擎适配器基类 ====================

class EngineAdapter(ABC):
    """
    量子化学计算引擎适配器基类
    
    设计原则:
    1. 统一的接口抽象
    2. 支持异步执行
    3. 内置错误处理和重试
    4. 性能监控和优化
    """
    
    def __init__(self, name: str, version: str = "unknown"):
        self.name = name
        self.version = version
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._executor = None
        self._lock = threading.RLock()
        
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        pass
    
    @abstractmethod
    def validate_config(self, config: CalculationConfig) -> Tuple[bool, List[str]]:
        """
        验证计算配置
        
        Returns:
            (是否有效, 错误信息列表)
        """
        pass
    
    @abstractmethod
    def generate_input(self, config: CalculationConfig, 
                       work_dir: str) -> str:
        """
        生成输入文件
        
        Args:
            config: 计算配置
            work_dir: 工作目录
            
        Returns:
            输入文件路径
        """
        pass
    
    @abstractmethod
    def execute(self, input_file: str, work_dir: str,
                timeout: Optional[int] = None) -> Tuple[int, str, str]:
        """
        执行计算
        
        Args:
            input_file: 输入文件路径
            work_dir: 工作目录
            timeout: 超时时间（秒）
            
        Returns:
            (返回码, 标准输出, 标准错误)
        """
        pass
    
    @abstractmethod
    def parse_output(self, output_file: str, 
                     config: CalculationConfig) -> CalculationResult:
        """
        解析输出文件
        
        Args:
            output_file: 输出文件路径
            config: 计算配置
            
        Returns:
            计算结果
        """
        pass
    
    def run_calculation(self, config: CalculationConfig,
                       work_dir: Optional[str] = None,
                       timeout: Optional[int] = None) -> CalculationResult:
        """
        运行完整计算流程
        
        Args:
            config: 计算配置
            work_dir: 工作目录（可选）
            timeout: 超时时间（秒）
            
        Returns:
            计算结果
        """
        start_time = time.time()
        
        # 验证配置
        valid, errors = self.validate_config(config)
        if not valid:
            return CalculationResult(
                success=False,
                status=CalculationStatus.FAILED,
                error_message=f"配置验证失败: {'; '.join(errors)}"
            )
        
        # 创建工作目录
        if work_dir is None:
            work_dir = tempfile.mkdtemp(prefix=f"{self.name.lower()}_")
        else:
            os.makedirs(work_dir, exist_ok=True)
        
        self.logger.info(f"开始计算: {config.calculation_type.value} "
                        f"in {work_dir}")
        
        try:
            # 生成输入文件
            input_file = self.generate_input(config, work_dir)
            self.logger.debug(f"输入文件: {input_file}")
            
            # 执行计算
            returncode, stdout, stderr = self.execute(
                input_file, work_dir, timeout
            )
            
            # 解析输出
            output_file = os.path.join(work_dir, "output.dat")
            result = self.parse_output(output_file, config)
            
            # 更新结果信息
            result.wall_time = time.time() - start_time
            result.raw_output = stdout + "\n" + stderr
            result.output_file = output_file
            
            if returncode != 0 and result.success:
                result.success = False
                result.status = CalculationStatus.FAILED
                result.error_message = f"进程返回非零代码: {returncode}"
            
            return result
            
        except CalculationError as e:
            self.logger.error(f"计算错误: {e}")
            return CalculationResult(
                success=False,
                status=CalculationStatus.FAILED,
                error_message=str(e),
                metadata={"error_type": e.error_type, "recoverable": e.recoverable}
            )
        except Exception as e:
            self.logger.exception("计算执行失败")
            return CalculationResult(
                success=False,
                status=CalculationStatus.FAILED,
                error_message=f"执行错误: {str(e)}"
            )
    
    def run_with_retry(self, config: CalculationConfig,
                      work_dir: Optional[str] = None,
                      timeout: Optional[int] = None,
                      max_retries: Optional[int] = None) -> CalculationResult:
        """
        带重试机制的计算执行
        
        Args:
            config: 计算配置
            work_dir: 工作目录
            timeout: 超时时间
            max_retries: 最大重试次数
            
        Returns:
            计算结果
        """
        if max_retries is None:
            max_retries = config.max_retries
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            self.logger.info(f"计算尝试 {attempt + 1}/{max_retries + 1}")
            
            result = self.run_calculation(config, work_dir, timeout)
            
            if result.success:
                if attempt > 0:
                    result.metadata["retry_count"] = attempt
                    result.metadata["recovered_from_error"] = True
                return result
            
            last_error = result.error_message
            
            # 检查是否可以重试
            if attempt < max_retries:
                # 尝试自动修复配置
                config = self._auto_fix_config(config, result)
                
                self.logger.info(f"等待 {config.retry_delay} 秒后重试...")
                time.sleep(config.retry_delay)
        
        # 所有重试都失败
        result.error_message = f"经过 {max_retries + 1} 次尝试后失败: {last_error}"
        return result
    
    def _auto_fix_config(self, config: CalculationConfig, 
                         failed_result: CalculationResult) -> CalculationConfig:
        """
        自动修复配置以处理常见错误
        
        Args:
            config: 当前配置
            failed_result: 失败的计算结果
            
        Returns:
            修复后的配置
        """
        error_msg = failed_result.error_message.lower()
        
        # SCF不收敛 - 尝试不同的初始猜测
        if "scf" in error_msg and ("not converge" in error_msg or "convergence" in error_msg):
            self.logger.info("检测到SCF不收敛，调整初始猜测...")
            
            guess_cycle = ["SAD", "GWH", "CORE"]
            current_guess = config.guess
            
            if current_guess in guess_cycle:
                idx = guess_cycle.index(current_guess)
                if idx < len(guess_cycle) - 1:
                    config.guess = guess_cycle[idx + 1]
                    config.max_scf_iterations = min(config.max_scf_iterations * 2, 500)
        
        # 几何优化不收敛
        elif "opt" in error_msg and "not converge" in error_msg:
            self.logger.info("检测到几何优化不收敛，增加迭代次数...")
            config.max_opt_cycles = min(config.max_opt_cycles + 50, 500)
        
        # 内存不足
        elif "memory" in error_msg or "allocat" in error_msg:
            self.logger.info("检测到内存问题，调整SCF类型...")
            if config.scf_type == "PK":
                config.scf_type = "DF"
            elif config.scf_type == "DF":
                config.scf_type = "OUT_OF_CORE"
        
        return config
    
    def run_parallel(self, configs: List[CalculationConfig],
                    work_dir: Optional[str] = None,
                    max_workers: Optional[int] = None) -> List[CalculationResult]:
        """
        并行执行多个计算
        
        Args:
            configs: 计算配置列表
            work_dir: 基础工作目录
            max_workers: 最大并行数
            
        Returns:
            计算结果列表
        """
        if max_workers is None:
            max_workers = min(len(configs), os.cpu_count() or 4)
        
        self.logger.info(f"并行执行 {len(configs)} 个计算，使用 {max_workers} 个worker")
        
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for i, config in enumerate(configs):
                if work_dir:
                    job_dir = os.path.join(work_dir, f"job_{i:04d}")
                else:
                    job_dir = None
                
                future = executor.submit(
                    self.run_with_retry, config, job_dir
                )
                futures.append(future)
            
            for future in futures:
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"并行计算失败: {e}")
                    results.append(CalculationResult(
                        success=False,
                        status=CalculationStatus.FAILED,
                        error_message=str(e)
                    ))
        
        return results
    
    def get_version_info(self) -> Dict[str, str]:
        """获取引擎版本信息"""
        return {
            "name": self.name,
            "version": self.version,
            "available": str(self.is_available)
        }


# ==================== PSI4输出解析器 ====================

class PSI4OutputParser:
    """
    PSI4输出文件解析器
    
    支持解析:
    - 能量信息 (SCF, MP2, CCSD, etc.)
    - 几何结构 (初始和最终)
    - 频率和Hessian
    - 收敛信息
    - 性能统计
    """
    
    def __init__(self):
        self.logger = logging.getLogger("PSI4OutputParser")
    
    def parse(self, output_file: str, 
              config: CalculationConfig) -> CalculationResult:
        """
        解析PSI4输出文件
        
        Args:
            output_file: 输出文件路径
            config: 计算配置
            
        Returns:
            计算结果
        """
        result = CalculationResult(
            status=CalculationStatus.RUNNING,
            output_file=output_file
        )
        
        if not os.path.exists(output_file):
            result.status = CalculationStatus.FAILED
            result.error_message = f"输出文件不存在: {output_file}"
            return result
        
        try:
            with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            result.raw_output = content
            
            # 解析能量
            self._parse_energies(content, result)
            
            # 解析几何结构
            self._parse_geometries(content, result)
            
            # 解析频率
            self._parse_frequencies(content, result)
            
            # 解析收敛信息
            self._parse_convergence(content, result)
            
            # 解析性能信息
            self._parse_performance(content, result)
            
            # 检查错误
            self._check_errors(content, result)
            
            # 确定最终状态
            if result.error_message:
                result.status = CalculationStatus.FAILED
                result.success = False
            else:
                result.status = CalculationStatus.COMPLETED
                result.success = True
            
            return result
            
        except Exception as e:
            self.logger.exception("解析输出文件失败")
            result.status = CalculationStatus.FAILED
            result.error_message = f"解析错误: {str(e)}"
            return result
    
    def _parse_energies(self, content: str, result: CalculationResult):
        """解析能量信息"""
        # SCF能量
        scf_patterns = [
            r'@DF-RHF Final Energy:\s+([-\d.]+)',
            r'@DF-RKS Final Energy:\s+([-\d.]+)',
            r'@RHF Final Energy:\s+([-\d.]+)',
            r'@RKS Final Energy:\s+([-\d.]+)',
            r'@UHF Final Energy:\s+([-\d.]+)',
            r'@UKS Final Energy:\s+([-\d.]+)',
            r'@DF-UHF Final Energy:\s+([-\d.]+)',
            r'@DF-UKS Final Energy:\s+([-\d.]+)',
            r'Total Energy =\s+([-\d.]+)',
            r'Final energy is\s+([-\d.]+)',
        ]
        
        for pattern in scf_patterns:
            match = re.search(pattern, content)
            if match:
                result.scf_energy = float(match.group(1))
                result.total_energy = result.scf_energy
                break
        
        # 相关能 (MP2, CCSD, etc.)
        correlation_patterns = [
            (r'\*\s+MP2 total energy\s+=\s+([-\d.]+)', 'MP2'),
            (r'\*\s+CCSD total energy\s+=\s+([-\d.]+)', 'CCSD'),
            (r'\*\s+CCSD\(T\) total energy\s+=\s+([-\d.]+)', 'CCSD(T)'),
        ]
        
        for pattern, method in correlation_patterns:
            match = re.search(pattern, content)
            if match:
                result.total_energy = float(match.group(1))
                if result.scf_energy:
                    result.correlation_energy = result.total_energy - result.scf_energy
                result.metadata['correlation_method'] = method
                break
    
    def _parse_geometries(self, content: str, result: CalculationResult):
        """解析几何结构"""
        # 初始几何
        initial_geom_match = re.search(
            r'Molecular geometry.*?-+\s*\n(.*?)\n.*?-',
            content, re.DOTALL
        )
        if initial_geom_match:
            result.initial_geometry = self._parse_xyz_block(
                initial_geom_match.group(1)
            )
        
        # 最终几何 (优化后)
        final_geom_patterns = [
            r'Optimized Geometry.*?-+\s*\n(.*?)\n.*?-',
            r'Final \(Optimization\) Molecular Geometry.*?-+\s*\n(.*?)\n.*?-',
            r'Cartesian Geometry \(in Angstrom\).*?-+\s*\n(.*?)\n.*?-',
        ]
        
        for pattern in final_geom_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                result.final_geometry = self._parse_xyz_block(
                    match.group(1)
                )
                break
        
        # 如果没有找到最终几何，尝试从分子坐标部分提取
        if not result.final_geometry:
            coord_match = re.search(
                r'Coordinates \(Cartesian, in Angstrom\).*?-+\s*\n(.*?)\n.*?-',
                content, re.DOTALL
            )
            if coord_match:
                result.final_geometry = self._parse_xyz_block(
                    coord_match.group(1)
                )
    
    def _parse_xyz_block(self, block: str) -> List[Dict[str, Any]]:
        """解析XYZ格式的坐标块"""
        atoms = []
        lines = block.strip().split('\n')
        
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 4:
                try:
                    atom = {
                        'symbol': parts[0],
                        'x': float(parts[1]),
                        'y': float(parts[2]),
                        'z': float(parts[3])
                    }
                    atoms.append(atom)
                except (ValueError, IndexError):
                    continue
        
        return atoms
    
    def _parse_frequencies(self, content: str, result: CalculationResult):
        """解析频率信息"""
        # 检查是否有频率计算
        if 'Vibrational' not in content and 'frequency' not in content.lower():
            return
        
        # 解析频率值
        freq_pattern = r'\s*(\d+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)'
        freq_matches = re.findall(
            r'Vibrational.*?-+\s*\n(.*?)\n.*?-',
            content, re.DOTALL
        )
        
        if freq_matches:
            frequencies = []
            ir_intensities = []
            raman_activities = []
            
            for block in freq_matches:
                for line in block.split('\n'):
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        try:
                            freq = float(parts[1])
                            frequencies.append(freq)
                            
                            if len(parts) >= 4:
                                ir_intensities.append(float(parts[2]))
                            if len(parts) >= 5:
                                raman_activities.append(float(parts[3]))
                        except ValueError:
                            continue
            
            result.frequencies = frequencies
            result.ir_intensities = ir_intensities
            result.raman_activities = raman_activities
        
        # 解析零点能和热力学校正
        zpe_match = re.search(r'Zero-point correction\s*=\s+([-\d.]+)', content)
        if zpe_match:
            result.zero_point_energy = float(zpe_match.group(1))
        
        thermal_match = re.search(r'Thermal correction to Energy\s*=\s+([-\d.]+)', content)
        if thermal_match:
            result.thermal_correction = float(thermal_match.group(1))
        
        entropy_match = re.search(r'Total Entropy\s*=\s+([-\d.]+)', content)
        if entropy_match:
            result.entropy = float(entropy_match.group(1))
        
        # 解析Hessian矩阵 (如果存在)
        hessian_match = re.search(
            r'Hessian.*?-+\s*\n(.*?)\n.*?-',
            content, re.DOTALL
        )
        if hessian_match:
            result.hessian_matrix = self._parse_hessian_block(
                hessian_match.group(1)
            )
    
    def _parse_hessian_block(self, block: str) -> List[List[float]]:
        """解析Hessian矩阵块"""
        matrix = []
        for line in block.strip().split('\n'):
            values = []
            for val in line.strip().split():
                try:
                    values.append(float(val))
                except ValueError:
                    continue
            if values:
                matrix.append(values)
        return matrix
    
    def _parse_convergence(self, content: str, result: CalculationResult):
        """解析收敛信息"""
        # SCF收敛
        if 'SCF converged' in content or 'Convergence criterion met' in content:
            result.scf_converged = True
        
        # SCF迭代次数
        scf_iter_match = re.search(r'Iterations:\s*(\d+)', content)
        if scf_iter_match:
            result.n_iterations = int(scf_iter_match.group(1))
        
        # 几何优化收敛
        if 'Optimization converged' in content or 'OPTIMIZATION CONVERGED' in content:
            result.geometry_converged = True
            result.converged = True
        
        # 优化循环次数
        opt_iter_match = re.search(r'Optimization completed after\s*(\d+)\s*cycles', content)
        if opt_iter_match:
            result.n_iterations = int(opt_iter_match.group(1))
    
    def _parse_performance(self, content: str, result: CalculationResult):
        """解析性能信息"""
        # CPU时间
        cpu_match = re.search(r'CPU time:\s+([\d.]+)\s*seconds', content)
        if cpu_match:
            result.cpu_time = float(cpu_match.group(1))
        
        # 墙钟时间
        wall_match = re.search(r'Wall time:\s+([\d.]+)\s*seconds', content)
        if wall_match:
            result.wall_time = float(wall_match.group(1))
        
        # 内存使用
        mem_match = re.search(r'Memory:\s+([\d.]+)\s*MB', content)
        if mem_match:
            result.memory_used_mb = float(mem_match.group(1))
    
    def _check_errors(self, content: str, result: CalculationResult):
        """检查错误信息"""
        error_patterns = [
            (r'SCF did not converge', 'SCF不收敛'),
            (r'Optimization did not converge', '几何优化不收敛'),
            (r'Fatal Error', '致命错误'),
            (r'Out of memory', '内存不足'),
            (r'FileIO Error', '文件IO错误'),
            (r'BasisSetError', '基组错误'),
        ]
        
        errors = []
        for pattern, desc in error_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                errors.append(desc)
        
        if errors:
            result.error_message = '; '.join(errors)


# ==================== PSI4适配器 ====================

class PSI4Adapter(EngineAdapter):
    """
    PSI4量子化学引擎适配器
    
    特性:
    - 支持多种计算方法 (HF, DFT, MP2, CCSD, etc.)
    - 自动输入文件生成
    - 智能错误处理和重试
    - 并行计算支持
    - 完整的输出解析
    """
    
    def __init__(self, psi4_path: Optional[str] = None):
        super().__init__("PSI4", "unknown")
        self.psi4_path = psi4_path or self._find_psi4()
        self.parser = PSI4OutputParser()
        self._version_checked = False
        
        if self.is_available and not self._version_checked:
            self._check_version()
    
    def _find_psi4(self) -> Optional[str]:
        """查找PSI4可执行文件"""
        # 检查环境变量
        psi4_env = os.environ.get('PSI4_PATH')
        if psi4_env and os.path.isfile(psi4_env):
            return psi4_env
        
        # 检查常见路径
        common_paths = [
            'psi4',
            '/usr/bin/psi4',
            '/usr/local/bin/psi4',
            '/opt/psi4/bin/psi4',
            os.path.expanduser('~/psi4/bin/psi4'),
            os.path.expanduser('~/anaconda3/bin/psi4'),
            os.path.expanduser('~/miniconda3/bin/psi4'),
            os.path.expanduser('~/.conda/envs/psi4/bin/psi4'),
        ]
        
        for path in common_paths:
            if shutil.which(path):
                return shutil.which(path)
        
        return None
    
    def _check_version(self):
        """检查PSI4版本"""
        try:
            result = subprocess.run(
                [self.psi4_path, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # 解析版本号
            version_match = re.search(r'(\d+\.\d+(?:\.\d+)?)', result.stdout)
            if version_match:
                self.version = version_match.group(1)
            
            self._version_checked = True
            self.logger.info(f"PSI4版本: {self.version}")
            
        except Exception as e:
            self.logger.warning(f"无法获取PSI4版本: {e}")
    
    @property
    def is_available(self) -> bool:
        """检查PSI4是否可用"""
        return self.psi4_path is not None and os.path.isfile(self.psi4_path)
    
    def validate_config(self, config: CalculationConfig) -> Tuple[bool, List[str]]:
        """验证计算配置"""
        errors = []
        
        # 检查几何结构
        if not config.geometry or not config.geometry.strip():
            errors.append("分子几何结构不能为空")
        
        # 检查方法
        valid_methods = [
            'HF', 'RHF', 'UHF', 'ROHF',
            'B3LYP', 'PBE', 'PBE0', 'M06-2X', 'ωB97X-D', 'wB97X-D',
            'MP2', 'RI-MP2', 'CCSD', 'CCSD(T)', 'FNO-CCSD(T)'
        ]
        
        if config.method.upper() not in [m.upper() for m in valid_methods]:
            errors.append(f"不支持的方法: {config.method}")
        
        # 检查基组
        if not config.basis:
            errors.append("基组不能为空")
        
        # 检查资源参数
        if config.num_threads < 1:
            errors.append("线程数必须大于0")
        
        return len(errors) == 0, errors
    
    def generate_input(self, config: CalculationConfig,
                       work_dir: str) -> str:
        """生成PSI4输入文件"""
        input_lines = []
        
        # 内存设置
        input_lines.append(f"memory {config.memory}")
        input_lines.append("")
        
        # 分子定义
        input_lines.append("molecule {")
        input_lines.append(f"  {config.charge} {config.multiplicity}")
        
        # 添加        # 添加几何结构
        geometry_lines = config.geometry.strip().split('\n')
        for line in geometry_lines:
            input_lines.append(f"  {line}")
        
        input_lines.append("}")
        input_lines.append("")
        
        # 设置选项
        input_lines.append("set {")
        input_lines.append(f"  basis {config.basis}")
        input_lines.append(f"  scf_type {config.scf_type}")
        input_lines.append(f"  guess {config.guess}")
        input_lines.append(f"  e_convergence {config.scf_convergence}")
        input_lines.append(f"  maxiter {config.max_scf_iterations}")
        
        # 几何优化选项
        if config.calculation_type in [CalculationType.GEOMETRY_OPTIMIZATION, 
                                       CalculationType.TRANSITION_STATE]:
            input_lines.append(f"  opt_type {config.opt_type}")
            input_lines.append(f"  g_convergence {config.opt_convergence}")
            input_lines.append(f"  geom_maxiter {config.max_opt_cycles}")
        
        # 频率选项
        if config.calculation_type == CalculationType.FREQUENCY:
            input_lines.append(f"  temp {config.temperature}")
        
        # 并行设置
        input_lines.append(f"  num_threads {config.num_threads}")
        
        # 自定义选项
        for key, value in config.psi4_options.items():
            input_lines.append(f"  {key} {value}")
        
        input_lines.append("}")
        input_lines.append("")
        
        # 计算命令
        if config.calculation_type == CalculationType.SINGLE_POINT:
            input_lines.append(f"energy('{config.method}')")
        elif config.calculation_type == CalculationType.GEOMETRY_OPTIMIZATION:
            input_lines.append(f"optimize('{config.method}')")
        elif config.calculation_type == CalculationType.FREQUENCY:
            input_lines.append(f"frequency('{config.method}')")
        elif config.calculation_type == CalculationType.TRANSITION_STATE:
            input_lines.append(f"optimize('{config.method}', transition_state=True)")
        else:
            input_lines.append(f"energy('{config.method}')")
        
        # 写入文件
        input_file = os.path.join(work_dir, "input.dat")
        with open(input_file, 'w') as f:
            f.write('\n'.join(input_lines))
        
        return input_file
    
    def execute(self, input_file: str, work_dir: str,
                timeout: Optional[int] = None) -> Tuple[int, str, str]:
        """执行PSI4计算"""
        output_file = os.path.join(work_dir, "output.dat")
        
        cmd = [
            self.psi4_path,
            input_file,
            output_file,
            f"-n{self._get_config_from_file(input_file).num_threads}"
        ]
        
        self.logger.info(f"执行命令: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=work_dir
            )
            
            return result.returncode, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"计算超时 ({timeout}秒)")
            return -1, "", f"Timeout after {timeout} seconds"
        except Exception as e:
            self.logger.error(f"执行失败: {e}")
            return -1, "", str(e)
    
    def _get_config_from_file(self, input_file: str) -> CalculationConfig:
        """从输入文件解析配置（简化版）"""
        config = CalculationConfig()
        with open(input_file, 'r') as f:
            content = f.read()
        
        # 解析线程数
        match = re.search(r'num_threads\s+(\d+)', content)
        if match:
            config.num_threads = int(match.group(1))
        
        return config
    
    def parse_output(self, output_file: str, 
                     config: CalculationConfig) -> CalculationResult:
        """解析PSI4输出"""
        return self.parser.parse(output_file, config)


# ==================== 性能优化 ====================

class PerformanceOptimizer:
    """
    性能优化器
    
    功能:
    - 自动内存管理
    - 并行计算优化
    - 磁盘I/O优化
    - 缓存管理
    """
    
    def __init__(self):
        self.logger = logging.getLogger("PerformanceOptimizer")
        self._cache = {}
        self._cache_lock = threading.RLock()
    
    def estimate_memory(self, n_atoms: int, basis: str, method: str) -> str:
        """
        估算所需内存
        
        Args:
            n_atoms: 原子数
            basis: 基组
            method: 计算方法
            
        Returns:
            内存字符串 (如 "4 GB")
        """
        # 基组大小因子
        basis_factors = {
            'sto-3g': 1,
            '3-21g': 1.5,
            '6-31g': 2,
            '6-31g(d)': 2.5,
            '6-311g(d,p)': 3.5,
            'cc-pvdz': 3,
            'cc-pvtz': 6,
            'cc-pvqz': 12,
        }
        
        basis_lower = basis.lower()
        factor = 2.0  # 默认值
        for key, val in basis_factors.items():
            if key in basis_lower:
                factor = val
                break
        
        # 方法因子
        method_factors = {
            'hf': 1.0,
            'dft': 1.2,
            'mp2': 2.0,
            'ccsd': 4.0,
            'ccsd(t)': 6.0,
        }
        
        method_lower = method.lower()
        method_factor = 1.0
        for key, val in method_factors.items():
            if key in method_lower:
                method_factor = val
                break
        
        # 估算内存 (GB)
        memory_gb = max(1, int(n_atoms * factor * method_factor / 10))
        
        return f"{memory_gb} GB"
    
    def optimize_parallel(self, n_calculations: int, 
                         max_cores: Optional[int] = None) -> Dict[str, int]:
        """
        优化并行计算配置
        
        Args:
            n_calculations: 计算任务数
            max_cores: 最大可用核心数
            
        Returns:
            优化配置字典
        """
        if max_cores is None:
            max_cores = os.cpu_count() or 4
        
        # 计算最优配置
        if n_calculations <= max_cores:
            # 任务数少于核心数，每个任务使用更多核心
            n_workers = n_calculations
            threads_per_job = max(1, max_cores // n_calculations)
        else:
            # 任务数多于核心数，限制并行度
            n_workers = max_cores
            threads_per_job = 1
        
        return {
            'n_workers': n_workers,
            'threads_per_job': threads_per_job,
            'total_cores_used': n_workers * threads_per_job
        }
    
    def cleanup_work_dir(self, work_dir: str, keep_output: bool = True):
        """
        清理工作目录
        
        Args:
            work_dir: 工作目录路径
            keep_output: 是否保留输出文件
        """
        if not os.path.exists(work_dir):
            return
        
        try:
            if keep_output:
                # 只保留输出文件
                for item in os.listdir(work_dir):
                    item_path = os.path.join(work_dir, item)
                    if item != 'output.dat':
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
            else:
                # 删除整个目录
                shutil.rmtree(work_dir)
                
        except Exception as e:
            self.logger.warning(f"清理工作目录失败: {e}")
    
    def cache_result(self, key: str, result: CalculationResult):
        """缓存计算结果"""
        with self._cache_lock:
            self._cache[key] = {
                'result': result,
                'timestamp': time.time()
            }
    
    def get_cached_result(self, key: str, max_age: float = 3600) -> Optional[CalculationResult]:
        """获取缓存的结果"""
        with self._cache_lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - entry['timestamp'] < max_age:
                    return entry['result']
                else:
                    del self._cache[key]
            return None
    
    def clear_cache(self):
        """清空缓存"""
        with self._cache_lock:
            self._cache.clear()


# ==================== 计算管理器 ====================

class CalculationManager:
    """
    计算管理器
    
    统一管理多个计算引擎和任务
    """
    
    def __init__(self):
        self.engines: Dict[str, EngineAdapter] = {}
        self.optimizer = PerformanceOptimizer()
        self.logger = logging.getLogger("CalculationManager")
        
        # 注册默认引擎
        self._register_default_engines()
    
    def _register_default_engines(self):
        """注册默认计算引擎"""
        psi4 = PSI4Adapter()
        if psi4.is_available:
            self.register_engine('psi4', psi4)
            self.logger.info("PSI4引擎已注册")
        else:
            self.logger.warning("PSI4引擎不可用")
    
    def register_engine(self, name: str, engine: EngineAdapter):
        """注册计算引擎"""
        self.engines[name] = engine
    
    def get_engine(self, name: str) -> Optional[EngineAdapter]:
        """获取计算引擎"""
        return self.engines.get(name)
    
    def list_engines(self) -> List[str]:
        """列出可用引擎"""
        return [name for name, engine in self.engines.items() if engine.is_available]
    
    def submit(self, config: CalculationConfig, 
               engine_name: str = 'psi4',
               work_dir: Optional[str] = None) -> CalculationResult:
        """
        提交单个计算任务
        
        Args:
            config: 计算配置
            engine_name: 引擎名称
            work_dir: 工作目录
            
        Returns:
            计算结果
        """
        engine = self.get_engine(engine_name)
        if not engine:
            return CalculationResult(
                success=False,
                status=CalculationStatus.FAILED,
                error_message=f"引擎 '{engine_name}' 未找到"
            )
        
        # 自动估算内存
        if config.geometry:
            n_atoms = len([line for line in config.geometry.strip().split('\n') 
                          if line.strip() and not line.strip().startswith('#')])
            config.memory = self.optimizer.estimate_memory(n_atoms, config.basis, config.method)
        
        return engine.run_with_retry(config, work_dir)
    
    def submit_batch(self, configs: List[CalculationConfig],
                    engine_name: str = 'psi4',
                    work_dir: Optional[str] = None,
                    max_workers: Optional[int] = None) -> List[CalculationResult]:
        """
        批量提交计算任务
        
        Args:
            configs: 计算配置列表
            engine_name: 引擎名称
            work_dir: 基础工作目录
            max_workers: 最大并行数
            
        Returns:
            计算结果列表
        """
        engine = self.get_engine(engine_name)
        if not engine:
            return [CalculationResult(
                success=False,
                status=CalculationStatus.FAILED,
                error_message=f"引擎 '{engine_name}' 未找到"
            )] * len(configs)
        
        # 优化并行配置
        opt_config = self.optimizer.optimize_parallel(len(configs), max_workers)
        self.logger.info(f"并行配置: {opt_config}")
        
        # 更新每个配置的线程数
        for config in configs:
            config.num_threads = opt_config['threads_per_job']
        
        return engine.run_parallel(configs, work_dir, opt_config['n_workers'])


# ==================== 使用示例 ====================

def example_single_point():
    """单点能计算示例"""
    # 创建配置
    config = CalculationConfig(
        method="B3LYP",
        basis="6-31G(d)",
        calculation_type=CalculationType.SINGLE_POINT,
        charge=0,
        multiplicity=1,
        geometry="""H 0.0 0.0 0.0
H 0.0 0.0 0.74""",
        num_threads=4,
        memory="2 GB"
    )
    
    # 创建管理器并提交计算
    manager = CalculationManager()
    result = manager.submit(config)
    
    print(f"计算成功: {result.success}")
    print(f"总能量: {result.total_energy}")
    print(f"SCF能量: {result.scf_energy}")
    
    return result


def example_geometry_optimization():
    """几何优化示例"""
    config = CalculationConfig(
        method="B3LYP",
        basis="6-31G(d)",
        calculation_type=CalculationType.GEOMETRY_OPTIMIZATION,
        charge=0,
        multiplicity=1,
        geometry="""O 0.0 0.0 0.0
H 0.757 0.586 0.0
H -0.757 0.586 0.0""",
        opt_convergence="GAU_TIGHT",
        max_opt_cycles=100,
        num_threads=4
    )
    
    manager = CalculationManager()
    result = manager.submit(config)
    
    print(f"优化成功: {result.success}")
    print(f"收敛状态: {result.converged}")
    print(f"最终能量: {result.total_energy}")
    
    if result.final_geometry:
        print("最终几何结构:")
        for atom in result.final_geometry:
            print(f"  {atom['symbol']}: ({atom['x']:.4f}, {atom['y']:.4f}, {atom['z']:.4f})")
    
    return result


def example_frequency():
    """频率计算示例"""
    config = CalculationConfig(
        method="B3LYP",
        basis="6-31G(d)",
        calculation_type=CalculationType.FREQUENCY,
        charge=0,
        multiplicity=1,
        geometry="""O 0.0 0.0 0.0
H 0.757 0.586 0.0
H -0.757 0.586 0.0""",
        temperature=298.15,
        num_threads=4
    )
    
    manager = CalculationManager()
    result = manager.submit(config)
    
    print(f"计算成功: {result.success}")
    
    if result.frequencies:
        print(f"频率: {result.frequencies}")
    
    if result.zero_point_energy:
        print(f"零点能: {result.zero_point_energy}")
    
    return result


def example_batch_calculation():
    """批量计算示例"""
    # 创建多个配置
    configs = []
    basis_sets = ['sto-3g', '6-31G(d)', 'cc-pVDZ']
    
    for basis in basis_sets:
        config = CalculationConfig(
            method="B3LYP",
            basis=basis,
            calculation_type=CalculationType.SINGLE_POINT,
            charge=0,
            multiplicity=1,
            geometry="""H 0.0 0.0 0.0
H 0.0 0.0 0.74"""
        )
        configs.append(config)
    
    # 批量提交
    manager = CalculationManager()
    results = manager.submit_batch(configs)
    
    for i, (config, result) in enumerate(zip(configs, results)):
        print(f"任务 {i+1} ({config.basis}): 能量 = {result.total_energy}")
    
    return results


if __name__ == "__main__":
    print("=" * 60)
    print("PSI4计算引擎生产级实现")
    print("=" * 60)
    
    # 检查PSI4可用性
    adapter = PSI4Adapter()
    print(f"\nPSI4可用性: {adapter.is_available}")
    print(f"PSI4版本: {adapter.version}")
    print(f"PSI4路径: {adapter.psi4_path}")
    
    print("\n" + "=" * 60)
    print("组件清单:")
    print("  1. EngineAdapter - 引擎适配器基类")
    print("  2. PSI4Adapter - PSI4引擎适配器")
    print("  3. PSI4OutputParser - 输出解析器")
    print("  4. PerformanceOptimizer - 性能优化器")
    print("  5. CalculationManager - 计算管理器")
    print("=" * 60)

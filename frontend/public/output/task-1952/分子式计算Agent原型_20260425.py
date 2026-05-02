#!/usr/bin/env python3
"""
分子式计算Agent工具原型
========================
基于DeepSeek R1数学推理能力的材料科学计算Agent

功能：
1. 摩尔质量计算
2. 元素质量百分比计算
3. 化学计量比计算
4. 晶体化学式确定
5. 反应热力学计算
6. 晶体结构参数计算

作者：刘宇宙教授
日期：2026年4月25日
单位：北京航空航天大学化学学院 / 和光智成
"""

import re
import math
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass

# ============= 原子量数据库 =============
ATOMIC_WEIGHTS = {
    'H': 1.008, 'He': 4.003, 'Li': 6.94, 'Be': 9.012, 'B': 10.81,
    'C': 12.01, 'N': 14.01, 'O': 16.00, 'F': 19.00, 'Ne': 20.18,
    'Na': 22.99, 'Mg': 24.31, 'Al': 26.98, 'Si': 28.09, 'P': 30.97,
    'S': 32.07, 'Cl': 35.45, 'Ar': 39.95, 'K': 39.10, 'Ca': 40.08,
    'Sc': 44.96, 'Ti': 47.87, 'V': 50.94, 'Cr': 52.00, 'Mn': 54.94,
    'Fe': 55.85, 'Co': 58.93, 'Ni': 58.69, 'Cu': 63.55, 'Zn': 65.38,
    'Ga': 69.72, 'Ge': 72.63, 'As': 74.92, 'Se': 78.96, 'Br': 79.90,
    'Kr': 83.80, 'Rb': 85.47, 'Sr': 87.62, 'Y': 88.91, 'Zr': 91.22,
    'Nb': 92.91, 'Mo': 95.95, 'Tc': 98.00, 'Ru': 101.1, 'Rh': 102.9,
    'Pd': 106.4, 'Ag': 107.9, 'Cd': 112.4, 'In': 114.8, 'Sn': 118.7,
    'Sb': 121.8, 'Te': 127.6, 'I': 126.9, 'Xe': 131.3, 'Cs': 132.9,
    'Ba': 137.3, 'La': 138.9, 'Ce': 140.1, 'Pr': 140.9, 'Nd': 144.2,
    'Pm': 145.0, 'Sm': 150.4, 'Eu': 152.0, 'Gd': 157.3, 'Tb': 158.9,
    'Dy': 162.5, 'Ho': 164.9, 'Er': 167.3, 'Tm': 168.9, 'Yb': 173.1,
    'Lu': 175.0, 'Hf': 178.5, 'Ta': 180.9, 'W': 183.8, 'Re': 186.2,
    'Os': 190.2, 'Ir': 192.2, 'Pt': 195.1, 'Au': 197.0, 'Hg': 200.6,
    'Tl': 204.4, 'Pb': 207.2, 'Bi': 209.0, 'Po': 209.0, 'At': 210.0,
    'Rn': 222.0, 'Fr': 223.0, 'Ra': 226.0, 'Ac': 227.0, 'Th': 232.0,
    'Pa': 231.0, 'U': 238.0, 'Np': 237.0, 'Pu': 244.0, 'Am': 243.0,
    'Cm': 247.0, 'Bk': 247.0, 'Cf': 251.0, 'Es': 252.0, 'Fm': 257.0,
    'Md': 258.0, 'No': 259.0, 'Lr': 262.0, 'Rf': 267.0, 'Db': 268.0,
    'Sg': 269.0, 'Bh': 270.0, 'Hs': 277.0, 'Mt': 278.0, 'Ds': 281.0,
    'Rg': 282.0, 'Cn': 285.0, 'Nh': 286.0, 'Fl': 289.0, 'Mc': 290.0,
    'Lv': 293.0, 'Ts': 294.0, 'Og': 294.0,
}

# 常用物理常数
PHYSICAL_CONSTANTS = {
    'R': 8.314,  # J/(mol·K) 气体常数
    'N_A': 6.022e23,  # mol⁻¹ 阿伏伽德罗常数
    'h': 6.626e-34,  # J·s 普朗克常数
    'c': 2.998e8,  # m/s 光速
    'k_B': 1.381e-23,  # J/K 玻尔兹曼常数
    'F': 96485,  # C/mol 法拉第常数
}

AVOGADRO = PHYSICAL_CONSTANTS['N_A']
GAS_CONSTANT = PHYSICAL_CONSTANTS['R']


@dataclass
class CalculationResult:
    """计算结果数据类"""
    success: bool
    value: float
    unit: str
    formula: str
    steps: List[str]
    error: Optional[str] = None


class MolecularFormulaAgent:
    """分子式计算Agent"""

    def __init__(self):
        self.atomic_weights = ATOMIC_WEIGHTS
        self.history = []

    def parse_formula(self, formula: str) -> Dict[str, int]:
        """
        解析分子式，返回各元素及其计数

        Args:
            formula: 分子式字符串，如 "LiFePO4", "H2O", "Ca(OH)2"

        Returns:
            元素计数字典，如 {'Li': 1, 'Fe': 1, 'P': 1, 'O': 4}
        """
        elements = {}

        # 处理括号
        while '(' in formula:
            match = re.search(r'\(([A-Za-z0-9]+)\)(\d*)', formula)
            if not match:
                break
            inner = match.group(1)
            multiplier = int(match.group(2)) if match.group(2) else 1
            inner_elements = self._parse_simple_formula(inner)
            for elem, count in inner_elements.items():
                inner_elements[elem] = count * multiplier
            formula = formula[:match.start()] + \
                self._dict_to_formula(inner_elements) + formula[match.end():]

        # 处理剩余部分
        remaining = self._parse_simple_formula(formula)
        for elem, count in remaining.items():
            elements[elem] = elements.get(elem, 0) + count

        return elements

    def _parse_simple_formula(self, formula: str) -> Dict[str, int]:
        """解析无括号的简单分子式"""
        pattern = r'([A-Z][a-z]?)(\d*)'
        elements = {}
        for match in re.finditer(pattern, formula):
            elem = match.group(1)
            count = int(match.group(2)) if match.group(2) else 1
            if elem in self.atomic_weights:
                elements[elem] = elements.get(elem, 0) + count
            else:
                raise ValueError(f"未知元素: {elem}")
        return elements

    def _dict_to_formula(self, elements: Dict[str, int]) -> str:
        """将元素字典转换为分子式字符串"""
        return ''.join(f"{elem}{count if count > 1 else ''}"
                      for elem, count in elements.items())

    def calculate_molar_mass(self, formula: str) -> CalculationResult:
        """
        计算摩尔质量

        Args:
            formula: 分子式，如 "LiFePO4"

        Returns:
            CalculationResult对象
        """
        steps = []
        try:
            elements = self.parse_formula(formula)
            steps.append(f"解析分子式 {formula}: {elements}")

            total_mass = 0.0
            breakdown = []

            for elem, count in elements.items():
                mass = self.atomic_weights[elem]
                contribution = mass * count
                total_mass += contribution
                breakdown.append(f"{elem}: {count} × {mass} = {contribution:.2f}")
                steps.append(breakdown[-1])

            steps.append(f"总摩尔质量: {total_mass:.2f} g/mol")

            return CalculationResult(
                success=True,
                value=total_mass,
                unit='g/mol',
                formula=formula,
                steps=steps
            )

        except Exception as e:
            return CalculationResult(
                success=False,
                value=0.0,
                unit='g/mol',
                formula=formula,
                steps=steps,
                error=str(e)
            )

    def calculate_mass_percent(self, formula: str,
                                target_element: str) -> CalculationResult:
        """
        计算指定元素的质量百分比

        Args:
            formula: 分子式
            target_element: 目标元素符号

        Returns:
            CalculationResult对象
        """
        steps = []
        try:
            elements = self.parse_formula(formula)
            steps.append(f"解析分子式 {formula}: {elements}")

            if target_element not in elements:
                raise ValueError(f"分子式中不含元素 {target_element}")

            # 计算总质量
            total_mass = sum(self.atomic_weights[elem] * count
                            for elem, count in elements.items())
            steps.append(f"总摩尔质量: {total_mass:.4f} g/mol")

            # 计算目标元素质量
            elem_mass = self.atomic_weights[target_element] * \
                elements[target_element]
            steps.append(
                f"{target_element}的总质量: {elements[target_element]} × {self.atomic_weights[target_element]} = {elem_mass:.4f} g/mol")

            # 计算百分比
            percent = (elem_mass / total_mass) * 100
            steps.append(f"质量百分比: ({elem_mass:.4f} / {total_mass:.4f}) × 100% = {percent:.2f}%")

            return CalculationResult(
                success=True,
                value=percent,
                unit='%',
                formula=formula,
                steps=steps
            )

        except Exception as e:
            return CalculationResult(
                success=False,
                value=0.0,
                unit='%',
                formula=formula,
                steps=steps,
                error=str(e)
            )

    def calculate_stoichiometry(self, reaction: str, reactant_mass: float,
                                 reactant_formula: str, product_formula: str) -> CalculationResult:
        """
        化学反应计量计算

        Args:
            reaction: 反应方程式，如 "CH4 + 2 O2 -> CO2 + 2 H2O"
            reactant_mass: 反应物质量（克）
            reactant_formula: 反应物分子式
            product_formula: 生成物分子式

        Returns:
            CalculationResult对象
        """
        steps = []
        try:
            steps.append(f"反应方程式: {reaction}")
            steps.append(f"反应物质量: {reactant_mass} g ({reactant_formula})")

            # 计算反应物摩尔质量
            reactant_mm = self.calculate_molar_mass(reactant_formula)
            if not reactant_mm.success:
                raise ValueError(reactant_mm.error)
            steps.append(f"{reactant_formula}摩尔质量: {reactant_mm.value:.2f} g/mol")

            # 计算物质的量
            reactant_moles = reactant_mass / reactant_mm.value
            steps.append(f"{reactant_formula}物质的量: {reactant_mass:.2f} / {reactant_mm.value:.2f} = {reactant_moles:.4f} mol")

            # 解析反应方程式获取计量比
            # 简化处理：假设用户知道计量比，这里按1:1处理（实际应用中需要更复杂的解析）
            ratio = 1.0  # 默认1:1，实际需要从反应式解析
            steps.append(f"使用计量比 1:1（实际应用需根据反应方程式准确解析）")

            # 计算生成物质量
            product_mm = self.calculate_molar_mass(product_formula)
            product_mass = reactant_moles * ratio * product_mm.value
            steps.append(f"{product_formula}理论产量: {reactant_moles:.4f} × {ratio} × {product_mm.value:.2f} = {product_mass:.2f} g")

            return CalculationResult(
                success=True,
                value=product_mass,
                unit='g',
                formula=reaction,
                steps=steps
            )

        except Exception as e:
            return CalculationResult(
                success=False,
                value=0.0,
                unit='g',
                formula=reaction,
                steps=steps,
                error=str(e)
            )


class ThermodynamicsAgent:
    """热力学计算Agent"""

    def __init__(self):
        self.formation_enthalpies = {
            'Al2O3': -1676, 'Fe2O3': -824, 'CaCO3': -1207,
            'CaO': -635, 'CO2': -393.5, 'H2O(l)': -285.8,
            'H2O(g)': -241.8, 'NaCl': -411.2, 'MgO': -601.7,
        }

    def calculate_reaction_enthalpy(self, reactants: Dict[str, float],
                                     products: Dict[str, float]) -> CalculationResult:
        """
        计算反应焓变 ΔH°

        Args:
            reactants: 反应物及其生成焓 {物质: 系数}
            products: 生成物及其生成焓 {物质: 系数}

        Returns:
            CalculationResult对象
        """
        steps = []
        try:
            steps.append("根据 Hess 定律: ΔH° = ΣΔH°_f(产物) - ΣΔH°_f(反应物)")

            products_sum = 0.0
            for compound, coeff in products.items():
                if compound in self.formation_enthalpies:
                    hf = self.formation_enthalpies[compound]
                    contribution = coeff * hf
                    products_sum += contribution
                    steps.append(f"产物 {compound}: {coeff} × {hf} = {contribution} kJ/mol")
                else:
                    steps.append(f"产物 {compound}: 单质或未知，生成焓=0")

            reactants_sum = 0.0
            for compound, coeff in reactants.items():
                if compound in self.formation_enthalpies:
                    hf = self.formation_enthalpies[compound]
                    contribution = coeff * hf
                    reactants_sum += contribution
                    steps.append(f"反应物 {compound}: {coeff} × {hf} = {contribution} kJ/mol")
                else:
                    steps.append(f"反应物 {compound}: 单质或未知，生成焓=0")

            delta_h = products_sum - reactants_sum
            steps.append(f"ΔH° = {products_sum:.1f} - ({reactants_sum:.1f}) = {delta_h:.1f} kJ/mol")

            if delta_h < 0:
                steps.append("反应为放热反应 (ΔH° < 0)")
            else:
                steps.append("反应为吸热反应 (ΔH° > 0)")

            return CalculationResult(
                success=True,
                value=delta_h,
                unit='kJ/mol',
                formula='ΔH° = ΣΔH°_f(产物) - ΣΔH°_f(反应物)',
                steps=steps
            )

        except Exception as e:
            return CalculationResult(
                success=False,
                value=0.0,
                unit='kJ/mol',
                formula='ΔH° calculation',
                steps=steps,
                error=str(e)
            )

    def calculate_gibbs_free_energy(self, delta_h: float, delta_s: float,
                                     temperature: float = 298) -> CalculationResult:
        """
        计算 Gibbs 自由能 ΔG°

        Args:
            delta_h: 焓变 (kJ/mol)
            delta_s: 熵变 (J/(mol·K))
            temperature: 温度 (K)，默认298K

        Returns:
            CalculationResult对象
        """
        steps = []
        try:
            steps.append(f"Gibbs自由能公式: ΔG° = ΔH° - TΔS°")
            steps.append(f"ΔH° = {delta_h} kJ/mol = {delta_h * 1000} J/mol")
            steps.append(f"ΔS° = {delta_s} J/(mol·K)")
            steps.append(f"T = {temperature} K")

            delta_s_kJ = delta_s / 1000  # 转换为 kJ/(mol·K)
            steps.append(f"ΔS° 单位转换: {delta_s} J/(mol·K) = {delta_s_kJ} kJ/(mol·K)")

            delta_g = delta_h - temperature * delta_s_kJ
            steps.append(f"ΔG° = {delta_h} - {temperature} × {delta_s_kJ:.4f} = {delta_g:.1f} kJ/mol")

            if delta_g < 0:
                steps.append("反应自发进行 (ΔG° < 0)")
            elif delta_g > 0:
                steps.append("反应非自发 (ΔG° > 0)")
            else:
                steps.append("反应达平衡 (ΔG° = 0)")

            return CalculationResult(
                success=True,
                value=delta_g,
                unit='kJ/mol',
                formula='ΔG° = ΔH° - TΔS°',
                steps=steps
            )

        except Exception as e:
            return CalculationResult(
                success=False,
                value=0.0,
                unit='kJ/mol',
                formula='ΔG° calculation',
                steps=steps,
                error=str(e)
            )

    def calculate_equilibrium_constant(self, delta_g: float,
                                        temperature: float = 298) -> CalculationResult:
        """
        计算平衡常数 K

        Args:
            delta_g: Gibbs自由能 (kJ/mol)
            temperature: 温度 (K)

        Returns:
            CalculationResult对象
        """
        steps = []
        try:
            steps.append(f"平衡常数公式: ΔG° = -RT ln(K)")
            steps.append(f"ΔG° = {delta_g} kJ/mol = {delta_g * 1000} J/mol")
            steps.append(f"R = {GAS_CONSTANT} J/(mol·K)")
            steps.append(f"T = {temperature} K")

            delta_g_j = delta_g * 1000
            ln_k = -delta_g_j / (GAS_CONSTANT * temperature)
            k = math.exp(ln_k)

            steps.append(f"ln(K) = -ΔG°/(RT) = {-delta_g_j:.0f} / ({GAS_CONSTANT:.3f} × {temperature}) = {ln_k:.3f}")
            steps.append(f"K = e^{ln_k:.3f} = {k:.2e}")

            return CalculationResult(
                success=True,
                value=k,
                unit='(无量纲)',
                formula='ΔG° = -RT ln(K)',
                steps=steps
            )

        except Exception as e:
            return CalculationResult(
                success=False,
                value=0.0,
                unit='(无量纲)',
                formula='K calculation',
                steps=steps,
                error=str(e)
            )


class CrystalAgent:
    """晶体结构计算Agent"""

    def __init__(self):
        self.mol_agent = MolecularFormulaAgent()

    def calculate_crystal_density(self, formula: str, z: int,
                                   a: float, unit: str = 'Å') -> CalculationResult:
        """
        计算晶体密度

        Args:
            formula: 分子式
            z: 晶胞中化学式单元数
            a: 晶胞参数（立方体晶胞边长）
            unit: 晶胞参数单位，'Å' 或 'cm'

        Returns:
            CalculationResult对象
        """
        steps = []
        try:
            steps.append(f"晶体密度计算: ρ = (Z × M) / (N_A × V)")
            steps.append(f"Z = {z} (晶胞中化学式单元数)")
            steps.append(f"a = {a} {unit}")

            # 计算摩尔质量
            mm_result = self.mol_agent.calculate_molar_mass(formula)
            molar_mass = mm_result.value
            steps.append(f"M = {molar_mass:.2f} g/mol (摩尔质量)")

            # 单位转换
            if unit == 'Å':
                a_cm = a * 1e-8  # Å → cm
                steps.append(f"单位转换: a = {a} Å = {a_cm:.2e} cm")
            else:
                a_cm = a

            # 计算晶胞体积
            volume = a_cm ** 3
            steps.append(f"V = a³ = ({a_cm:.2e})³ = {volume:.4e} cm³")

            # 计算密度
            density = (z * molar_mass) / (AVOGADRO * volume)
            steps.append(f"ρ = ({z} × {molar_mass:.2f}) / ({AVOGADRO:.2e} × {volume:.4e})")
            steps.append(f"ρ = {density:.2f} g/cm³")

            return CalculationResult(
                success=True,
                value=density,
                unit='g/cm³',
                formula='ρ = ZM / (N_A V)',
                steps=steps
            )

        except Exception as e:
            return CalculationResult(
                success=False,
                value=0.0,
                unit='g/cm³',
                formula='ρ = ZM / (N_A V)',
                steps=steps,
                error=str(e)
            )

    def bragg_equation(self, wavelength: float, two_theta: float,
                        n: int = 1) -> CalculationResult:
        """
        布拉格方程计算晶面间距

        Args:
            wavelength: X射线波长 (Å)
            two_theta: 衍射角 2θ (度)
            n: 衍射级数

        Returns:
            CalculationResult对象
        """
        steps = []
        try:
            steps.append(f"布拉格方程: 2d sin(θ) = nλ")
            steps.append(f"n = {n} (衍射级数)")
            steps.append(f"λ = {wavelength} Å")
            steps.append(f"2θ = {two_theta}°")

            theta = two_theta / 2
            steps.append(f"θ = {two_theta}° / 2 = {theta}°")

            theta_rad = math.radians(theta)
            sin_theta = math.sin(theta_rad)
            steps.append(f"sin({theta}°) = {sin_theta:.4f}")

            d = (n * wavelength) / (2 * sin_theta)
            steps.append(f"d = ({n} × {wavelength}) / (2 × {sin_theta:.4f}) = {d:.2f} Å")

            return CalculationResult(
                success=True,
                value=d,
                unit='Å',
                formula='2d sin(θ) = nλ',
                steps=steps
            )

        except Exception as e:
            return CalculationResult(
                success=False,
                value=0.0,
                unit='Å',
                formula='2d sin(θ) = nλ',
                steps=steps,
                error=str(e)
            )

    def calculate_atomic_packing_factor(self, structure: str) -> CalculationResult:
        """
        计算原子堆积因子 APF

        Args:
            structure: 晶体结构类型 ('SC', 'BCC', 'FCC', 'HCP')

        Returns:
            CalculationResult对象
        """
        steps = []
        try:
            steps.append(f"原子堆积因子 APF = (晶胞中原子总体积) / (晶胞体积)")

            if structure.upper() == 'SC':  # 简单立方
                steps.append("简单立方 (SC) 结构:")
                steps.append("  - 晶胞原子数 N = 1")
                steps.append("  - 晶胞边长 a = 2r")
                steps.append("  - APF = (1 × 4/3 π r³) / (2r)³ = π/6 ≈ 0.52")
                apf = math.pi / 6

            elif structure.upper() == 'BCC':  # 体心立方
                steps.append("体心立方 (BCC) 结构:")
                steps.append("  - 晶胞原子数 N = 2")
                steps.append("  - 体对角线 √3 a = 4r → a = 4r/√3")
                steps.append("  - APF = (2 × 4/3 π r³) / (4r/√3)³ = π√3/8 ≈ 0.68")
                apf = math.pi * math.sqrt(3) / 8

            elif structure.upper() == 'FCC':  # 面心立方
                steps.append("面心立方 (FCC) 结构:")
                steps.append("  - 晶胞原子数 N = 4")
                steps.append("  - 面对角线 √2 a = 4r → a = 4r/√2 = 2√2 r")
                steps.append("  - APF = (4 × 4/3 π r³) / (2√2 r)³ = π√2/6 ≈ 0.74")
                apf = math.pi * math.sqrt(2) / 6

            elif structure.upper() == 'HCP':  # 六方最密堆积
                steps.append("六方最密堆积 (HCP) 结构:")
                steps.append("  - 晶胞原子数 N = 6")
                steps.append("  - c/a 理想比 = 1.633")
                steps.append("  - APF ≈ 0.74 (与FCC相同)")
                apf = math.pi * math.sqrt(2) / 6

            else:
                raise ValueError(f"未知晶体结构: {structure}")

            steps.append(f"原子堆积因子 APF = {apf:.4f} = {apf*100:.1f}%")

            return CalculationResult(
                success=True,
                value=apf,
                unit='(无量纲)',
                formula='APF = V_atoms / V_cell',
                steps=steps
            )

        except Exception as e:
            return CalculationResult(
                success=False,
                value=0.0,
                unit='(无量纲)',
                formula='APF calculation',
                steps=steps,
                error=str(e)
            )


class MaterialScienceAgent:
    """材料科学综合计算Agent - 集成所有功能"""

    def __init__(self):
        self.mol_agent = MolecularFormulaAgent()
        self.thermo_agent = ThermodynamicsAgent()
        self.crystal_agent = CrystalAgent()

    def interactive_calculator(self):
        """交互式计算界面"""
        print("=" * 60)
        print("材料科学计算Agent v1.0")
        print("基于DeepSeek R1数学推理能力")
        print("=" * 60)
        print()

        while True:
            print("请选择计算类型:")
            print("  1. 摩尔质量计算")
            print("  2. 元素质量百分比")
            print("  3. 反应焓变计算")
            print("  4. Gibbs自由能计算")
            print("  5. 平衡常数计算")
            print("  6. 晶体密度计算")
            print("  7. 布拉格方程（晶面间距）")
            print("  8. 原子堆积因子")
            print("  0. 退出")
            print()

            choice = input("请输入选项 (0-8): ").strip()

            if choice == '0':
                print("感谢使用！")
                break

            elif choice == '1':
                formula = input("请输入分子式: ").strip()
                result = self.mol_agent.calculate_molar_mass(formula)
                self._print_result(result)

            elif choice == '2':
                formula = input("请输入分子式: ").strip()
                element = input("请输入目标元素符号: ").strip()
                result = self.mol_agent.calculate_mass_percent(formula, element)
                self._print_result(result)

            elif choice == '3':
                print("铝热反应示例: 2Al + Fe2O3 → Al2O3 + 2Fe")
                reactants = {'Al': 2, 'Fe2O3': 1}
                products = {'Al2O3': 1, 'Fe': 2}
                result = self.thermo_agent.calculate_reaction_enthalpy(
                    reactants, products)
                self._print_result(result)

            elif choice == '4':
                delta_h = float(input("请输入ΔH° (kJ/mol): "))
                delta_s = float(input("请输入ΔS° (J/(mol·K)): "))
                temp = float(input("请输入温度 (K, 默认298): ") or "298")
                result = self.thermo_agent.calculate_gibbs_free_energy(
                    delta_h, delta_s, temp)
                self._print_result(result)

            elif choice == '5':
                delta_g = float(input("请输入ΔG° (kJ/mol): "))
                temp = float(input("请输入温度 (K, 默认298): ") or "298")
                result = self.thermo_agent.calculate_equilibrium_constant(
                    delta_g, temp)
                self._print_result(result)

            elif choice == '6':
                formula = input("请输入分子式: ").strip()
                z = int(input("请输入晶胞中化学式单元数 Z: "))
                a = float(input("请输入晶胞参数 a (Å): "))
                result = self.crystal_agent.calculate_crystal_density(
                    formula, z, a)
                self._print_result(result)

            elif choice == '7':
                wavelength = float(input("请输入X射线波长 (Å, 默认1.54): ") or "1.54")
                two_theta = float(input("请输入衍射角 2θ (度): "))
                n = int(input("请输入衍射级数 n (默认1): ") or "1")
                result = self.crystal_agent.bragg_equation(
                    wavelength, two_theta, n)
                self._print_result(result)

            elif choice == '8':
                structure = input("请输入晶体结构 (SC/BCC/FCC/HCP): ").strip()
                result = self.crystal_agent.calculate_atomic_packing_factor(
                    structure)
                self._print_result(result)

            else:
                print("无效选项，请重新输入！")

            print()

    def _print_result(self, result: CalculationResult):
        """打印计算结果"""
        print()
        print("-" * 50)
        if result.success:
            print("✅ 计算成功!")
            print(f"计算公式: {result.formula}")
            print(f"计算结果: {result.value:.4f} {result.unit}")
            print()
            print("详细推导过程:")
            for i, step in enumerate(result.steps, 1):
                print(f"  {i}. {step}")
        else:
            print(f"❌ 计算失败: {result.error}")
            print("已执行的步骤:")
            for i, step in enumerate(result.steps, 1):
                print(f"  {i}. {step}")
        print("-" * 50)
# SOP: 数据分析标准化流程

> 适用场景: 材料科学数据处理、图表生成、统计分析
> 版本: v1.0 | 2026-04-23

---

## 1. 场景概述

利用 OpenClaw 的 AI 能力和工具链进行材料科学研究中的数据分析，包括数据清洗、统计分析、图表生成、趋势分析等。

**涉及能力：**
- Python 脚本执行（exec）
- 文件读取与写入（read/write）
- 数据可视化（matplotlib/seaborn/plotly）
- 大模型分析推理
- 数据格式转换

---

## 2. 前置条件

- [ ] OpenClaw 已正常运行
- [ ] Python 3.10+ 已安装
- [ ] 必要 Python 包已安装 (pandas, numpy, matplotlib, seaborn, scipy)
- [ ] 待分析数据已准备（CSV/Excel/JSON/txt 格式）

---

## 3. 标准流程

### 3.1 阶段一：数据导入与预览

```
用户指令示例:
"读取桌面上的 'calcium_titanate_data.csv' 文件，显示前10行
和基本统计信息。"

系统执行:
1. 读取 CSV 文件
2. 显示数据概览（行数、列数、数据类型）
3. 显示基本统计（均值、方差、最大/最小值）
4. 检查缺失值和异常值
```

**支持的数据格式：**

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| CSV | .csv | 标准表格数据 |
| Excel | .xlsx, .xls | Excel 工作簿 |
| JSON | .json | 结构化数据 |
| TXT | .txt | 文本数据 |
| HDF5 | .h5 | 科学计算大文件 |
| NPY/NPZ | .npy, .npz | NumPy 格式 |
| CIF | .cif | 材料晶体结构 |

### 3.2 阶段二：数据清洗

```
用户指令示例:
"删除空值行，将温度列转换为摄氏度，错误数据标记为-999的值替换为中位数。"

系统执行:
1. 识别并处理缺失值
2. 检查并处理异常值（IQR/Z-score 方法）
3. 数据类型转换
4. 数据去重
5. 生成清洗报告
```

### 3.3 阶段三：探索性数据分析 (EDA)

```
用户指令示例:
"对所有数值列进行相关性分析，生成热力图。重点分析
bandgap 与 composition 之间的关系。"

系统执行:
1. 计算相关系数矩阵
2. 生成热力图
3. 分析关键特征关系
4. 生成分布直方图
5. 输出分析结论
```

### 3.4 阶段四：专业分析

**材料科学场景：**

```
"对我计算的钙钛矿 bandgap 数据进行分析，
筛选出 bandgap 在 1.2-1.8 eV 之间的候选材料，
按稳定性排序。"

系统输出:
1. 条件筛选结果
2. 排序后的材料列表
3. 最佳候选材料（top 10）
4. 可视化分布图
```

### 3.5 阶段五：图表生成

```
用户指令示例:
"生成一张 publication-ready 的图表：x轴为温度(K)，
y轴为电导率(S/cm)，使用不同颜色区分不同掺杂比例，
添加误差棒和图例。"

图表输出格式:
- PNG (默认，适合快速查看)
- PDF (出版级矢量图)
- SVG (网页展示)
- TIFF (期刊投稿)
```

**图表质量标准：**
```
- 分辨率: ≥300 DPI (出版标准)
- 字体: Times New Roman / Arial (期刊标准)
- 尺寸: 单栏 8.5cm / 双栏 17.8cm
- 格式: PDF 矢量图优先
- 配色: 色盲友善配色方案
```

### 3.6 阶段六：报告生成

```
用户指令示例:
"将以上分析结果整理成一份完整的分析报告，
包含数据概述、分析方法、结果图表和结论。"
```

---

## 4. 典型分析工作流

### 4.1 高通量筛选分析

```
输入: 计算数据库（含数千个材料的数据）
流程: 
  1. 数据导入并验证完整性
  2. 条件过滤（带隙、稳定性、成本）
  3. 多目标优化（Pareto前沿分析）
  4. 候选材料排名
  5. 结果可视化和报告输出
```

### 4.2 机器学习辅助分析

```
输入: 实验/计算数据 (CSV)
流程:
  1. 数据分析（EDA）
  2. 特征工程（特征选择 + 构建）
  3. 模型训练（随机森林 / XGBoost / 神经网络）
  4. 模型评估（交叉验证 + SHAP分析）
  5. 预测结果与可视化
```

### 4.3 统计假设检验

```
输入: 两组或多组实验数据
流程:
  1. 正态性检验（Shapiro-Wilk）
  2. 方差齐性检验（Levene）
  3. 选择合适的检验方法（t-test / ANOVA / Mann-Whitney）
  4. 执行统计分析
  5. 生成结果报告
```

---

## 5. 工具链配置

### 5.1 Python 包安装

```bash
# 核心数据分析包
pip install pandas numpy scipy matplotlib seaborn
pip install scikit-learn  # 机器学习
pip install plotly        # 交互式图表
pip install openpyxl      # Excel读写
pip install pymatgen      # 材料科学专用

# 按需安装
pip install xgboost lightgbm  # 高性能模型
pip install shap lime          # 模型可解释性
```

### 5.2 OpenClaw 技能联动

```bash
# 技能列表
- paper-fetcher: 搜索相关方法论文
- mol-vision: 分子结构可视化
- zotero-local-import: 保存引用
```

---

## 6. 输出规范

### 6.1 文件命名

```
格式: {project}_{analysis_type}_{date}.{ext}
示例: perovskite_bandgap_analysis_20260423.pdf
```

### 6.2 输出目录

```
~/openclaw/workspace/output/analysis/
├── data/        # 处理后的数据文件
├── figures/     # 图表文件
├── reports/     # 分析报告
└── models/      # ML模型文件
```

### 6.3 代码保存

所有执行的 Python 分析代码自动保存到：

```
~/openclaw/workspace/output/analysis/scripts/
```

---

## 7. 质量保证

### 7.1 结果验证

- [ ] 数据清洗前后对比报告
- [ ] 统计结果可复现
- [ ] 图表特征标注完整
- [ ] 结论有数据支撑
- [ ] 异常值已说明处理方式

### 7.2 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 中文字符显示乱码 | 字体缺失 | 安装 SimHei 或中文字体 |
| 数据量过大处理慢 | 内存不足 | 分批处理或采样 |
| matplotlib 图表模糊 | DPI设置低 | 设置 dpi=300 |
| Excel 文件读取失败 | 格式不兼容 | 转为 CSV 处理 |

### 7.3 复现性保证

```python
# 每次分析脚本开头加入：
import numpy as np
np.random.seed(42)  # 固定随机种子

# 记录环境信息：
import platform, sys
print(f"Python {sys.version}")
print(f"Platform: {platform.platform()}")
```

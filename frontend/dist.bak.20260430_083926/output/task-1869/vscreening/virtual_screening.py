#!/usr/bin/env python3
"""
丁二烯氢氰化配体虚拟筛选
生成1000+候选配体并进行选择性预测
"""

import pandas as pd
import numpy as np
import pickle
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors
import warnings
warnings.filterwarnings('ignore')

# 加载训练好的模型
with open('/Users/mettlyz/.openclaw/workspace/output/task-1869/model/selectivity_model.pkl', 'rb') as f:
    model = pickle.load(f)

print("模型加载成功!")

# ============ 1. 配体模板库 ============
# 定义各种取代基
aryl_substituents = [
    '', 'H', 'Me', 'Et', 'iPr', 'tBu', 'OMe', 'OEt', 'F', 'Cl', 'Br',
    'CF3', 'CN', 'NO2', 'NH2', 'NMe2', 'Ph', 'SMe', 'SO2Me'
]

alkyl_groups = [
    'Me', 'Et', 'nPr', 'iPr', 'nBu', 'iBu', 'tBu', 'cHex', 'Ph',
    'CH2Ph', 'CH2CH2Ph'
]

# 骨架模板
ligand_templates = []

# 单齿亚磷酸酯模板: P(OAr)3
for r1 in ['H', 'Me', 'iPr', 'tBu', 'OMe', 'F', 'Cl', 'CF3']:
    for r2 in ['H', 'Me', 'OMe', 'F']:
        for r3 in ['H', 'Me', 'OMe']:
            template = {
                'type': 'phosphite',
                'denticity': 1,
                'substitution': f"2-{r1}_4-{r2}_6-{r3}",
                'r_positions': [r1, r2, r3]
            }
            ligand_templates.append(template)

# 双齿亚磷酸酯模板: (ArO)2P-O-(CH2)n-P(OAr)2
for n in [2, 3, 4, 5, 6]:
    for r in ['H', 'Me', 'iPr', 'tBu', 'OMe', 'F', 'Cl']:
        template = {
            'type': 'diphosphite',
            'denticity': 2,
            'bridge_length': n,
            'substitution': f"2-{r}",
        }
        ligand_templates.append(template)

# 双齿膦配体模板: Ph2P-(CH2)n-PPh2
for n in [1, 2, 3, 4, 5, 6]:
    for ring_sub in ['H', 'Me', 'OMe', 'F', 'CF3']:
        template = {
            'type': 'diphosphine',
            'denticity': 2,
            'bridge_length': n,
            'substitution': f"4-{ring_sub}",
        }
        ligand_templates.append(template)

# 单齿膦配体: PAr3
for r1 in ['H', 'Me', 'iPr', 'tBu', 'OMe', 'F', 'Cl', 'CF3', 'NMe2']:
    for r2 in ['H', 'Me', 'OMe', 'F']:
        for r3 in ['H', 'Me', 'OMe', 'F', 'Cl']:
            template = {
                'type': 'phosphine',
                'denticity': 1,
                'substitution': f"2-{r1}_4-{r2}_6-{r3}",
                'r_positions': [r1, r2, r3]
            }
            ligand_templates.append(template)

print(f"生成模板数量: {len(ligand_templates)}")

# ============ 2. 条件变量 ============
temperatures = [60, 70, 80, 90, 100, 110, 120, 130]
solvents = ['toluene', 'THF', 'dioxane', 'hexane', 'benzene', 'xylene']
solvent_mapping = {'toluene': 0, 'THF': 1, 'dioxane': 2, 'hexane': 3, 'benzene': 4, 'xylene': 5}
ligand_class_mapping = {'phosphine': 0, 'phosphite': 1, 'diphosphine': 2, 'diphosphite': 3}

# ============ 3. 生成候选配体 ============
candidates = []

for template in ligand_templates:
    for temp in temperatures:
        for solvent in solvents:
            # 计算描述符
            dent = template['denticity']
            
            # 根据配体类型和取代基估算描述符
            lig_type = template['type']
            sub = template['substitution']
            
            # 分子量估算
            if lig_type == 'phosphite':
                base_mw = 310  # P(OPh)3
                mw_mod = sub.count('Me') * 14 + sub.count('iPr') * 42 + sub.count('tBu') * 56
                mw_mod += sub.count('OMe') * 30 + sub.count('Cl') * 34 + sub.count('F') * 18
                mw_mod += sub.count('CF3') * 68
                MW = base_mw + mw_mod
                LogP = 5.0 + sub.count('Me') * 0.5 + sub.count('tBu') * 1.5 - sub.count('OMe') * 0.3
                TPSA = 28.0
                P_atoms = 1
                O_atoms = 3
            elif lig_type == 'diphosphite':
                base_mw = 620
                n = template['bridge_length']
                mw_mod = (n - 2) * 14 + sub.count('Me') * 42
                MW = base_mw + mw_mod
                LogP = 8.0 + sub.count('Me') * 1.0
                TPSA = 56.0
                P_atoms = 2
                O_atoms = 6
            elif lig_type == 'diphosphine':
                base_mw = 426  # dppe
                n = template['bridge_length']
                mw_mod = (n - 2) * 14 + sub.count('Me') * 84
                MW = base_mw + mw_mod
                LogP = 7.5 + sub.count('Me') * 0.8
                TPSA = 13.0
                P_atoms = 2
                O_atoms = 0
            else:  # phosphine
                base_mw = 262  # PPh3
                mw_mod = sub.count('Me') * 42 + sub.count('iPr') * 126 + sub.count('tBu') * 168
                mw_mod += sub.count('OMe') * 90 + sub.count('Cl') * 102 + sub.count('F') * 54
                mw_mod += sub.count('CF3') * 204
                MW = base_mw + mw_mod
                LogP = 4.5 + sub.count('Me') * 0.6 + sub.count('tBu') * 1.8 - sub.count('OMe') * 0.2
                TPSA = 13.0
                P_atoms = 1
                O_atoms = 0 if 'OMe' not in sub else sub.count('OMe')
            
            NumRotatableBonds = 6 + (dent - 1) * 3 + sub.count('iPr') + sub.count('tBu')
            NumRings = 3 * P_atoms
            NumHDonors = 0
            NumHAcceptors = O_atoms
            HeavyAtoms = int(MW / 13)
            
            lig_class = lig_type
            
            candidates.append({
                'ligand_name': f"{lig_type}_{template.get('substitution', 'none')}_T{temp}_{solvent}",
                'ligand_type': lig_type,
                'denticity': dent,
                'temperature': temp,
                'solvent': solvent,
                'ligand_class': lig_class,
                'MW': MW,
                'LogP': LogP,
                'TPSA': TPSA,
                'NumHDonors': NumHDonors,
                'NumHAcceptors': NumHAcceptors,
                'NumRotatableBonds': NumRotatableBonds,
                'NumRings': NumRings,
                'P_atoms': P_atoms,
                'O_atoms': O_atoms,
                'HeavyAtoms': HeavyAtoms,
            })

print(f"生成候选配体数: {len(candidates)}")

# 创建DataFrame
df_candidates = pd.DataFrame(candidates)

# ============ 4. 进行预测 ============
features = ['MW', 'LogP', 'TPSA', 'NumHDonors', 'NumHAcceptors',
            'NumRotatableBonds', 'NumRings', 'P_atoms', 'O_atoms',
            'HeavyAtoms', 'temperature', 'denticity', 'solvent', 'ligand_class']

# 准备预测数据
X_predict = df_candidates[features].copy()

# 进行预测
predictions = model.predict(X_predict)
df_candidates['predicted_selectivity'] = predictions

# 去重（保留每个配体在标准条件下的最佳预测）
standard_df = df_candidates[df_candidates['temperature'] == 100].copy()
unique_ligands = standard_df.sort_values('predicted_selectivity', ascending=False)
unique_ligands = unique_ligands.drop_duplicates(subset=['ligand_name'])

print(f"唯一配体数量: {len(unique_ligands)}")

# ============ 5. 结果分析 ============
# 按配体类型统计
print(f"\n按配体类型统计平均选择性:")
print(unique_ligands.groupby('ligand_class')['predicted_selectivity'].agg(['count', 'mean', 'min', 'max']).round(1))

# Top 10 配体
top_10 = unique_ligands.nlargest(10, 'predicted_selectivity')
print(f"\n{'='*80}")
print(f"Top 10 高选择性配体")
print(f"{'='*80}")
print(top_10[['ligand_name', 'ligand_class', 'denticity', 'predicted_selectivity', 'MW', 'LogP']].to_string(index=False))

# Top 3 进行DFT验证
top_3 = unique_ligands.nlargest(3, 'predicted_selectivity')
print(f"\n{'='*80}")
print(f"Top 3 候选配体 (用于DFT验证):")
print(f"{'='*80}")
for i, (_, row) in enumerate(top_3.iterrows(), 1):
    print(f"\n配体 #{i}: {row['ligand_name']}")
    print(f"  类型: {row['ligand_class']}")
    print(f"  预测选择性: {row['predicted_selectivity']:.1f}%")
    print(f"  配位原子数: {row['denticity']}")
    print(f"  分子量: {row['MW']:.1f}")

# ============ 6. 保存结果 ============
output_dir = '/Users/mettlyz/.openclaw/workspace/output/task-1869/vscreening/'

# 保存所有预测结果
df_candidates.to_csv(output_dir + 'all_candidates_predictions.csv', index=False)

# 保存Top配体
unique_ligands.to_csv(output_dir + 'unique_ligands_ranked.csv', index=False)
top_10.to_csv(output_dir + 'top_10_candidates.csv', index=False)
top_3.to_csv(output_dir + 'top_3_for_dft.csv', index=False)

# 配体类分布分析
class_analysis = unique_ligands.groupby('ligand_class').agg({
    'predicted_selectivity': ['mean', 'median', 'max', 'min', 'count'],
    'MW': 'mean'
}).round(1)

class_analysis.to_csv(output_dir + 'ligand_class_analysis.csv')

print(f"\n{'='*80}")
print(f"虚拟筛选完成!")
print(f"{'='*80}")
print(f"- 生成配体总数: {len(df_candidates)}")
print(f"- 唯一配体数: {len(unique_ligands)}")
print(f"- 最高预测选择性: {unique_ligands['predicted_selectivity'].max():.1f}%")
print(f"- 最低预测选择性: {unique_ligands['predicted_selectivity'].min():.1f}%")
print(f"- 平均预测选择性: {unique_ligands['predicted_selectivity'].mean():.1f}%")
print(f"\n结果已保存至: {output_dir}")
print(f"  - all_candidates_predictions.csv")
print(f"  - unique_ligands_ranked.csv")
print(f"  - top_10_candidates.csv")
print(f"  - top_3_for_dft.csv")

#!/usr/bin/env python3
"""
丁二烯氢氰化配体选择性预测模型
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.linear_model import Ridge
from sklearn.svm import SVR

import xgboost as xgb
import lightgbm as lgb

import warnings
warnings.filterwarnings('ignore')

# 读取数据
df = pd.read_csv('/Users/mettlyz/.openclaw/workspace/output/task-1869/dataset/ligand_dataset.csv')
# print(f"数据集大小: {df.shape}")
# print(f"列名: {df.columns.tolist()}")

# 特征选择
numerical_features = ['MW', 'LogP', 'TPSA', 'NumHDonors', 'NumHAcceptors',
                      'NumRotatableBonds', 'NumRings', 'P_atoms', 'O_atoms',
                      'HeavyAtoms', 'temperature']
categorical_features = ['denticity', 'solvent', 'ligand_class']
all_features = numerical_features + categorical_features

# 目标变量
y = df['linear_selectivity']
X = df[all_features]

# print(f"\n特征数: {len(all_features)}")
# print(f"- 数值特征: {len(numerical_features)}")
# print(f"- 类别特征: {len(categorical_features)}")

# 划分训练集测试集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=df['ligand_class']
)

# print(f"\n训练集大小: {X_train.shape}")
# print(f"测试集大小: {X_test.shape}")

# 预处理管道
preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), numerical_features),
        ('cat', OneHotEncoder(drop='first', sparse_output=False), categorical_features)
    ])

# 模型比较
models = {
    'Ridge Regression': Ridge(random_state=42),
    'Random Forest': RandomForestRegressor(random_state=42, n_jobs=-1),
    'Gradient Boosting': GradientBoostingRegressor(random_state=42),
    'XGBoost': xgb.XGBRegressor(random_state=42, n_jobs=-1),
    'LightGBM': lgb.LGBMRegressor(random_state=42, verbose=-1),
    'SVR': SVR(),
}

results = {}
# print(f"\n{'='*60}")
# print(f"模型训练与比较")
# print(f"{'='*60}")

for name, model in models.items():
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', model)
    ])
    
    # 交叉验证
    cv_scores = cross_val_score(pipeline, X_train, y_train, 
                               cv=5, scoring='r2', n_jobs=-1)
    
    # 训练并预测
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    
    # 评估指标
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    
    # 计算"准确率"（预测值在真实值±5%范围内的比例）
    accuracy_5 = np.mean(np.abs(y_pred - y_test) <= 5)
    accuracy_3 = np.mean(np.abs(y_pred - y_test) <= 3)
    
    results[name] = {
        'cv_mean': cv_scores.mean(),
        'cv_std': cv_scores.std(),
        'r2': r2,
        'mae': mae,
        'rmse': rmse,
        'accuracy_5%': accuracy_5,
        'accuracy_3%': accuracy_3,
        'pipeline': pipeline
    }
    
    # print(f"\n{name}:")
    # print(f"  CV R²: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    # print(f"  Test R²: {r2:.4f}")
    # print(f"  MAE: {mae:.2f} %")
    # print(f"  RMSE: {rmse:.2f} %")
    # print(f"  准确率(±5%): {accuracy_5:.1%}")
    # print(f"  准确率(±3%): {accuracy_3:.1%}")

# 找出最佳模型
best_model_name = max(results.keys(), key=lambda x: results[x]['r2'])
# print(f"\n{'='*60}")
# print(f"最佳模型: {best_model_name}")
# print(f"R² = {results[best_model_name]['r2']:.4f}")
# print(f"{'='*60}")

# 优化最佳模型
# print(f"\n优化最佳模型: {best_model_name}...")

if best_model_name == 'XGBoost':
    param_grid = {
        'regressor__n_estimators': [100, 200, 300],
        'regressor__max_depth': [3, 5, 7],
        'regressor__learning_rate': [0.01, 0.05, 0.1],
        'regressor__subsample': [0.8, 0.9, 1.0],
    }
    base_model = xgb.XGBRegressor(random_state=42, n_jobs=-1)
elif best_model_name == 'LightGBM':
    param_grid = {
        'regressor__n_estimators': [100, 200, 300],
        'regressor__max_depth': [3, 5, 7, -1],
        'regressor__learning_rate': [0.01, 0.05, 0.1],
    }
    base_model = lgb.LGBMRegressor(random_state=42, verbose=-1)
elif best_model_name == 'Random Forest':
    param_grid = {
        'regressor__n_estimators': [100, 200, 300],
        'regressor__max_depth': [None, 10, 20, 30],
        'regressor__min_samples_split': [2, 5, 10],
    }
    base_model = RandomForestRegressor(random_state=42, n_jobs=-1)
else:
    param_grid = {
        'regressor__n_estimators': [100, 200],
        'regressor__max_depth': [3, 5, 7],
    }
    base_model = GradientBoostingRegressor(random_state=42)

pipeline = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('regressor', base_model)
])

grid_search = GridSearchCV(pipeline, param_grid, cv=5, 
                          scoring='r2', n_jobs=-1, verbose=0)
grid_search.fit(X_train, y_train)

# print(f"\n最佳参数: {grid_search.best_params_}")
# print(f"最佳CV R²: {grid_search.best_score_:.4f}")

# 评估优化后的模型
best_pipeline = grid_search.best_estimator_
y_pred_best = best_pipeline.predict(X_test)

r2_best = r2_score(y_test, y_pred_best)
mae_best = mean_absolute_error(y_test, y_pred_best)
rmse_best = np.sqrt(mean_squared_error(y_test, y_pred_best))
accuracy_5_best = np.mean(np.abs(y_pred_best - y_test) <= 5)
accuracy_3_best = np.mean(np.abs(y_pred_best - y_test) <= 3)

# print(f"\n优化后模型性能:")
# print(f"  Test R²: {r2_best:.4f}")
# print(f"  MAE: {mae_best:.2f} %")
# print(f"  RMSE: {rmse_best:.2f} %")
# print(f"  准确率(±5%): {accuracy_5_best:.1%}")
# print(f"  准确率(±3%): {accuracy_3_best:.1%}")

# 特征重要性分析
if hasattr(best_pipeline.named_steps['regressor'], 'feature_importances_'):
    # 获取特征名
    ohe = best_pipeline.named_steps['preprocessor'].named_transformers_['cat']
    cat_feature_names = ohe.get_feature_names_out(categorical_features).tolist()
    all_feature_names = numerical_features + cat_feature_names
    
    importances = best_pipeline.named_steps['regressor'].feature_importances_
    
    feat_imp = pd.DataFrame({
        'feature': all_feature_names,
        'importance': importances
    }).sort_values('importance', ascending=False)
    
    # print(f"\n特征重要性Top 10:")
    # print(feat_imp.head(10).to_string(index=False))
    
    # 保存特征重要性
    feat_imp.to_csv('/Users/mettlyz/.openclaw/workspace/output/task-1869/model/feature_importance.csv',
                   index=False)

# 绘制预测结果图
plt.figure(figsize=(10, 8))
plt.scatter(y_test, y_pred_best, alpha=0.6, s=50)
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 
         'r--', lw=2, label='Perfect Prediction')
plt.xlabel('Experimental Linear Selectivity (%)', fontsize=12)
plt.ylabel('Predicted Linear Selectivity (%)', fontsize=12)
plt.title(f'Predicted vs. Experimental Selectivity\n{best_model_name} (R² = {r2_best:.3f})', 
          fontsize=14)
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('/Users/mettlyz/.openclaw/workspace/output/task-1869/model/prediction_plot.png', dpi=300)
plt.close()

# 残差图
plt.figure(figsize=(10, 6))
residuals = y_test - y_pred_best
plt.scatter(y_pred_best, residuals, alpha=0.6)
plt.axhline(y=0, color='r', linestyle='--')
plt.xlabel('Predicted Selectivity (%)', fontsize=12)
plt.ylabel('Residuals (%)', fontsize=12)
plt.title('Residual Plot', fontsize=14)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('/Users/mettlyz/.openclaw/workspace/output/task-1869/model/residual_plot.png', dpi=300)
plt.close()

# 按配体类别评估
# print(f"\n按配体类别预测性能:")
for lig_class in df['ligand_class'].unique():
    mask = X_test['ligand_class'] == lig_class
    if mask.sum() > 0:
        r2_class = r2_score(y_test[mask], y_pred_best[mask])
        mae_class = mean_absolute_error(y_test[mask], y_pred_best[mask])
        # print(f"  {lig_class:15s}: R² = {r2_class:.3f}, MAE = {mae_class:.2f}% (n={mask.sum()})")

# 保存模型报告
report = f"""
{'='*60}
丁二烯氢氰化配体选择性预测模型报告
{'='*60}

1. 数据集信息:
   - 总样本数: {len(df)}
   - 训练集: {len(X_train)}
   - 测试集: {len(X_test)}
   - 特征数: {len(all_features)}

2. 最佳模型: {best_model_name}
   
3. 模型性能:
   - 交叉验证 R²: {grid_search.best_score_:.4f}
   - 测试集 R²: {r2_best:.4f}
   - MAE: {mae_best:.2f} %
   - RMSE: {rmse_best:.2f} %
   - 准确率(±5%范围内): {accuracy_5_best:.1%}
   - 准确率(±3%范围内): {accuracy_3_best:.1%}

4. 最佳参数:
   {grid_search.best_params_}

5. 数据集构成:
   {df['ligand_class'].value_counts().to_string()}

{'='*60}
模型训练完成!
{'='*60}
"""

# print(report)

with open('/Users/mettlyz/.openclaw/workspace/output/task-1869/model/model_report.txt', 'w') as f:
    f.write(report)

# 保存模型
import pickle
model_path = '/Users/mettlyz/.openclaw/workspace/output/task-1869/model/selectivity_model.pkl'
with open(model_path, 'wb') as f:
    pickle.dump(best_pipeline, f)

# print(f"\n模型已保存: {model_path}")
# print(f"报告已保存: /Users/mettlyz/.openclaw/workspace/output/task-1869/model/model_report.txt")

#!/usr/bin/env python3
"""
更新前端 LLMConfigs.tsx，添加"暂无今日数据"提示
"""

import os

file_path = os.path.join(os.path.dirname(__file__), '../frontend/src/pages/LLMConfigs.tsx')
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 旧的代码
old_code = '''      {/* Token 使用与费用统计 */}
      {(stats?.total_cost !== undefined || tokenStats) && (
        <div className="card" style={{ marginBottom: '20px', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
          <div style={{ padding: '20px' }}>
            <h4 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.5rem' }}>💰</span>
              Token 使用与费用统计
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '16px' }}>
              {/* 今日费用 */}
              <div style={{ 
                background: 'rgba(255,255,255,0.15)', 
                borderRadius: '12px', 
                padding: '16px',
                backdropFilter: 'blur(10px)'
              }}>
                <div style={{ fontSize: '0.85rem', opacity: 0.9, marginBottom: '4px' }}>今日费用</div>
                <div style={{ fontSize: '1.8rem', fontWeight: 700 }}>
                  ${stats?.today_cost?.toFixed(4) || '0.0000'}
                </div>
                <div style={{ fontSize: '0.75rem', opacity: 0.7 }}>USD</div>
              </div>'''

# 新的代码（添加"暂无今日数据"提示）
new_code = '''      {/* Token 使用与费用统计 */}
      {(stats?.total_cost !== undefined || tokenStats) && (
        <div className="card" style={{ marginBottom: '20px', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
          <div style={{ padding: '20px' }}>
            <h4 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.5rem' }}>💰</span>
              Token 使用与费用统计
            </h4>
            
            {/* 暂无今日数据提示 */}
            {(!stats?.today_cost || stats.today_cost === 0) && (
              <div style={{ 
                background: 'rgba(255,255,255,0.1)', 
                borderRadius: '8px', 
                padding: '12px',
                marginBottom: '16px',
                textAlign: 'center',
                fontSize: '0.9rem',
                opacity: 0.9
              }}>
                📊 暂无今日数据 - 开始使用 LLM 后会自动记录费用
              </div>
            )}
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '16px' }}>
              {/* 今日费用 */}
              <div style={{ 
                background: 'rgba(255,255,255,0.15)', 
                borderRadius: '12px', 
                padding: '16px',
                backdropFilter: 'blur(10px)'
              }}>
                <div style={{ fontSize: '0.85rem', opacity: 0.9, marginBottom: '4px' }}>今日费用</div>
                <div style={{ fontSize: '1.8rem', fontWeight: 700 }}>
                  ${stats?.today_cost?.toFixed(4) || '0.0000'}
                </div>
                <div style={{ fontSize: '0.75rem', opacity: 0.7 }}>USD</div>
              </div>'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print("✅ 已添加'暂无今日数据'提示")
else:
    print("❌ 未找到要替换的代码")
    import sys
    sys.exit(1)

# 保存
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ LLMConfigs.tsx 已更新")

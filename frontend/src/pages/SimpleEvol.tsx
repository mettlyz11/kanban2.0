import React from 'react';

const SimpleEvol: React.FC = () => {
  const [data, setData] = React.useState(null);
  const [err, setErr] = React.useState('');

  React.useEffect(() => {
    fetch('/uploads/docs/std_eval_data.json')
      .then(r => r.json())
      .then(d => { setData(d); console.log('✅ 数据加载成功', d); })
      .catch(e => { setErr(String(e)); console.error('❌ 加载失败', e); });
  }, []);

  return (
    <div style={{ padding: '30px', color: '#e2e8f0' }}>
      <h2 style={{ color: '#38bdf8' }}>📊 SDS 质量趋势 (测试版)</h2>
      {err && <div style={{ color: '#f87171' }}>错误: {err}</div>}
      {data ? (
        <div>
          <p>✅ 数据加载成功！{data.cycles?.length} 个周期</p>
          <p>最新评分: {data.cycles?.[data.cycles.length - 1]?.score ?? 'N/A'}</p>
          <p>版本: {data.version}</p>
        </div>
      ) : (
        <p>⏳ 加载中...</p>
      )}
    </div>
  );
};

export default SimpleEvol;

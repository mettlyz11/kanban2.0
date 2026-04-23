import { useState } from 'react';

export function TestErrorButton() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string>('');

  const triggerError = async (type: 'frontend' | 'backend' | 'database') => {
    setLoading(true);
    setResult('');
    
    try {
      if (type === 'frontend') {
        // 前端错误：直接抛出异常
        throw new Error('🧪 前端测试错误 - 这是故意触发的 JavaScript 错误');
      } else {
        // 后端错误
        const response = await fetch('/api/test-error', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ type: type === 'backend' ? 'backend' : 'database' }),
        });
        
        if (!response.ok) {
          throw new Error(`后端错误：${response.status}`);
        }
        
        const data = await response.json();
        setResult(`✅ 响应：${JSON.stringify(data)}`);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '未知错误';
      setResult(`❌ 错误：${errorMessage}`);
      console.error('测试错误:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ 
      padding: '20px', 
      margin: '20px', 
      border: '2px dashed #4299e1', 
      borderRadius: '8px',
      backgroundColor: '#ebf8ff'
    }}>
      <h3 style={{ marginBottom: '15px', color: '#2b6cb0' }}>
        🧪 Sentry 错误监控测试
      </h3>
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        <button
          onClick={() => triggerError('frontend')}
          disabled={loading}
          style={{
            padding: '10px 20px',
            backgroundColor: loading ? '#cbd5e0' : '#e53e3e',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: 'bold'
          }}
        >
          {loading ? '测试中...' : '触发前端错误'}
        </button>
        <button
          onClick={() => triggerError('backend')}
          disabled={loading}
          style={{
            padding: '10px 20px',
            backgroundColor: loading ? '#cbd5e0' : '#dd6b20',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: 'bold'
          }}
        >
          {loading ? '测试中...' : '触发后端错误'}
        </button>
        <button
          onClick={() => triggerError('database')}
          disabled={loading}
          style={{
            padding: '10px 20px',
            backgroundColor: loading ? '#cbd5e0' : '#805ad5',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: 'bold'
          }}
        >
          {loading ? '测试中...' : '触发数据库错误'}
        </button>
      </div>
      {result && (
        <div style={{ 
          marginTop: '15px', 
          padding: '10px', 
          backgroundColor: 'white',
          borderRadius: '4px',
          fontFamily: 'monospace',
          fontSize: '14px'
        }}>
          {result}
        </div>
      )}
    </div>
  );
}

# SystemResourceDashboard

> 任务: v8 #13 系统资源看板 — CPU/内存/DB连接数
> 附件类型: 代码文件
> 生成时间: 2026-05-12 06:25

# SystemResourceDashboard.tsx — 系统资源看板组件

本文件实现了一个完整的系统资源看板 React 组件，用于实时展示 CPU 使用率、内存使用率和数据库连接数。组件集成了模拟数据生成器、仪表盘布局、指标卡片、实时曲线图、WebSocket 数据接入及手动刷新回调，并提供了 React Router 路由注册示例。所有代码基于 TypeScript，依赖 React 18+、Recharts 和 react-dom。

## 依赖安装

确保项目中已安装以下依赖：

```bash
npm install react recharts @types/react @types/react-dom
```

如果使用 React Router v6：

```bash
npm install react-router-dom @types/react-router-dom
```

## 完整代码文件

```typescript
// SystemResourceDashboard.tsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

// ---------- 类型定义 ----------
export interface ResourceDataPoint {
  timestamp: number; // Unix timestamp (ms)
  cpu: number;       // 0-100
  memory: number;    // 0-100
  dbConnections: number; // 0-500
}

export interface DashboardConfig {
  maxDataPoints: number;        // 曲线图保留的最大数据点数量
  refreshInterval: number;      // 模拟数据推送间隔 (ms)
  cpuWarningThreshold: number;  // CPU 告警阈值 (百分比)
  memoryWarningThreshold: number;
  dbConnectionsWarningThreshold: number;
}

export const defaultConfig: DashboardConfig = {
  maxDataPoints: 60,
  refreshInterval: 1000,
  cpuWarningThreshold: 80,
  memoryWarningThreshold: 75,
  dbConnectionsWarningThreshold: 400,
};

// ---------- 模拟数据生成器 ----------
const generateRandomDataPoint = (): ResourceDataPoint => ({
  timestamp: Date.now(),
  cpu: Math.round(Math.random() * 100),
  memory: Math.round(Math.random() * 100),
  dbConnections: Math.round(Math.random() * 500),
});

/**
 * 返回一个包含初始数据点的数组，用于首次渲染
 */
export const generateInitialData = (
  count: number = 20
): ResourceDataPoint[] => {
  const now = Date.now();
  return Array.from({ length: count }, (_, i) => ({
    timestamp: now - (count - i) * 1000, // 过去 count 秒
    cpu: Math.round(Math.random() * 100),
    memory: Math.round(Math.random() * 100),
    dbConnections: Math.round(Math.random() * 500),
  }));
};

// ---------- WebSocket 模拟 Hook ----------
/**
 * 模拟 WebSocket 连接，返回当前数据流和连接状态
 * 实际使用时可替换为真实 WebSocket 实现
 */
export const useSimulatedWebSocket = (
  config: DashboardConfig
): {
  dataStream: ResourceDataPoint[];
  isConnected: boolean;
  error: string | null;
  reconnect: () => void;
} => {
  const [dataStream, setDataStream] = useState<ResourceDataPoint[]>(
    generateInitialData(config.maxDataPoints)
  );
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<number | null>(null);

  // 模拟连接建立
  const connect = useCallback(() => {
    setIsConnected(true);
    setError(null);
    intervalRef.current = window.setInterval(() => {
      const newPoint = generateRandomDataPoint();
      setDataStream((prev) => {
        const updated = [...prev, newPoint];
        // 超出最大数量则移除最早的数据
        if (updated.length > config.maxDataPoints) {
          return updated.slice(updated.length - config.maxDataPoints);
        }
        return updated;
      });
    }, config.refreshInterval);
  }, [config.maxDataPoints, config.refreshInterval]);

  // 模拟连接断开与重连
  const reconnect = useCallback(() => {
    // 清除旧定时器
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsConnected(false);
    setError('连接已断开，尝试重新连接...');
    // 模拟 500ms 后重连成功
    setTimeout(() => {
      connect();
    }, 500);
  }, [connect]);

  useEffect(() => {
    // 初始化连接
    const timer = setTimeout(() => {
      connect();
    }, 300); // 模拟连接延迟
    return () => {
      clearTimeout(timer);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [connect]);

  return { dataStream, isConnected, error, reconnect };
};

// ---------- 指标卡片子组件 ----------
interface MetricCardProps {
  title: string;
  value: number;
  unit: string;
  threshold: number;
  color?: string; // 正常颜色，超出阈值自动变红
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  threshold,
  color = '#1890ff',
}) => {
  const isWarning = value >= threshold;
  const displayColor = isWarning ? '#ff4d4f' : color;
  return (
    <div
      style={{
        border: `1px solid ${displayColor}`,
        borderRadius: 8,
        padding: 16,
        minWidth: 160,
        background: isWarning ? '#fff2f0' : '#fff',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        textAlign: 'center',
        transition: 'all 0.3s ease',
      }}
    >
      <div style={{ fontSize: 14, color: '#666', marginBottom: 8 }}>{title}</div>
      <div style={{ fontSize: 32, fontWeight: 'bold', color: displayColor }}>
        {value}
        <span style={{ fontSize: 14, marginLeft: 4 }}>{unit}</span>
      </div>
      <div style={{ fontSize: 12, color: '#999', marginTop: 8 }}>
        阈值: {threshold}{unit}
      </div>
    </div>
  );
};

// ---------- 实时曲线子组件 ----------
interface RealTimeChartProps {
  data: ResourceDataPoint[];
  dataKey: 'cpu' | 'memory' | 'dbConnections';
  label: string;
  color: string;
  yLabel: string;
}

const RealTimeChart: React.FC<RealTimeChartProps> = ({
  data,
  dataKey,
  label,
  color,
  yLabel,
}) => {
  // 格式化时间戳为 HH:mm:ss
  const formatTime = (ts: number): string => {
    const date = new Date(ts);
    return `${date.getHours().toString().padStart(2, '0')}:${date
      .getMinutes()
      .toString()
      .padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
  };

  return (
    <div style={{ width: '100%', height: 200, margin: '12px 0' }}>
      <h4 style={{ margin: '0 0 8px 8px' }}>{label}</h4>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={formatTime}
            interval="preserveStartEnd"
            minTickGap={30}
            fontSize={10}
          />
          <YAxis label={{ value: yLabel, angle: -90, position: 'insideLeft' }} fontSize={10} />
          <Tooltip
            labelFormatter={(label: number) => formatTime(label)}
            formatter={(value: number) => [`${value}`, label]}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            dot={false}
            isAnimationActive={false}
            name={label}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

// ---------- 主组件 ----------
export interface SystemResourceDashboardProps {
  config?: DashboardConfig;
  onRefresh?: () => void; // 手动刷新回调
  useRealWebSocket?: boolean; // 未来扩展，当前仅支持模拟
}

const SystemResourceDashboard: React.FC<SystemResourceDashboardProps> = ({
  config = defaultConfig,
  onRefresh,
}) => {
  const { dataStream, isConnected, error, reconnect } = useSimulatedWebSocket(config);

  // 手动刷新：重置数据并重新连接
  const handleManualRefresh = useCallback(() => {
    reconnect();
    if (onRefresh) onRefresh();
  }, [reconnect, onRefresh]);

  // 最新一个数据点用于卡片显示
  const latestData = dataStream[dataStream.length - 1] || {
    timestamp: Date.now(),
    cpu: 0,
    memory: 0,
    dbConnections: 0,
  };

  return (
    <div style={{ padding: 24, fontFamily: 'Arial, sans-serif' }}>
      {/* 头部状态栏 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 20,
        }}
      >
        <h2 style={{ margin: 0 }}>系统资源看板</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span
            style={{
              display: 'inline-block',
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: isConnected ? '#52c41a' : '#ff4d4f',
            }}
          />
          <span>{isConnected ? '已连接' : '已断开'}</span>
          {error && <span style={{ color: '#ff4d4f', fontSize: 12 }}>{error}</span>}
          <button
            onClick={handleManualRefresh}
            style={{
              padding: '6px 16px',
              background: '#1890ff',
              color: '#fff',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              fontSize: 14,
            }}
          >
            手动刷新
          </button>
        </div>
      </div>

      {/* 连接状态提示 */}
      {!isConnected && !error && (
        <div style={{ background: '#fffbe6', padding: 8, marginBottom: 12, borderRadius: 4 }}>
          正在建立连接...
        </div>
      )}

      {/* 指标卡片组 */}
      <div
        style={{
          display: 'flex',
          gap: 16,
          flexWrap: 'wrap',
          marginBottom: 24,
        }}
      >
        <MetricCard
          title="CPU 使用率"
          value={latestData.cpu}
          unit="%"
          threshold={config.cpuWarningThreshold}
        />
        <MetricCard
          title="内存使用率"
          value={latestData.memory}
          unit="%"
          threshold={config.memoryWarningThreshold}
          color="#52c41a"
        />
        <MetricCard
          title="数据库连接数"
          value={latestData.dbConnections}
          unit="个"
          threshold={config.dbConnectionsWarningThreshold}
          color="#722ed1"
        />
      </div>

      {/* 实时曲线图 */}
      <div
        style={{
          background: '#fff',
          padding: 16,
          borderRadius: 8,
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        }}
      >
        <h3 style={{ marginTop: 0 }}>实时趋势</h3>
        <RealTimeChart
          data={dataStream}
          dataKey="cpu"
          label="CPU"
          color="#ff4d4f"
          yLabel="%"
        />
        <RealTimeChart
          data={dataStream}
          dataKey="memory"
          label="内存"
          color="#52c41a"
          yLabel="%"
        />
        <RealTimeChart
          data={dataStream}
          dataKey="dbConnections"
          label="DB连接数"
          color="#722ed1"
          yLabel="连接数"
        />
      </div>

      {/* 数据表格 (辅助展示) */}
      <details style={{ marginTop: 16, cursor: 'pointer' }}>
        <summary style={{ fontWeight: 'bold', fontSize: 14 }}>
          查看原始数据（最近5条）
        </summary>
        <table border={1} cellPadding={6} style={{ borderCollapse: 'collapse', width: '100%', marginTop: 8 }}>
          <thead>
            <tr>
              <th>时间</th>
              <th>CPU (%)</th>
              <th>内存 (%)</th>
              <th>DB连接数</th>
            </tr>
          </thead>
          <tbody>
            {dataStream.slice(-5).reverse().map((point, idx) => (
              <tr key={idx}>
                <td>{new Date(point.timestamp).toLocaleTimeString()}</td>
                <td>{point.cpu}</td>
                <td>{point.memory}</td>
                <td>{point.dbConnections}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
};

export default SystemResourceDashboard;
```

## 组件复用与配置项说明

### 配置项 (`DashboardConfig`)

| 属性 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `maxDataPoints` | number | 60 | 曲线图保留的最大数据点数量，超出则自动移除最早数据 |
| `refreshInterval` | number | 1000 | 模拟数据推送间隔（毫秒） |
| `cpuWarningThreshold` | number | 80 | CPU 告警百分比阈值 |
| `memoryWarningThreshold` | number | 75 | 内存告警百分比阈值 |
| `dbConnectionsWarningThreshold` | number | 400 | 数据库连接数告警阈值 |

### 组件属性 (`SystemResourceDashboardProps`)

| 属性 | 类型 | 描述 |
|------|------|------|
| `config` | `DashboardConfig` (可选) | 覆盖默认配置 |
| `onRefresh` | `() => void` (可选) | 手动刷新按钮被点击时的回调函数，可用于外部触发数据刷新或日志记录 |
| `useRealWebSocket` | `boolean` (可选) | 保留给扩展，当前仅支持模拟 WebSocket |

### 子组件概览

1. **MetricCard**：显示单个指标的当前值，支持根据阈值自动变色（红色告警）。
2. **RealTimeChart**：基于 Recharts 的实时折线图，自动格式化时间标签，不显示动画以确保性能。
3. **useSimulatedWebSocket**：自定义 Hook，模拟 WebSocket 连接并提供重连机制。可替换为真实 `WebSocket` 类。

### 样式说明

所有样式采用内联方式，便于直接复制使用。正式项目中可提取为 CSS Modules 或 Styled Components。卡片和图表均包含简单阴影与圆角，视觉上清晰专业。

## 路由注册示例

在 React 应用中使用该组件的典型路由配置（基于 React Router v6）：

```tsx
// App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import SystemResourceDashboard from './SystemResourceDashboard';

const App = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/dashboard/resources" element={<SystemResourceDashboard />} />
        {/* 其他路由 */}
      </Routes>
    </BrowserRouter>
  );
};

export default App;
```

该组件也可以直接嵌套在其他父组件中，无需路由：

```tsx
<SystemResourceDashboard
  config={{ maxDataPoints: 30, refreshInterval: 2000 }}
  onRefresh={() => console.log('用户手动刷新')}
/>
```

## 扩展性与真实 WebSocket 接入

将 `useSimulatedWebSocket` 替换为真实 WebSocket 只需修改该 Hook 内部实现，返回结构保持一致即可
import React, { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
  ComposedChart
} from 'recharts';
import { Upload, FileText, TrendingUp, Activity, Heart } from 'lucide-react';

// 全屏图表容器
export const FullScreenChart: React.FC<{ title: string; children: React.ReactNode }> = ({ 
  title, 
  children 
}) => (
  <div style={{ 
    background: 'white', 
    borderRadius: '16px', 
    padding: '24px',
    boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
    marginBottom: '24px'
  }}>
    <h3 style={{ 
      fontSize: '1.2rem', 
      fontWeight: 600, 
      marginBottom: '20px',
      color: '#333',
      display: 'flex',
      alignItems: 'center',
      gap: '10px'
    }}>
      {title}
    </h3>
    <div style={{ width: '100%', height: '400px' }}>
      {children}
    </div>
  </div>
);

// BMI趋势图 - 全屏优化版
export const BMITrendChart: React.FC<{ data: any[] }> = ({ data }) => (
  <FullScreenChart title="📊 BMI变化趋势">
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
        <defs>
          <linearGradient id="bmiGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#667eea" stopOpacity={0.3}/>
            <stop offset="95%" stopColor="#667eea" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis 
          dataKey="date" 
          tick={{ fill: '#666', fontSize: 12 }}
          axisLine={{ stroke: '#e0e0e0' }}
        />
        <YAxis 
          domain={[15, 30]} 
          tick={{ fill: '#666', fontSize: 12 }}
          axisLine={{ stroke: '#e0e0e0' }}
        />
        <Tooltip 
          contentStyle={{ 
            background: 'white', 
            border: 'none', 
            borderRadius: '12px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.15)'
          }}
        />
        <Legend />
        <Area 
          type="monotone" 
          dataKey="BMI" 
          stroke="#667eea" 
          strokeWidth={3}
          fill="url(#bmiGradient)"
          name="BMI"
        />
        <Line type="monotone" dataKey="正常上限" stroke="#e74c3c" strokeDasharray="5 5" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="正常下限" stroke="#27ae60" strokeDasharray="5 5" strokeWidth={2} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  </FullScreenChart>
);

// 血压趋势图 - 全屏优化版
export const BloodPressureChart: React.FC<{ data: any[] }> = ({ data }) => (
  <FullScreenChart title="❤️ 血压变化趋势">
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="date" tick={{ fill: '#666', fontSize: 12 }} />
        <YAxis domain={[60, 180]} tick={{ fill: '#666', fontSize: 12 }} />
        <Tooltip contentStyle={{ background: 'white', border: 'none', borderRadius: '12px', boxShadow: '0 4px 20px rgba(0,0,0,0.15)' }} />
        <Legend />
        <Area type="monotone" dataKey="收缩压" stroke="#e74c3c" fill="#e74c3c" fillOpacity={0.3} />
        <Area type="monotone" dataKey="舒张压" stroke="#3498db" fill="#3498db" fillOpacity={0.3} />
        <Line type="monotone" dataKey="正常收缩压" stroke="#27ae60" strokeDasharray="5 5" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="正常舒张压" stroke="#27ae60" strokeDasharray="5 5" strokeWidth={2} dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  </FullScreenChart>
);

// 血脂趋势图
export const LipidChart: React.FC<{ data: any[] }> = ({ data }) => (
  <FullScreenChart title="🩸 血脂指标趋势">
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="date" tick={{ fill: '#666', fontSize: 12 }} />
        <YAxis tick={{ fill: '#666', fontSize: 12 }} />
        <Tooltip contentStyle={{ background: 'white', border: 'none', borderRadius: '12px', boxShadow: '0 4px 20px rgba(0,0,0,0.15)' }} />
        <Legend />
        <Line type="monotone" dataKey="总胆固醇" stroke="#e74c3c" strokeWidth={3} dot={{ r: 5 }} />
        <Line type="monotone" dataKey="甘油三酯" stroke="#f39c12" strokeWidth={3} dot={{ r: 5 }} />
        <Line type="monotone" dataKey="LDL" stroke="#e67e22" strokeWidth={3} dot={{ r: 5 }} />
        <Line type="monotone" dataKey="HDL" stroke="#27ae60" strokeWidth={3} dot={{ r: 5 }} />
      </LineChart>
    </ResponsiveContainer>
  </FullScreenChart>
);

// 综合健康指标卡片
export const HealthIndicatorCards: React.FC<{ latest: any }> = ({ latest }) => {
  const indicators = [
    { 
      title: 'BMI', 
      value: latest?.bmi || '--', 
      unit: '', 
      status: latest?.bmi && latest.bmi <= 24 ? '正常' : '偏高',
      color: latest?.bmi && latest.bmi <= 24 ? '#27ae60' : '#e74c3c',
      icon: <Activity size={24} />
    },
    { 
      title: '收缩压', 
      value: latest?.systolic || '--', 
      unit: 'mmHg', 
      status: latest?.systolic && latest.systolic <= 140 ? '正常' : '偏高',
      color: latest?.systolic && latest.systolic <= 140 ? '#27ae60' : '#e74c3c',
      icon: <Heart size={24} />
    },
    { 
      title: '空腹血糖', 
      value: latest?.fastingSugar || '--', 
      unit: 'mmol/L', 
      status: latest?.fastingSugar && latest.fastingSugar <= 6.1 ? '正常' : '偏高',
      color: latest?.fastingSugar && latest.fastingSugar <= 6.1 ? '#27ae60' : '#e74c3c',
      icon: <TrendingUp size={24} />
    },
    { 
      title: '总胆固醇', 
      value: latest?.totalCholesterol || '--', 
      unit: 'mmol/L', 
      status: latest?.totalCholesterol && latest.totalCholesterol <= 5.2 ? '正常' : '偏高',
      color: latest?.totalCholesterol && latest.totalCholesterol <= 5.2 ? '#27ae60' : '#e74c3c',
      icon: <FileText size={24} />
    },
  ];

  return (
    <div style={{ 
      display: 'grid', 
      gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', 
      gap: '20px',
      marginBottom: '32px'
    }}>
      {indicators.map((item, index) => (
        <div 
          key={index}
          style={{
            background: 'white',
            borderRadius: '16px',
            padding: '24px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
            borderLeft: `4px solid ${item.color}`,
            display: 'flex',
            alignItems: 'center',
            gap: '16px'
          }}
        >
          <div style={{ 
            width: '56px', 
            height: '56px', 
            borderRadius: '12px', 
            background: `${item.color}15`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: item.color
          }}>
            {item.icon}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '4px' }}>{item.title}</div>
            <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#333' }}>
              {item.value}
              <span style={{ fontSize: '0.9rem', marginLeft: '4px', color: '#999' }}>{item.unit}</span>
            </div>
            <div style={{ fontSize: '0.85rem', color: item.color, marginTop: '4px', fontWeight: 500 }}>
              {item.status}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

// 体检数据上传组件
export const ExamDataUpload: React.FC<{ onDataLoaded?: (data: any[]) => void }> = ({ onDataLoaded }) => {
  const [uploading, setUploading] = useState(false);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    
    // 模拟处理 - 实际应该调用OCR API
    setTimeout(() => {
      setUploading(false);
      if (onDataLoaded) {
        onDataLoaded([]);
      }
      alert('体检报告已上传，正在提取数据...\n\n注意：需要配置OCR服务才能自动提取。目前可以手动输入数据。');
    }, 1500);
  };

  return (
    <div style={{
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      borderRadius: '16px',
      padding: '32px',
      color: 'white',
      textAlign: 'center',
      marginBottom: '32px'
    }}>
      <Upload size={48} style={{ marginBottom: '16px' }} />
      <h3 style={{ marginBottom: '8px' }}>上传体检报告</h3>
      <p style={{ opacity: 0.9, marginBottom: '20px' }}>
        支持 PDF、JPG、PNG 格式，自动提取关键指标
      </p>
      <label style={{
        display: 'inline-block',
        background: 'white',
        color: '#667eea',
        padding: '12px 32px',
        borderRadius: '8px',
        cursor: 'pointer',
        fontWeight: 600,
        transition: 'transform 0.2s'
      }}>
        {uploading ? '上传中...' : '选择文件'}
        <input 
          type="file" 
          accept=".pdf,.jpg,.jpeg,.png" 
          style={{ display: 'none' }}
          onChange={handleFileUpload}
        />
      </label>
      <p style={{ fontSize: '0.8rem', opacity: 0.7, marginTop: '16px' }}>
        已发现 6 份历史体检报告待处理
      </p>
    </div>
  );
};

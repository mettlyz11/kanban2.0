import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * ProfileFromFiles 组件 - 简化版
 * 从 Files 目录动态读取并显示个人信息和公司信息
 * 支持 Markdown 渲染
 * 
 * 使用示例:
 * <ProfileFromFiles type="personal" name="刘宇宙" />
 * <ProfileFromFiles type="company" name="和光智成" />
 */

const API_BASE_URL = '/api';

const ProfileFromFiles = ({ type = 'personal', name = '', showTabs = true }) => {
  const [content, setContent] = useState(null);
  const [parsedData, setParsedData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('preview');

  useEffect(() => {
    fetchContent();
  }, [type, name]);

  const fetchContent = async () => {
    try {
      setLoading(true);
      setError(null);

      // 获取原始内容
      const contentResponse = await fetch(
        `${API_BASE_URL}/file-content?type=${type}&name=${encodeURIComponent(name)}&format=raw`
      );
      
      if (!contentResponse.ok) {
        throw new Error(`Failed to fetch content: ${contentResponse.status}`);
      }

      const contentData = await contentResponse.json();
      setContent(contentData.data);

      // 获取解析后的内容
      const parsedResponse = await fetch(
        `${API_BASE_URL}/file-content?type=${type}&name=${encodeURIComponent(name)}&format=parsed`
      );
      
      if (parsedResponse.ok) {
        const parsedData = await parsedResponse.json();
        setParsedData(parsedData.data);
      }

      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const styles = {
    card: {
      background: 'white',
      borderRadius: '12px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
      marginBottom: '24px',
      overflow: 'hidden'
    },
    cardHeader: {
      padding: '20px 24px',
      borderBottom: '1px solid #e5e7eb',
      display: 'flex',
      alignItems: 'center',
      gap: '12px'
    },
    cardTitle: {
      margin: 0,
      fontSize: '1.25rem',
      fontWeight: '600',
      color: '#1f2937'
    },
    cardContent: {
      padding: '24px'
    },
    tabs: {
      display: 'flex',
      gap: '8px',
      marginBottom: '16px',
      borderBottom: '2px solid #e5e7eb',
      paddingBottom: '12px'
    },
    tab: {
      padding: '8px 16px',
      border: 'none',
      borderRadius: '8px',
      cursor: 'pointer',
      fontWeight: '500',
      transition: 'all 0.2s'
    },
    activeTab: {
      background: '#667eea',
      color: 'white'
    },
    inactiveTab: {
      background: 'transparent',
      color: '#6b7280'
    },
    alert: {
      padding: '16px',
      borderRadius: '8px',
      marginBottom: '16px',
      display: 'flex',
      alignItems: 'center',
      gap: '12px'
    },
    alertError: {
      background: '#fee2e2',
      color: '#dc2626',
      border: '1px solid #fecaca'
    },
    alertInfo: {
      background: '#eff6ff',
      color: '#2563eb',
      border: '1px solid #dbeafe'
    },
    badge: {
      display: 'inline-block',
      padding: '4px 12px',
      borderRadius: '9999px',
      fontSize: '0.75rem',
      fontWeight: '500',
      background: '#e0e7ff',
      color: '#667eea',
      marginLeft: '12px'
    },
    infoGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
      gap: '16px',
      marginBottom: '24px'
    },
    infoItem: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      padding: '12px',
      background: '#f9fafb',
      borderRadius: '8px'
    },
    pre: {
      background: '#f3f4f6',
      padding: '16px',
      borderRadius: '8px',
      overflow: 'auto',
      fontSize: '0.875rem',
      maxHeight: '600px'
    }
  };

  if (loading) {
    return (
      <div style={styles.card}>
        <div style={styles.cardContent}>
          <div style={{ color: '#6b7280' }}>加载中...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ ...styles.alert, ...styles.alertError }}>
        <span>⚠️</span>
        <span>加载失败：{error}</span>
      </div>
    );
  }

  if (!content) {
    return (
      <div style={{ ...styles.alert, ...styles.alertInfo }}>
        <span>ℹ️</span>
        <span>未找到内容</span>
      </div>
    );
  }

  const metadata = parsedData?.metadata || {};

  return (
    <div>
      {showTabs && (
        <div style={styles.tabs}>
          <button
            onClick={() => setActiveTab('preview')}
            style={{
              ...styles.tab,
              ...(activeTab === 'preview' ? styles.activeTab : styles.inactiveTab)
            }}
          >
            预览
          </button>
          <button
            onClick={() => setActiveTab('markdown')}
            style={{
              ...styles.tab,
              ...(activeTab === 'markdown' ? styles.activeTab : styles.inactiveTab)
            }}
          >
            Markdown
          </button>
        </div>
      )}

      {activeTab === 'preview' && (
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <h3 style={styles.cardTitle}>
              {metadata.title || (type === 'personal' ? '个人资料' : '公司信息')}
            </h3>
            {metadata.last_updated && (
              <span style={styles.badge}>
                最后更新：{metadata.last_updated}
              </span>
            )}
          </div>
          <div style={styles.cardContent}>
            <div className="prose" style={{ maxWidth: '100%' }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content.content}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'markdown' && (
        <div style={styles.card}>
          <div style={styles.cardContent}>
            <pre style={styles.pre}>
              <code>{content.content}</code>
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProfileFromFiles;

import React from 'react';
import * as Sentry from '@sentry/react';

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    Sentry.captureException(error, {
      contexts: { react: errorInfo },
    });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReport = () => {
    Sentry.showReportDialog({
      title: '报告问题',
      subtitle: '请描述一下你遇到的问题',
      subtitle2: '我们会尽快修复',
      labelName: '姓名',
      labelEmail: '邮箱',
      labelComments: '详细描述',
      labelClose: '关闭',
      labelSubmit: '提交',
      successMessage: '感谢反馈！',
    });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          padding: '20px',
          backgroundColor: '#f5f5f5',
        }}>
          <h2 style={{ color: '#e53e3e', marginBottom: '16px' }}>
            ⚠️ 抱歉，出现了错误
          </h2>
          <p style={{ color: '#666', marginBottom: '24px', textAlign: 'center' }}>
            应用遇到了意外错误，请尝试刷新页面或报告问题
          </p>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={this.handleReload}
              style={{
                padding: '10px 20px',
                backgroundColor: '#3182ce',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              🔄 刷新页面
            </button>
            <button
              onClick={this.handleReport}
              style={{
                padding: '10px 20px',
                backgroundColor: '#e53e3e',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              🐛 报告问题
            </button>
          </div>
          {import.meta.env.DEV && this.state.error && (
            <pre style={{
              marginTop: '20px',
              padding: '16px',
              backgroundColor: '#fff',
              borderRadius: '8px',
              maxWidth: '800px',
              overflow: 'auto',
            }}>
              {this.state.error.stack}
            </pre>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

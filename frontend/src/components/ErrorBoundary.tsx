import React, { useState, useRef, useCallback } from 'react';
import * as Sentry from '@sentry/react';

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  showFeedback?: boolean;
}

// 可拖动的反馈对话框
function DraggableFeedbackDialog({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [comments, setComments] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);

  // offset from center: 0 means centered
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const dragRef = useRef({ startX: 0, startY: 0, offX: 0, offY: 0 });

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragRef.current = { startX: e.clientX, startY: e.clientY, offX: offset.x, offY: offset.y };
    const onMove = (ev: MouseEvent) => {
      setOffset({
        x: dragRef.current.offX + (ev.clientX - dragRef.current.startX),
        y: dragRef.current.offY + (ev.clientY - dragRef.current.startY),
      });
    };
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [offset.x, offset.y]);

  const handleSubmit = () => {
    Sentry.captureMessage('User Feedback: ' + comments, {
      user: { username: name, email },
    });
    setSubmitted(true);
    setTimeout(onClose, 2000);
  };

  if (submitted) {
    return (
      <div style={overlayStyle} onClick={onClose}>
        <div style={dialogStyle}>
          <h3 style={{ color: '#22c55e', marginBottom: '16px' }}>✅ 感谢反馈！</h3>
          <p style={{ color: '#666' }}>我们会尽快修复问题。</p>
        </div>
      </div>
    );
  }

  // When offset != 0, use translate instead of the center translate(-50%,-50%)
  const hasMoved = offset.x !== 0 || offset.y !== 0;

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div
        ref={dialogRef}
        onClick={(e) => e.stopPropagation()}
        style={{
          ...dialogStyle,
          transform: hasMoved ? `translate(calc(-50% + ${offset.x}px), calc(-50% + ${offset.y}px))` : undefined,
          cursor: 'default',
        }}
      >
        <div
          onMouseDown={handleMouseDown}
          style={{
            padding: '12px 16px',
            borderBottom: '1px solid #e5e7eb',
            cursor: 'grab',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            backgroundColor: '#f9fafb',
            borderRadius: '12px 12px 0 0',
            userSelect: 'none',
          }}
        >
          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>🐛 报告问题</h3>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '20px',
              cursor: 'pointer',
              color: '#9ca3af',
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>
        <div style={{ padding: '20px' }}>
          <p style={{ color: '#666', marginBottom: '16px', fontSize: '14px' }}>
            请描述你遇到的问题，我们会尽快修复
          </p>
          <div style={{ marginBottom: '12px' }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, marginBottom: '4px' }}>姓名</label>
            <input
              type='text'
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={inputStyle}
              placeholder='你的姓名'
            />
          </div>
          <div style={{ marginBottom: '12px' }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, marginBottom: '4px' }}>邮箱</label>
            <input
              type='email'
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={inputStyle}
              placeholder='your@email.com'
            />
          </div>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, marginBottom: '4px' }}>详细描述</label>
            <textarea
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              style={{ ...inputStyle, minHeight: '100px', resize: 'vertical' }}
              placeholder='请描述问题详情...'
            />
          </div>
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
            <button onClick={onClose} style={{ ...btnStyle, backgroundColor: '#f3f4f6', color: '#374151' }}>
              取消
            </button>
            <button onClick={handleSubmit} style={{ ...btnStyle, backgroundColor: '#e53e3e', color: 'white' }}>
              提交
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

const overlayStyle: React.CSSProperties = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: 'rgba(0, 0, 0, 0.4)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 9999,
};

const dialogStyle: React.CSSProperties = {
  position: 'relative',
  backgroundColor: 'white',
  borderRadius: '12px',
  boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
  width: '420px',
  maxWidth: '90vw',
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 12px',
  border: '1px solid #d1d5db',
  borderRadius: '6px',
  fontSize: '14px',
  boxSizing: 'border-box',
};

const btnStyle: React.CSSProperties = {
  padding: '8px 16px',
  borderRadius: '6px',
  border: 'none',
  fontSize: '14px',
  cursor: 'pointer',
  fontWeight: 500,
};

class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, showFeedback: false };
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

  render() {
    if (this.state.hasError) {
      return (
        <>
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
                onClick={() => this.setState({ showFeedback: true })}
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
          {this.state.showFeedback && (
            <DraggableFeedbackDialog onClose={() => this.setState({ showFeedback: false })} />
          )}
        </>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

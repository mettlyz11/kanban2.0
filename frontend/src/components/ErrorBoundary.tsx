import { ErrorBoundary as SentryErrorBoundary } from "@sentry/react";

interface FallbackProps {
  error: Error;
  resetError?: () => void;
}

function Fallback({ error, resetError }: FallbackProps) {
  return (
    <div style={{ 
      padding: '20px', 
      margin: '20px', 
      border: '1px solid #ff4444', 
      borderRadius: '8px',
      backgroundColor: '#fff5f5'
    }}>
      <h2 style={{ color: '#c53030', marginBottom: '10px' }}>
        ⚠️ 出错了
      </h2>
      <p style={{ color: '#742a2a', marginBottom: '15px' }}>
        {error.message}
      </p>
      {resetError && (
        <button
          onClick={resetError}
          style={{
            padding: '8px 16px',
            backgroundColor: '#e53e3e',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          重试
        </button>
      )}
    </div>
  );
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

export function ErrorBoundary({ children }: ErrorBoundaryProps) {
  return (
    <SentryErrorBoundary fallback={Fallback}>
      {children}
    </SentryErrorBoundary>
  );
}

export default ErrorBoundary;

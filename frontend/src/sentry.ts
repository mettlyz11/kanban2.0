import * as Sentry from '@sentry/react';
import { BrowserTracing } from '@sentry/tracing';

const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN || '';

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    integrations: [
      new BrowserTracing({
        tracePropagationTargets: ['localhost', /^https:\/\//],
      }),
    ],
    
    environment: import.meta.env.MODE || 'development',
    tracesSampleRate: import.meta.env.PROD ? 0.2 : 1.0,
    sampleRate: 1.0,
    
    release: 'kanban@' + (import.meta.env.VITE_APP_VERSION || '4.6.0'),
    
    autoSessionTracking: true,
    
    initialScope: {
      tags: {
        component: 'frontend',
        version: '4.6.0',
      },
    },
    
    ignoreErrors: [
      'ResizeObserver loop limit exceeded',
      'Network request failed',
      'Failed to fetch',
      'Non-Error exception captured',
    ],
    
    beforeSend(event) {
      // 过滤掉非错误级别
      if (event.level === 'log' || event.level === 'info') {
        return null;
      }
      return event;
    },
  });
  
  console.log('[Sentry] 已初始化');
} else {
  console.warn('[Sentry] DSN 未配置，跳过初始化');
}

export default Sentry;

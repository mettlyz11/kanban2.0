import React, { useState, useEffect } from 'react';
import { socketIO, TaskLock } from '../utils/socket';

interface EditLockIndicatorProps {
  taskId: string;
  userId: string;
  onLockChange?: (locked: boolean) => void;
}

const EditLockIndicator: React.FC<EditLockIndicatorProps> = ({ 
  taskId, 
  userId,
  onLockChange 
}) => {
  const [isLocked, setIsLocked] = useState(false);
  const [lockedBy, setLockedBy] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [isRequesting, setIsRequesting] = useState(false);

  useEffect(() => {
    // 监听锁事件
    const handleLockAcquired = (lock: TaskLock) => {
      if (lock.task_id === taskId) {
        setIsLocked(true);
        setLockedBy(lock.locked_by);
        setExpiresAt(lock.expires_at);
        onLockChange?.(true);
      }
    };

    const handleLockDenied = (lock: TaskLock) => {
      if (lock.task_id === taskId) {
        console.warn('编辑锁被拒绝，已被其他用户锁定');
        setIsLocked(true);
        setLockedBy(lock.locked_by);
      }
    };

    const handleLockReleased = (releasedTaskId: string) => {
      if (releasedTaskId === taskId) {
        setIsLocked(false);
        setLockedBy(null);
        setExpiresAt(null);
        onLockChange?.(false);
      }
    };

    // 注册事件监听（这里简化处理，实际应该通过 socketIO 的回调机制）
    // 在实际使用中，应该在 socket.ts 中维护事件监听器列表

    return () => {
      // 清理监听
    };
  }, [taskId, onLockChange]);

  const requestLock = () => {
    if (!isLocked && !isRequesting) {
      setIsRequesting(true);
      socketIO.requestLock(taskId);
      setTimeout(() => setIsRequesting(false), 2000);
    }
  };

  const releaseLock = () => {
    if (isLocked && lockedBy === userId) {
      socketIO.releaseLock(taskId);
      setIsLocked(false);
      setLockedBy(null);
      setExpiresAt(null);
    }
  };

  const isCurrentUserLock = lockedBy === userId;

  // 如果未锁定，显示获取锁按钮
  if (!isLocked) {
    return (
      <button 
        onClick={requestLock}
        disabled={isRequesting}
        style={styles.lockButton}
      >
        {isRequesting ? '🔒 请求中...' : '🔓 编辑'}
      </button>
    );
  }

  // 如果被当前用户锁定，显示释放锁按钮
  if (isCurrentUserLock) {
    return (
      <div style={styles.lockedContainer}>
        <span style={styles.lockedIcon}>🔒</span>
        <span style={styles.lockedText}>编辑中</span>
        <button onClick={releaseLock} style={styles.unlockButton}>
          完成编辑
        </button>
      </div>
    );
  }

  // 如果被其他用户锁定，显示锁定提示
  return (
    <div style={styles.lockedByOtherContainer}>
      <span style={styles.lockedIcon}>🔒</span>
      <span style={styles.lockedByText}>
        {lockedBy} 正在编辑
      </span>
    </div>
  );
};

// ============================================
// 样式
// ============================================
const styles: { [key: string]: React.CSSProperties } = {
  lockButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 12px',
    backgroundColor: '#1890ff',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '13px',
    transition: 'all 0.2s'
  },
  lockedContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '6px 12px',
    backgroundColor: '#f6ffed',
    border: '1px solid #b7eb8f',
    borderRadius: '4px',
    fontSize: '13px'
  },
  lockedIcon: {
    fontSize: '16px'
  },
  lockedText: {
    color: '#52c41a',
    fontWeight: 500
  },
  unlockButton: {
    padding: '4px 8px',
    backgroundColor: '#fff',
    border: '1px solid #d9d9d9',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '12px',
    marginLeft: '8px'
  },
  lockedByOtherContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '6px 12px',
    backgroundColor: '#fff1f0',
    border: '1px solid #ffa39e',
    borderRadius: '4px',
    fontSize: '13px'
  },
  lockedByText: {
    color: '#f5222d'
  }
};

export default EditLockIndicator;

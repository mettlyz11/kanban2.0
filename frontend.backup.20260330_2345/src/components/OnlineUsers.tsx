import React, { useState, useEffect } from 'react';
import { socketIO, OnlineUser } from '../utils/socket';

interface OnlineUsersProps {
  currentUserId?: string;
}

const OnlineUsers: React.FC<OnlineUsersProps> = ({ currentUserId }) => {
  const [onlineUsers, setOnlineUsers] = useState<OnlineUser[]>([]);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // 初始化 WebSocket 连接
    const initSocket = async () => {
      try {
        await socketIO.connect({
          url: window.location.origin,
          userId: currentUserId || 'anonymous',
          username: '当前用户',
          onOnlineUsersList: (users) => {
            setOnlineUsers(users);
          },
          onUserOnline: (user) => {
            setOnlineUsers(prev => {
              const exists = prev.find(u => u.user_id === user.user_id);
              if (!exists) {
                return [...prev, user];
              }
              return prev;
            });
          },
          onUserOffline: (user) => {
            setOnlineUsers(prev => prev.filter(u => u.user_id !== user.user_id));
          }
        });
      } catch (error) {
        console.error('WebSocket 连接失败:', error);
      }
    };

    initSocket();

    // 清理
    return () => {
      socketIO.disconnect();
    };
  }, [currentUserId]);

  const getUserCount = () => {
    return onlineUsers.length;
  };

  const getCurrentUser = () => {
    return onlineUsers.find(u => u.user_id === currentUserId);
  };

  return (
    <div style={styles.container}>
      <div 
        style={styles.header}
        onClick={() => setIsVisible(!isVisible)}
      >
        <span style={styles.icon}>👥</span>
        <span style={styles.count}>{getUserCount()}</span>
        <span style={styles.text}>在线</span>
      </div>
      
      {isVisible && onlineUsers.length > 0 && (
        <div style={styles.dropdown}>
          <div style={styles.list}>
            {onlineUsers.map((user) => {
              const isCurrentUser = user.user_id === currentUserId;
              return (
                <div 
                  key={user.user_id}
                  style={{
                    ...styles.userItem,
                    ...(isCurrentUser ? styles.currentUser : {})
                  }}
                >
                  <span style={styles.userAvatar}>
                    {isCurrentUser ? '👤' : '👥'}
                  </span>
                  <div style={styles.userInfo}>
                    <span style={styles.username}>
                      {user.username}
                      {isCurrentUser && ' (我)'}
                    </span>
                    {user.sessions > 1 && (
                      <span style={styles.sessionCount}>
                        {user.sessions} 个会话
                      </span>
                    )}
                  </div>
                  <span style={styles.statusDot}></span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================
// 样式
// ============================================
const styles: { [key: string]: React.CSSProperties } = {
  container: {
    position: 'relative',
    display: 'inline-block'
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 12px',
    backgroundColor: '#f0f2f5',
    borderRadius: '20px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    fontSize: '13px'
  },
  icon: {
    fontSize: '16px'
  },
  count: {
    fontWeight: 'bold',
    color: '#1890ff'
  },
  text: {
    color: '#666'
  },
  dropdown: {
    position: 'absolute',
    top: '100%',
    right: 0,
    marginTop: '8px',
    backgroundColor: 'white',
    borderRadius: '8px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
    minWidth: '200px',
    zIndex: 1000,
    overflow: 'hidden'
  },
  list: {
    maxHeight: '300px',
    overflowY: 'auto'
  },
  userItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '10px 12px',
    borderBottom: '1px solid #f0f0f0',
    transition: 'background-color 0.2s'
  },
  currentUser: {
    backgroundColor: '#e6f7ff'
  },
  userAvatar: {
    fontSize: '20px'
  },
  userInfo: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '2px'
  },
  username: {
    fontSize: '14px',
    fontWeight: 500,
    color: '#333'
  },
  sessionCount: {
    fontSize: '12px',
    color: '#999'
  },
  statusDot: {
    width: '8px',
    height: '8px',
    backgroundColor: '#52c41a',
    borderRadius: '50%'
  }
};

export default OnlineUsers;

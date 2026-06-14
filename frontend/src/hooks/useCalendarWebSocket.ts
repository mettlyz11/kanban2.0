import { useEffect, useState, useCallback } from 'react';
import { socketIO } from '../utils/socket';

export function useCalendarWebSocket(userId?: string) {
  const [wsConnected, setWsConnected] = useState(false);
  const [pendingRefresh, setPendingRefresh] = useState(false);
  const [alert, setAlert] = useState<{
    meeting_id: number;
    title: string;
    minutes_before: number;
  } | null>(null);

  // 如果 userId 为空，使用默认值确保能连接
  const effectiveUserId = userId || 'guest-calendar';

  useEffect(() => {
    // Subscribe to calendar events
    // Check real socket connection status
    const checkConn = setInterval(() => {
      // @ts-ignore
      if (socketIO.connected) {
        setWsConnected(true);
        clearInterval(checkConn);
      }
    }, 500);

    socketIO.emit('calendar_subscribe', { user_id: effectiveUserId });

    // Listen for new events
    socketIO.on('calendar_event_added', (data: any) => {
      setPendingRefresh(true);
    });

    socketIO.on('calendar_event_changed', (data: any) => {
      setPendingRefresh(true);
    });

    socketIO.on('calendar_event_removed', (data: any) => {
      setPendingRefresh(true);
    });

    socketIO.on('meeting_alert', (data: any) => {
      setAlert(data);
      setPendingRefresh(true);
    });

    return () => {
      clearInterval(checkConn);
      socketIO.emit('calendar_unsubscribe', { user_id: effectiveUserId });
      socketIO.off('calendar_event_added');
      socketIO.off('calendar_event_changed');
      socketIO.off('calendar_event_removed');
      socketIO.off('meeting_alert');
    };
  }, [effectiveUserId]);

  const clearAlert = useCallback(() => setAlert(null), []);
  const markRefreshed = useCallback(() => setPendingRefresh(false), []);

  return { wsConnected, pendingRefresh, markRefreshed, alert, clearAlert };
}

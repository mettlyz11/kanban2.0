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

  useEffect(() => {
    if (!userId) return;

    // Subscribe to calendar events
    socketIO.emit('calendar_subscribe', { user_id: userId });

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

    setWsConnected(true);

    return () => {
      socketIO.emit('calendar_unsubscribe', { user_id: userId });
      socketIO.off('calendar_event_added');
      socketIO.off('calendar_event_changed');
      socketIO.off('calendar_event_removed');
      socketIO.off('meeting_alert');
    };
  }, [userId]);

  const clearAlert = useCallback(() => setAlert(null), []);
  const markRefreshed = useCallback(() => setPendingRefresh(false), []);

  return { wsConnected, pendingRefresh, markRefreshed, alert, clearAlert };
}

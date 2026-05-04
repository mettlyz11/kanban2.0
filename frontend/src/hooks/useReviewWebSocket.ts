import { useEffect, useRef, useState, useCallback } from 'react';
import { socketIO } from '../utils/socket';

export interface ReviewTaskNotification {
  task_id: number;
  title: string;
  priority: string;
  submitted_by: string;
  timestamp: string;
}

export interface ReviewResultNotification {
  task_id: number;
  result: 'approved' | 'rejected' | 'skipped';
  reviewed_by: string;
  feedback?: string;
  timestamp: string;
}

export function useReviewWebSocket(userId?: string) {
  const [newTaskAlert, setNewTaskAlert] = useState<ReviewTaskNotification | null>(null);
  const [resultAlert, setResultAlert] = useState<ReviewResultNotification | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const pendingRefreshRef = useRef(false);

  const clearNewTaskAlert = useCallback(() => {
    setNewTaskAlert(null);
  }, []);

  const clearResultAlert = useCallback(() => {
    setResultAlert(null);
  }, []);

  useEffect(() => {
    // Wait for socket connection
    const checkConnection = setInterval(() => {
      // @ts-ignore - accessing internal state
      if (socketIO.connected) {
        setWsConnected(true);
        clearInterval(checkConnection);
      }
    }, 1000);

    return () => clearInterval(checkConnection);
  }, []);

  useEffect(() => {
    if (!wsConnected || !userId) return;

    // Subscribe to review events
    socketIO.emit('review_join', { user_id: userId });

    // Listen for new review tasks
    const handleNewTask = (data: ReviewTaskNotification) => {
      setNewTaskAlert(data);
      pendingRefreshRef.current = true;
    };

    // Listen for review results
    const handleResult = (data: ReviewResultNotification) => {
      setResultAlert(data);
      pendingRefreshRef.current = true;
    };

    // Listen for task reviewed events (from project room)
    const handleTaskReviewed = (data: { task_id: number; status: string; reviewed_by: string }) => {
      pendingRefreshRef.current = true;
    };

    socketIO.on('review_task_pending', handleNewTask);
    socketIO.on('review_result', handleResult);
    socketIO.on('task_reviewed', handleTaskReviewed);

    return () => {
      socketIO.emit('review_leave', { user_id: userId });
      socketIO.off('review_task_pending', handleNewTask);
      socketIO.off('review_result', handleResult);
      socketIO.off('task_reviewed', handleTaskReviewed);
    };
  }, [wsConnected, userId]);

  const shouldRefresh = pendingRefreshRef.current;
  const markRefreshed = useCallback(() => {
    pendingRefreshRef.current = false;
  }, []);

  return {
    wsConnected,
    newTaskAlert,
    resultAlert,
    clearNewTaskAlert,
    clearResultAlert,
    shouldRefresh,
    markRefreshed,
  };
}

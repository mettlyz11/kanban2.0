import { useEffect, useState, useCallback, useRef } from 'react';
import { socketIO } from '../utils/socket';

export interface ActiveEditor {
  user_id: string;
  username: string;
  joined_at: string;
}

export function useMeetingWebSocket(meetingId?: string, userId?: string, username?: string) {
  const [wsConnected, setWsConnected] = useState(false);
  const [activeEditors, setActiveEditors] = useState<ActiveEditor[]>([]);
  const [contentUpdate, setContentUpdate] = useState<any>(null);
  const [newComment, setNewComment] = useState<any>(null);

  const meetingRef = useRef(meetingId);

  useEffect(() => {
    meetingRef.current = meetingId;
  }, [meetingId]);

  useEffect(() => {
    if (!meetingId || !userId || !username) return;

    // Join meeting room
    socketIO.emit('meeting_join', {
      meeting_id: meetingId,
      user_id: userId,
      username: username,
    });

    // Listen for editor join/leave
    socketIO.on('editor_joined', (data: any) => {
      setActiveEditors(data.active_editors || []);
    });

    socketIO.on('editor_left', (data: any) => {
      setActiveEditors(data.active_editors || []);
    });

    // Listen for content changes
    socketIO.on('content_updated', (data: any) => {
      setContentUpdate(data);
    });

    // Listen for new comments
    socketIO.on('new_comment', (data: any) => {
      setNewComment(data);
    });

    setWsConnected(true);

    return () => {
      socketIO.emit('meeting_leave', {
        meeting_id: meetingId,
        user_id: userId,
      });
      socketIO.off('editor_joined');
      socketIO.off('editor_left');
      socketIO.off('content_updated');
      socketIO.off('new_comment');
    };
  }, [meetingId, userId, username]);

  const emitContentChange = useCallback((changes: any) => {
    if (meetingRef.current && userId) {
      socketIO.emit('content_changed', {
        meeting_id: meetingRef.current,
        user_id: userId,
        changes,
      });
    }
  }, [userId]);

  const clearContentUpdate = useCallback(() => setContentUpdate(null), []);
  const clearComment = useCallback(() => setNewComment(null), []);

  return {
    wsConnected,
    activeEditors,
    contentUpdate,
    newComment,
    clearContentUpdate,
    clearComment,
    emitContentChange,
  };
}

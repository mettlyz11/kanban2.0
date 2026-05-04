/**
 * Extended WebSocket client for all modules
 * Extends the base socket manager with new event types
 */

import { socketIO, OnlineUser, TaskLock } from './socket';

// ============================================
// Board Events
// ============================================
export interface BoardCallbacks {
  onTaskMoved?: (data: {
    task_id: number;
    from_column: string;
    to_column: string;
    moved_by: string;
  }) => void;
  onColumnReordered?: (data: {
    columns: string[];
  }) => void;
  onTaskDragStarted?: (data: {
    task_id: number;
    username: string;
  }) => void;
  onTaskDragEnded?: (data: {
    task_id: number;
  }) => void;
}

export const boardSocket = {
  joinBoard: (boardId: string) => {
    socketIO.emit('board_join', { board_id: boardId });
  },
  leaveBoard: (boardId: string) => {
    socketIO.emit('board_leave', { board_id: boardId });
  },
  emitTaskMoved: (data: {
    board_id: string;
    task_id: number;
    from_column: string;
    to_column: string;
  }) => {
    socketIO.emit('task_moved', data);
  },
  onTaskMoved: (callback: BoardCallbacks['onTaskMoved']) => {
    socketIO.on('task_moved', callback);
  },
  onColumnReordered: (callback: BoardCallbacks['onColumnReordered']) => {
    socketIO.on('column_reordered', callback);
  }
};

// ============================================
// Review Events
// ============================================
export interface ReviewCallbacks {
  onReviewTaskPending?: (data: {
    task_id: number;
    title: string;
    priority: string;
    submitted_by: string;
  }) => void;
  onReviewResult?: (data: {
    task_id: number;
    result: string;
    reviewed_by: string;
    feedback?: string;
  }) => void;
}

export const reviewSocket = {
  subscribe: (userId: string) => {
    socketIO.emit('review_join', { user_id: userId });
  },
  onReviewTaskPending: (callback: ReviewCallbacks['onReviewTaskPending']) => {
    socketIO.on('review_task_pending', callback);
  },
  onReviewResult: (callback: ReviewCallbacks['onReviewResult']) => {
    socketIO.on('review_result', callback);
  }
};

// ============================================
// Meeting Events
// ============================================
export interface MeetingCallbacks {
  onEditorJoined?: (data: { username: string; active_editors: any[] }) => void;
  onEditorLeft?: (data: { active_editors: any[] }) => void;
  onContentUpdated?: (data: { changes: any; user_id: string }) => void;
  onNewComment?: (data: { comment: any; added_by: string }) => void;
}

export const meetingSocket = {
  joinMeeting: (meetingId: string, userId: string, username: string) => {
    socketIO.emit('meeting_join', { meeting_id: meetingId, user_id: userId, username });
  },
  leaveMeeting: (meetingId: string, userId: string) => {
    socketIO.emit('meeting_leave', { meeting_id: meetingId, user_id: userId });
  },
  emitContentChange: (meetingId: string, userId: string, changes: any) => {
    socketIO.emit('content_changed', { meeting_id: meetingId, user_id: userId, changes });
  },
  onEditorJoined: (callback: MeetingCallbacks['onEditorJoined']) => {
    socketIO.on('editor_joined', callback);
  },
  onEditorLeft: (callback: MeetingCallbacks['onEditorLeft']) => {
    socketIO.on('editor_left', callback);
  },
  onContentUpdated: (callback: MeetingCallbacks['onContentUpdated']) => {
    socketIO.on('content_updated', callback);
  },
  onNewComment: (callback: MeetingCallbacks['onNewComment']) => {
    socketIO.on('new_comment', callback);
  }
};

// ============================================
// Calendar Events
// ============================================
export const calendarSocket = {
  subscribe: (userId: string) => {
    socketIO.emit('calendar_subscribe', { user_id: userId });
  },
  onEventAdded: (callback: (data: { event: any }) => void) => {
    socketIO.on('calendar_event_added', callback);
  },
  onEventChanged: (callback: (data: { event_id: number; changes: any }) => void) => {
    socketIO.on('calendar_event_changed', callback);
  },
  onEventRemoved: (callback: (data: { event_id: number; title: string }) => void) => {
    socketIO.on('calendar_event_removed', callback);
  },
  onMeetingAlert: (callback: (data: { meeting_id: number; title: string; minutes_before: number }) => void) => {
    socketIO.on('meeting_alert', callback);
  }
};

// ============================================
// SDS Events
// ============================================
export const sdsSocket = {
  subscribe: (userId: string) => {
    socketIO.emit('sds_subscribe', { user_id: userId });
  },
  onTaskCreated: (callback: (data: { task: any }) => void) => {
    socketIO.on('sds_task_created', callback);
  },
  onTaskExecuting: (callback: (data: { task_id: number; progress: number; status_message: string }) => void) => {
    socketIO.on('sds_task_executing', callback);
  },
  onTaskCompleted: (callback: (data: { task_id: number; result_summary: string }) => void) => {
    socketIO.on('sds_task_completed', callback);
  },
  onTaskFailed: (callback: (data: { task_id: number; error: string }) => void) => {
    socketIO.on('sds_task_failed', callback);
  },
  onSystemStatus: (callback: (data: { status: string; metrics: any }) => void) => {
    socketIO.on('sds_system_status', callback);
  },
  onAlert: (callback: (data: { type: string; message: string; severity: string }) => void) => {
    socketIO.on('sds_alert', callback);
  }
};

// ============================================
// System Monitor Events
// ============================================
export const systemSocket = {
  subscribe: (userId: string) => {
    socketIO.emit('monitor_subscribe', { user_id: userId });
  },
  onSystemAlert: (callback: (data: {
    type: string;
    severity: string;
    message: string;
    metric: string;
    current_value: number;
    threshold: number;
  }) => void) => {
    socketIO.on('system_alert', callback);
  },
  onHealthStatus: (callback: (data: { service: string; status: string; details: any }) => void) => {
    socketIO.on('health_status_changed', callback);
  },
  onResourceMetrics: (callback: (data: { cpu: number; memory: number; disk: number }) => void) => {
    socketIO.on('resource_metrics', callback);
  }
};

export default {
  board: boardSocket,
  review: reviewSocket,
  meeting: meetingSocket,
  calendar: calendarSocket,
  sds: sdsSocket,
  system: systemSocket
};

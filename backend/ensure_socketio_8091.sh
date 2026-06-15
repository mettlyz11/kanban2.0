#!/bin/bash
PORT=8091
APP=/opt/kanban-react/backend/socketio_standalone.py
LOG=/tmp/socketio_standalone_8091.log
if ! lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
  cd /opt/kanban-react/backend
  nohup python3 "$APP" >> "$LOG" 2>&1 &
fi

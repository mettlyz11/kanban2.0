#!/bin/bash
# Kill any existing processes on port 8086
fuser -k 8086/tcp 2>/dev/null
sleep 2
cd /opt/kanban-react/backend

# Use gunicorn with eventlet worker class for stability
exec /usr/bin/python3 -m gunicorn --bind 0.0.0.0:8086 \
  --worker-class eventlet \
  --workers 2 \
  --timeout 120 \
  --keep-alive 5 \
  --graceful-timeout 30 \
  --access-logfile - \
  --error-logfile - \
  app:app

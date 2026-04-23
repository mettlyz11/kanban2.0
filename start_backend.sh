#!/bin/bash
cd /opt/kanban-react/backend
pkill -9 -f gunicorn
sleep 2
python3 -m gunicorn --bind 0.0.0.0:8086 --workers 2 --timeout 120 --daemon --access-logfile access.log --error-logfile error.log app:app
sleep 3
ps aux | grep gunicorn | grep -v grep

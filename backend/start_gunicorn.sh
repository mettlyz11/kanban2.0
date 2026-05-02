#!/bin/bash
cd /opt/kanban-react/backend
exec /usr/bin/python3 -m gunicorn --bind 0.0.0.0:8086 --workers 1 --timeout 120 app:app

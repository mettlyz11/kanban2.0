#!/usr/bin/env bash
DIST=/opt/kanban-react/frontend/dist
if [ -f /tmp/landing.html ]; then cp /tmp/landing.html $DIST/landing.html; fi
if [ -f /tmp/gardens.html ]; then cp /tmp/gardens.html $DIST/gardens.html; fi
echo "Post-build: static files restored"

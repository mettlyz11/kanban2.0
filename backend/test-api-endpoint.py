#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/kanban-react/backend')

from app import app
import json

with app.test_client() as client:
    response = client.get('/api/metrics/history?range=24h')
    data = json.loads(response.get_data(as_text=True))
    print(json.dumps(data, indent=2, ensure_ascii=False))

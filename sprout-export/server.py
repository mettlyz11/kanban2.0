#!/usr/bin/env python3
"""SproutOS standalone export server.
Serves a minimal UI and proxies API to sprout_engine process running in same container.
"""
import os, subprocess, time, urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT=Path(__file__).parent
os.chdir(ROOT)

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/' or self.path.startswith('/grow'):
            self.path='/static/index.html'
        return super().do_GET()

if __name__=='__main__':
    env=os.environ.copy()
    engine=subprocess.Popen(['python3',str(ROOT/'sprout_engine.py')],env=env)
    time.sleep(1)
    # print('[SproutOS Export] UI on :8080, engine on :18795')
    try:
        HTTPServer(('0.0.0.0',8080),Handler).serve_forever()
    finally:
        engine.terminate()

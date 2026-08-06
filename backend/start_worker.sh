#!/bin/sh
python -c "
import os, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, *a):
        pass  # keep worker logs free of probe noise

port = int(os.environ.get('PORT', 8080))
threading.Thread(
    target=HTTPServer(('0.0.0.0', port), Health).serve_forever,
    daemon=True,
).start()
" &

exec celery -A config worker --loglevel=info --concurrency=2
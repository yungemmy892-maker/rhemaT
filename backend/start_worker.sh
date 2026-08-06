#!/bin/sh
# start_worker.sh
#
# Pxxl's route-promotion step probes an HTTP port before activating a new
# deployment. This project is a Celery worker with no HTTP traffic of its
# own, so that probe was always failing (connection reset -> SIGTERM/143 ->
# rollback). This shim binds a no-op HTTP listener on $PORT in a background
# thread purely to satisfy the probe, then hands off to the real worker.

python -c "
import os, sys, threading, traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Length', '0')
        self.end_headers()
        print(f'[health-shim] probe hit: {self.client_address} {self.path}', flush=True)
    def log_message(self, *a):
        pass  # suppress default per-request stderr line, we log above instead

try:
    # Dump anything port-related so we can see exactly what Pxxl injects,
    # instead of guessing the env var name.
    port_vars = {k: v for k, v in os.environ.items() if 'PORT' in k.upper()}
    print(f'[health-shim] port-related env vars: {port_vars}', flush=True)

    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), Health)
    print(f'[health-shim] bound and listening on 0.0.0.0:{port}', flush=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
except Exception:
    print('[health-shim] FAILED TO START:', flush=True)
    traceback.print_exc()
    sys.stdout.flush()
" &

exec celery -A config worker --loglevel=info --concurrency=2
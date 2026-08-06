#!/bin/sh
# start_beat.sh
#
# Pxxl's route-promotion step probes an HTTP port before activating a new
# deployment. `celery beat` is a scheduler with no HTTP traffic of its own,
# so that probe was always failing (connection reset -> SIGTERM/143 ->
# rollback). This shim binds a no-op HTTP listener on $PORT in a background
# thread purely to satisfy the probe, then hands off to the real scheduler.
#
# NOTE: confirm this matches the actual Start command currently set for the
# `beat` project in the Pxxl dashboard (e.g. extra --scheduler or --pidfile
# flags) before replacing it — adjust the final line if it differs.

python -c "
import os, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, *a):
        pass  # keep beat logs free of probe noise

port = int(os.environ.get('PORT', 8080))
threading.Thread(
    target=HTTPServer(('0.0.0.0', port), Health).serve_forever,
    daemon=True,
).start()
" &

exec celery -A config beat --loglevel=info
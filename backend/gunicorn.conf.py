import multiprocessing
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

workers = int(os.environ.get("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"

# Kill and restart a worker that hangs on a request this long — protects
# against a stuck Paystack/Gemini/Groq/HF call wedging a worker forever.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))

# On a graceful restart/deploy, give in-flight requests this long to finish
# before being force-killed.
graceful_timeout = 30

# Recycle each worker after this many requests (± jitter, so they don't all
# recycle in the same instant) — cheap insurance against slow memory growth
# in a long-running process (numpy/faiss/pymongo).
max_requests = 1000
max_requests_jitter = 100

# Log to stdout/stderr — the host's log collector takes it from there.
accesslog = "-"
errorlog = "-"

# One worker process on purpose: the rate limiter, live duel rooms and caches live in memory.
# Threads give concurrency, and each WebSocket connection uses one thread.
import os
bind = "0.0.0.0:%s" % os.environ.get("PORT", "8000")
worker_class = "gthread"
workers = 1
threads = int(os.environ.get("WEB_THREADS", "32"))
timeout = 120
keepalive = 30
accesslog = None

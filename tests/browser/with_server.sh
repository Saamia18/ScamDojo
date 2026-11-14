#!/bin/bash
# usage: tests/browser/with_server.sh tests/browser/t_acct.py   (starts the app on a temporary database, runs the script, stops the app)
cd "$(dirname "$0")/../.."
rm -f /tmp/e2e.db*
SCAMDOJO_FEEDS=0 SCAMDOJO_RATE_LIMIT=100000 SCAMDOJO_DB=/tmp/e2e.db PORT=8765 python3 server.py > /tmp/server.log 2>&1 &
SP=$!
for i in $(seq 1 40); do curl -s -m 1 localhost:8765/api/health >/dev/null && break; sleep 0.3; done
mkdir -p shots
timeout ${TMO:-200} python3 "$@"
RC=$?
kill $SP 2>/dev/null
exit $RC

#!/data/data/com.termux/files/usr/bin/bash

set -e

echo "========================================"
echo "WEBSITE ARCHIVE STARTUP"
echo "========================================"

echo
echo "1. PostgreSQL"
if pg_ctl -D "$PREFIX/var/lib/postgresql" status >/dev/null 2>&1; then
    echo "PostgreSQL: already running"
else
    echo "Starting PostgreSQL..."
    pg_ctl -D "$PREFIX/var/lib/postgresql" \
        -l "$PREFIX/var/log/postgresql.log" start
    sleep 2
fi

echo
echo "2. Redis"
if redis-cli ping 2>/dev/null | grep -q PONG; then
    echo "Redis: already running"
else
    echo "Starting Redis..."
    redis-server --daemonize yes --ignore-warnings ARM64-COW-BUG
    sleep 1
fi

echo
echo "3. Database"
python - <<'PY'
from backend.app.db import init
init()
print("Database: OK")
PY

echo
echo "4. Starting Celery worker"
celery -A backend.app.workers.celery worker --loglevel=INFO &
CELERY_PID=$!

echo "Celery PID: $CELERY_PID"

echo
echo "5. Starting FastAPI"
echo "URL: http://127.0.0.1:8000"
echo

uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

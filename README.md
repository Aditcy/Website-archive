# Website Archive Repository

Python/FastAPI/PostgreSQL/Redis/Celery website discovery and archival repository.

## Local

Create PostgreSQL database `archive` and Redis, install `backend/requirements.txt`, then start:

`uvicorn app.main:app --host 0.0.0.0 --port 8000`

From `backend` run the worker:

`celery -A app.workers.celery.cel worker --loglevel=INFO`

Open `http://127.0.0.1:8000`.

## Wayback

Configure `IA_KEY` and `IA_SECRET` when using the current authenticated SPN2 API.

## Archive.today

The current implementation generates a manual submission URL rather than pretending an undocumented automated API exists.

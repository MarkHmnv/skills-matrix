## How to run

1. Start Redis (broker + result backend):

```bash
docker run -p 6379:6379 redis:alpine
```

2. Install deps:

```bash
# POSIX:
cd beta_worker
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Windows (PowerShell):
cd beta_worker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Start Celery worker with priority queue (and optional DLQ):

```bash
# POSIX (prefork by default):
celery -A celery_app.celery worker -l INFO -Q beta,beta.dlq

# Windows (use solo pool):
celery -A celery_app.celery worker -l INFO -P solo -Q beta,beta.dlq
```

4. Enqueue demo jobs:

```bash
python -m producer
```

5. (Optional) Check tasks and DLQ:

```bash
# List registered tasks:
celery -A celery_app.celery inspect registered

# View DLQ log (only if both beta and stable fail):
# POSIX:
tail -n +1 dlq.log || true
# Windows:
type dlq.log
```

The worker consumes from the `beta` queue (priority is best-effort on Redis) and falls back to the stable API after retries for transient errors or immediately on fatal errors. Permanently failed items are recorded in `dlq.log` and also sent to the `beta.dlq` queue.
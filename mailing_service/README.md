## How to run

1. Start Redis (broker + result backend):

```bash
docker run -p 6379:6379 redis:alpine
```

2. Start a local SMTP (MailHog):

```bash
docker run -p 1025:1025 -p 8025:8025 mailhog/mailhog
# UI at http://localhost:8025
```

3. Install deps and init DB:

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

# Init db
python -c "import mailer; mailer.init_db()"
```

4. Run Celery worker + Beat:

```bash
# POSIX (single process):
celery -A celery_app.celery worker -B -l INFO
# Windows (two terminals):
celery -A celery_app.celery worker -l INFO -P solo
celery -A celery_app.celery beat -l INFO
```

5. Enqueue a test email:

```bash
python mailer.py --to you@example.com --subject "Ping" --body "Hello from Celery!" --delay 30
```

The Beat job fires every 30s (configurable via `SEND_INTERVAL_SECONDS`) and sends anything due.
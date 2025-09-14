## How to run

1. Build images

```bash
docker compose build
```

2. Start Redis (broker + backend) and the Celery worker

```bash
docker compose up -d redis worker
```

3. Enqueue demo jobs

```bash
docker compose --profile demo up producer
```

4. (Optional) Check tasks and DLQ

```bash
# List registered tasks:
docker compose exec worker celery -A celery_app.celery inspect registered

# View DLQ log (only if both beta and stable fail):
docker compose exec worker sh -lc 'tail -n +1 /data/dlq.log || true'
```

5. (Optional) Tweak settings
   Edit `docker-compose.yml` env vars (e.g., `MAX_RETRIES`, `BASE_BACKOFF_SECONDS`, Redis URLs).

6. (Optional) to run the tests:

```bash
docker compose run --rm tests
```
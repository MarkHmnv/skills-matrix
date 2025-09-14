FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apk add --no-cache tzdata

WORKDIR /app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY *.py /app/

RUN mkdir -p /data && ln -s /data/dlq.log /app/dlq.log

RUN adduser -D -u 1001 appuser && chown -R appuser:appuser /app /data
USER appuser

# Compose will override this with the worker/producer commands
CMD ["python", "-c", "print('Use docker-compose to run the Celery worker or the demo producer.')"]

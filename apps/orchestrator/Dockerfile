FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY apps/orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/orchestrator/ /app/apps/orchestrator/
COPY packages/ /app/packages/

# Set Python path to resolve package imports
ENV PYTHONPATH=/app

EXPOSE 5555

# Default: combined worker + beat for development
# In production, run worker and beat as separate containers
CMD ["celery", "-A", "apps.orchestrator.main:celery_app", "worker", "--beat", \
     "--queues=default,provisioning,lifecycle,monitoring", \
     "--loglevel=info", "--concurrency=4"]

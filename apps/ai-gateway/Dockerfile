FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY apps/ai-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/ai-gateway/ /app/apps/ai-gateway/
COPY packages/ /app/packages/

ENV PYTHONPATH=/app

EXPOSE 8001

CMD ["uvicorn", "apps.ai-gateway.main:app", "--host", "0.0.0.0", "--port", "8001"]

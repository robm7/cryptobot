FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Install Redis tools for health checks
RUN apt-get update && apt-get install -y redis-tools && rm -rf /var/lib/apt/lists/*

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD redis-cli ping | grep PONG || exit 1

CMD ["python", "main.py"]
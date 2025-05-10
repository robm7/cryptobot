FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
COPY auth/requirements.txt auth-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r auth-requirements.txt

COPY . .

# Install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Set up Prometheus metrics endpoint
EXPOSE 8000

CMD ["python", "-m", "services.data.collector"]
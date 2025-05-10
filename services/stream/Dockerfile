FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Optimize for CPU-intensive processing
ENV PYTHONUNBUFFERED=1
ENV OMP_NUM_THREADS=1

CMD ["python", "-m", "services.stream.processor"]
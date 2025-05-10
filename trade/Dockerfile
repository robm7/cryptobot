# Build stage
FROM python:3.10-slim as builder

WORKDIR /app
COPY requirements.txt .

RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.10-slim

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

# Environment variables
ENV TRADE_API_KEY=${TRADE_API_KEY}
ENV EXCHANGE_API_KEY=${EXCHANGE_API_KEY}
ENV EXCHANGE_API_SECRET=${EXCHANGE_API_SECRET}
ENV EXCHANGE_PASSPHRASE=${EXCHANGE_PASSPHRASE}

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/trades/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
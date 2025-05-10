#!/bin/bash

# Start Kafka and Zookeeper
docker-compose up -d zookeeper kafka

# Wait for Kafka to be ready
echo "Waiting for Kafka to be ready..."
while ! docker-compose exec kafka kafka-topics --list --bootstrap-server kafka:9092 > /dev/null 2>&1; do
  sleep 1
done

# Start TimescaleDB
docker-compose up -d timescale

# Wait for TimescaleDB to be ready
echo "Waiting for TimescaleDB to be ready..."
while ! docker-compose exec timescale pg_isready -U postgres > /dev/null 2>&1; do
  sleep 1
done

# Start data services
docker-compose up -d data-collector ohlcv-processor websocket-gateway historical-loader

echo "Data services started successfully"
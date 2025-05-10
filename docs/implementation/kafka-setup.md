# Kafka Cluster Setup Guide

## 1. Hardware Requirements
```yaml
brokers:
  count: 3
  specs:
    cpu: 8 cores
    memory: 32GB
    storage: 
      type: SSD
      size: 1TB
      iops: 3000
zookeeper:
  count: 3
  specs:
    cpu: 4 cores
    memory: 16GB
```

## 2. Installation (AWS MSK Recommended)
```bash
# Using AWS MSK (Managed Streaming for Kafka)
aws kafka create-cluster \
  --cluster-name "cryptobot-data-bus" \
  --kafka-version "3.5.0" \
  --number-of-broker-nodes 3 \
  --broker-node-group-info \
    '{"ClientSubnets":["subnet-123456","subnet-789012"], \
      "BrokerAZDistribution":"DEFAULT", \
      "InstanceType":"kafka.m5.2xlarge", \
      "StorageInfo":{"EbsStorageInfo":{"VolumeSize":1000}}}'
```

## 3. Critical Configuration
```properties
# server.properties
broker.id=${BROKER_ID}
listeners=PLAINTEXT://:9092,SSL://:9093
advertised.listeners=PLAINTEXT://${HOSTNAME}:9092,SSL://${HOSTNAME}:9093
num.network.threads=3
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600
log.dirs=/data/kafka
num.partitions=3
default.replication.factor=3
min.insync.replicas=2
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000
zookeeper.connect=zk1:2181,zk2:2181,zk3:2181
```

## 4. Topic Creation
```bash
# Create core topics
kafka-topics.sh --create \
  --bootstrap-server broker1:9092 \
  --topic raw.market-data \
  --partitions 30 \
  --replication-factor 3 \
  --config retention.ms=604800000 \
  --config segment.bytes=1073741824

kafka-topics.sh --create \
  --bootstrap-server broker1:9092 \
  --topic normalized.ohlcv \
  --partitions 60 \
  --replication-factor 3 \
  --config retention.ms=2592000000
```

## 5. Security Setup
```bash
# Enable TLS and SASL/SCRAM
# 1. Generate CA
openssl req -new -x509 -keyout ca-key -out ca-cert -days 365

# 2. Create broker certificates
keytool -keystore broker.keystore.jks -alias localhost -validity 365 -genkey
keytool -keystore broker.keystore.jks -alias localhost -certreq -file cert-file
openssl x509 -req -CA ca-cert -CAkey ca-key -in cert-file -out cert-signed -days 365 -CAcreateserial
keytool -keystore broker.keystore.jks -alias CARoot -import -file ca-cert
keytool -keystore broker.keystore.jks -alias localhost -import -file cert-signed

# 3. Configure SASL
echo "KafkaServer {
  org.apache.kafka.common.security.scram.ScramLoginModule required
  username=\"admin\"
  password=\"${ADMIN_PASSWORD}\";
};" > kafka_server_jaas.conf
```

## 6. Monitoring Configuration
```yaml
# Prometheus config
scrape_configs:
  - job_name: 'kafka'
    static_configs:
      - targets: ['broker1:7071', 'broker2:7071', 'broker3:7071']
    metrics_path: '/metrics'
```

## 7. Validation Tests
```bash
# Producer test
kafka-producer-perf-test.sh \
  --topic test-topic \
  --num-records 1000000 \
  --record-size 1000 \
  --throughput -1 \
  --producer-props bootstrap.servers=broker1:9092

# Consumer test
kafka-consumer-perf-test.sh \
  --topic test-topic \
  --bootstrap-server broker1:9092 \
  --messages 1000000 \
  --group test-group
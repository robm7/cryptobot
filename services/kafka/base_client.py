from confluent_kafka import Producer, Consumer
from typing import Callable, Optional
import json
from ..config import KafkaConfig

class KafkaBaseClient:
    def __init__(self, config: KafkaConfig):
        self.config = config

class KafkaProducer(KafkaBaseClient):
    def __init__(self, config: KafkaConfig):
        super().__init__(config)
        self.producer = Producer({
            'bootstrap.servers': ','.join(config.bootstrap_servers),
            'security.protocol': config.security_protocol,
            'sasl.mechanisms': config.sasl_mechanism,
            'sasl.username': config.sasl_username,
            'sasl.password': config.sasl_password
        })

    def produce(self, topic: str, key: str, value: dict):
        """Produce message to Kafka topic"""
        self.producer.produce(
            topic=topic,
            key=key,
            value=json.dumps(value),
            callback=self._delivery_report
        )
        self.producer.poll(0)

    @staticmethod
    def _delivery_report(err, msg):
        if err is not None:
            print(f'Message delivery failed: {err}')
        else:
            print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

class KafkaConsumer(KafkaBaseClient):
    def __init__(self, config: KafkaConfig):
        super().__init__(config)
        self.consumer = Consumer({
            'bootstrap.servers': ','.join(config.bootstrap_servers),
            'security.protocol': config.security_protocol,
            'sasl.mechanisms': config.sasl_mechanism,
            'sasl.username': config.sasl_username,
            'sasl.password': config.sasl_password,
            'group.id': config.group_id,
            'auto.offset.reset': config.auto_offset_reset,
            'enable.auto.commit': config.enable_auto_commit
        })

    def consume(self, topics: list, callback: Callable):
        """Consume messages from Kafka topics"""
        self.consumer.subscribe(topics)
        try:
            while True:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    print(f"Consumer error: {msg.error()}")
                    continue
                callback(msg.key(), json.loads(msg.value()))
        finally:
            self.consumer.close()
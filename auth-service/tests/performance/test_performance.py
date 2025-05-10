import pytest
import grpc
import time
import statistics
from locust import events
from auth_pb2 import KeyRequest, ListKeysRequest
from auth_pb2_grpc import KeyManagementServiceStub
from auth_service.auth_service import serve
import threading
import redis
from multiprocessing import Process

@pytest.fixture(scope="module")
def perf_test_server():
    """Fixture for performance test server"""
    redis_client = redis.Redis(host='localhost', port=6379, db=2)  # Use separate DB
    server_process = Process(
        target=serve,
        args=(redis_client,),
        kwargs={'port': 50054}
    )
    server_process.start()
    time.sleep(2)  # Give server time to start
    yield redis_client
    server_process.terminate()
    server_process.join()
    redis_client.flushdb()

@pytest.fixture
def perf_test_channel():
    """Fixture for performance test channel"""
    channel = grpc.insecure_channel('localhost:50054')
    yield channel
    channel.close()

class TestPerformance:
    @pytest.mark.parametrize("concurrency", [1, 10, 50])
    def test_get_current_key_latency(self, perf_test_server, perf_test_channel, concurrency):
        """Test latency of GetCurrentKey under different concurrency levels"""
        # Setup test key
        test_key = {
            "id": "perf_test_key",
            "is_active": True
        }
        perf_test_server.hset("keys:current", mapping=test_key)

        stub = KeyManagementServiceStub(perf_test_channel)
        latencies = []
        
        def make_request():
            start = time.time()
            stub.GetCurrentKey(KeyRequest())
            latencies.append(time.time() - start)

        threads = []
        for _ in range(concurrency):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        print(f"\nGetCurrentKey with {concurrency} concurrent requests:")
        print(f"Average latency: {statistics.mean(latencies)*1000:.2f}ms")
        print(f"Max latency: {max(latencies)*1000:.2f}ms")
        print(f"Min latency: {min(latencies)*1000:.2f}ms")

        assert statistics.mean(latencies) < 0.1  # Avg < 100ms

    def test_throughput(self, perf_test_server, perf_test_channel):
        """Test requests per second throughput"""
        stub = KeyManagementServiceStub(perf_test_channel)
        start = time.time()
        requests = 100
        for _ in range(requests):
            stub.GetCurrentKey(KeyRequest())

        duration = time.time() - start
        rps = requests / duration
        print(f"\nThroughput: {rps:.2f} requests/second")

        assert rps > 50  # Minimum 50 RPS

    def test_rotate_key_performance(self, perf_test_channel):
        """Test performance of key rotation operation"""
        stub = KeyManagementServiceStub(perf_test_channel)
        start = time.time()
        for _ in range(10):  # Test with 10 rotations
            stub.RotateKey(KeyRequest(expire_in_days=30))

        avg_time = (time.time() - start) / 10
        print(f"\nAverage RotateKey time: {avg_time*1000:.2f}ms")

        assert avg_time < 0.5  # Avg < 500ms per rotation
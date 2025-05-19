import pytest
from auth_service import AuthService
from key_manager import KeyManager
from key_service import KeyService
import redis

@pytest.fixture
def redis_client():
    """Fixture for Redis test client"""
    client = redis.Redis(host='localhost', port=6379, db=0)
    yield client
    client.flushdb()

@pytest.fixture
def auth_service(redis_client):
    """Fixture for AuthService with test Redis client"""
    return AuthService(redis_client)

@pytest.fixture 
def key_manager(redis_client):
    """Fixture for KeyManager with test Redis client"""
    return KeyManager(redis_client)

@pytest.fixture
def key_service(key_manager):
    """Fixture for KeyService with test KeyManager"""
    return KeyService(key_manager)

@pytest.fixture
def grpc_channel():
    """Fixture for gRPC test channel"""
    # Will be implemented after service stubs are created
    pass
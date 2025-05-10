import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from services.data.logging_middleware import RequestLoggingMiddleware
import logging
from io import StringIO

@pytest.fixture
def test_app():
    app = FastAPI()
    
    # Setup logging to capture output
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    logger = logging.getLogger("api")
    logger.addHandler(handler)
    
    # Add middleware
    app.add_middleware(RequestLoggingMiddleware, logger_name="api")
    
    @app.get("/test")
    async def test_endpoint(request: Request):
        return {"message": "success"}
    
    return app, log_stream

def test_request_logging(test_app):
    app, log_stream = test_app
    client = TestClient(app)
    
    response = client.get("/test")
    assert response.status_code == 200
    
    logs = log_stream.getvalue().splitlines()
    assert len(logs) == 2  # Request and response logs
    
    # Verify request log
    assert '"method": "GET"' in logs[0]
    assert '"path": "/test"' in logs[0]
    assert '"type": "request"' in logs[0]
    
    # Verify response log
    assert '"status_code": 200' in logs[1]
    assert '"type": "response"' in logs[1]

def test_error_logging(test_app):
    app, log_stream = test_app
    
    @app.get("/error")
    async def error_endpoint(request: Request):
        raise ValueError("Test error")
    
    client = TestClient(app)
    
    with pytest.raises(ValueError):
        client.get("/error")
    
    logs = log_stream.getvalue().splitlines()
    assert len(logs) >= 1  # At least error log
    
    # Verify error log
    assert '"error_type": "ValueError"' in logs[-1]
    assert '"error_message": "Test error"' in logs[-1]
    assert '"type": "error"' in logs[-1]

def test_request_id_header(test_app):
    app, _ = test_app
    client = TestClient(app)
    
    response = client.get("/test")
    assert "X-Request-ID" in response.headers
    assert isinstance(response.headers["X-Request-ID"], str)
    assert len(response.headers["X-Request-ID"]) == 36  # UUID length
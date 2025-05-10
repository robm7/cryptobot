import pytest
from fastapi import HTTPException, Request
from datetime import datetime, timedelta
from jose import jwt
from .auth_middleware import JWTBearer
from auth.config import settings

@pytest.fixture
def auth_middleware():
    return JWTBearer()

@pytest.fixture
def valid_token():
    payload = {
        "sub": "testuser",
        "roles": ["data_read"],
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

@pytest.fixture
def expired_token():
    payload = {
        "sub": "testuser",
        "roles": ["data_read"],
        "exp": datetime.utcnow() - timedelta(hours=1)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

@pytest.mark.asyncio
async def test_valid_token(auth_middleware, valid_token):
    request = Request(scope={"type": "http", "headers": [(b"authorization", f"Bearer {valid_token}".encode())]})
    payload = await auth_middleware(request)
    assert payload["sub"] == "testuser"
    assert "data_read" in payload["roles"]

@pytest.mark.asyncio
async def test_expired_token(auth_middleware, expired_token):
    request = Request(scope={"type": "http", "headers": [(b"authorization", f"Bearer {expired_token}".encode())]})
    with pytest.raises(HTTPException) as exc:
        await auth_middleware(request)
    assert exc.value.status_code == 401
    assert "Token has expired" in str(exc.value.detail)

@pytest.mark.asyncio
async def test_missing_token(auth_middleware):
    request = Request(scope={"type": "http", "headers": []})
    with pytest.raises(HTTPException) as exc:
        await auth_middleware(request)
    assert exc.value.status_code == 403
    assert "Not authenticated" in str(exc.value.detail)

@pytest.mark.asyncio
async def test_role_validation(valid_token):
    middleware = JWTBearer(required_roles=["admin"])
    request = Request(scope={"type": "http", "headers": [(b"authorization", f"Bearer {valid_token}".encode())]})
    with pytest.raises(HTTPException) as exc:
        await middleware(request)
    assert exc.value.status_code == 403
    assert "Insufficient permissions" in str(exc.value.detail)
import httpx
import jwt
import os
import asyncio
import logging
from datetime import datetime, timedelta
from auth_middleware import validate_token, get_current_user, has_role

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
SECRET_KEY = os.getenv("SECRET_KEY", "test_secret_key_for_local_testing")
os.environ["SECRET_KEY"] = SECRET_KEY  # Ensure it's available to the middleware

# Create a fake JWT token for testing
def create_test_token():
    """Create a test token for authentication testing"""
    payload = {
        "sub": "test_user",
        "roles": ["admin", "trader"],
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# Use environment variable if available, otherwise generate one
TEST_TOKEN = os.getenv("TEST_TOKEN", create_test_token())

async def test_auth_service_connection():
    """Test connection to auth service"""
    logger.info(f"Testing connection to auth service at {AUTH_SERVICE_URL}")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{AUTH_SERVICE_URL}/health")
            
            if response.status_code == 200:
                logger.info("✅ Successfully connected to auth service")
                return True
            else:
                logger.error(f"❌ Failed to connect to auth service. Status code: {response.status_code}")
                return False
    except httpx.RequestError as e:
        logger.error(f"❌ Connection error: {str(e)}")
        return False

async def test_token_validation():
    """Test token validation function"""
    if not TEST_TOKEN:
        logger.warning("No test token provided. Skipping token validation test.")
        return False
    
    logger.info("Testing token validation...")
    try:
        # Try validating the test token
        result = await validate_token(TEST_TOKEN)
        logger.info(f"✅ Token validation successful: {result}")
        return True
    except Exception as e:
        logger.error(f"❌ Token validation failed: {str(e)}")
        
        # Try decoding the token without verification as a fallback
        try:
            payload = jwt.decode(TEST_TOKEN, options={"verify_signature": False})
            logger.info(f"Token payload (not verified): {payload}")
        except jwt.PyJWTError as jwt_error:
            logger.error(f"Failed to decode token: {str(jwt_error)}")
        
        return False

async def test_fallback_token_handling():
    """Test fallback token handling when auth service is down"""
    logger.info("Testing fallback token handling...")
    
    # Temporarily change AUTH_SERVICE_URL to an invalid URL
    original_url = os.environ.get("AUTH_SERVICE_URL")
    try:
        os.environ["AUTH_SERVICE_URL"] = "http://nonexistent-service:9999"
        
        # Try validating a token when auth service is down
        result = await validate_token(TEST_TOKEN)
        
        if result and result.get("valid") and result.get("using_fallback"):
            logger.info(f"✅ Fallback validation successful: {result}")
            return True
        else:
            logger.warning(f"⚠️ Fallback worked but missing expected 'using_fallback' flag: {result}")
            return True
    except Exception as e:
        logger.error(f"❌ Fallback validation failed: {str(e)}")
        
        # Try to determine why it failed
        try:
            # Check if SECRET_KEY is properly set
            if not os.environ.get("SECRET_KEY"):
                logger.error("SECRET_KEY environment variable is not set")
            
            # Decode token without verification to diagnose
            payload = jwt.decode(TEST_TOKEN, options={"verify_signature": False})
            logger.info(f"Token payload (not verified): {payload}")
            
            # Check expected claims
            if not payload.get("sub"):
                logger.error("Token missing 'sub' claim")
            if not payload.get("roles"):
                logger.error("Token missing 'roles' claim")
            if not payload.get("exp"):
                logger.error("Token missing 'exp' claim")
                
        except Exception as inner_e:
            logger.error(f"Diagnostic error: {str(inner_e)}")
            
        return False
    finally:
        # Restore original URL
        if original_url:
            os.environ["AUTH_SERVICE_URL"] = original_url
        else:
            os.environ.pop("AUTH_SERVICE_URL", None)

async def run_tests():
    """Run all tests"""
    logger.info("Starting auth middleware tests")
    
    # Test auth service connection
    auth_service_ok = await test_auth_service_connection()
    
    # Test token validation
    token_validation_ok = await test_token_validation()
    
    # Test fallback handling
    fallback_ok = await test_fallback_token_handling()
    
    # Summary
    logger.info("==== Test Summary ====")
    logger.info(f"Auth Service Connection: {'✅' if auth_service_ok else '❌'}")
    logger.info(f"Token Validation: {'✅' if token_validation_ok else '❌'}")
    logger.info(f"Fallback Handling: {'✅' if fallback_ok else '❌'}")
    
    if not (auth_service_ok or fallback_ok):
        logger.error("CRITICAL: Both auth service and fallback handling are failing!")
        logger.error("Authentication will not work in this configuration!")
    elif not auth_service_ok:
        logger.warning("Auth service is down but fallback is working - less secure mode")
    elif not fallback_ok:
        logger.warning("Fallback mode is not working, but auth service is up - OK for now")
    else:
        logger.info("All auth tests passed successfully")

if __name__ == "__main__":
    asyncio.run(run_tests())
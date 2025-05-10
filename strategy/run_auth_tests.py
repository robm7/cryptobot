"""
Manual tests for authentication middleware
"""

import jwt
import logging
from datetime import datetime, timedelta
from auth_middleware import validate_token

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Secret key for token signing
SECRET_KEY = "test_secret_key_for_local_testing"

def create_test_token(username="test_user", roles=None, expire_minutes=30):
    """Create a test JWT token for authentication testing"""
    if roles is None:
        roles = ["admin", "trader"]
        
    payload = {
        "sub": username,
        "roles": roles,
        "token_type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=expire_minutes),
        "jti": f"test-{int(datetime.utcnow().timestamp())}"
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

async def test_validate_token():
    """Test token validation directly"""
    logger.info("Testing token validation...")
    
    # Test with admin token
    admin_token = create_test_token(username="admin_user", roles=["admin"])
    admin_result = await validate_token(admin_token)
    logger.info(f"Admin token validation result: {admin_result}")
    
    # Test with trader token
    trader_token = create_test_token(username="trader_user", roles=["trader"])
    trader_result = await validate_token(trader_token)
    logger.info(f"Trader token validation result: {trader_result}")
    
    # Test with viewer token
    viewer_token = create_test_token(username="viewer_user", roles=["viewer"])
    viewer_result = await validate_token(viewer_token)
    logger.info(f"Viewer token validation result: {viewer_result}")
    
    # Test with expired token
    expired_token = create_test_token(username="expired_user", roles=["admin"], expire_minutes=-5)
    try:
        expired_result = await validate_token(expired_token)
        logger.error(f"Expired token should have failed but returned: {expired_result}")
        return False
    except Exception as e:
        logger.info(f"Expired token correctly failed with: {str(e)}")
    
    # Test with malformed token
    malformed_token = "malformed.token.string"
    try:
        malformed_result = await validate_token(malformed_token)
        logger.error(f"Malformed token should have failed but returned: {malformed_result}")
        return False
    except Exception as e:
        logger.info(f"Malformed token correctly failed with: {str(e)}")
    
    return True

async def test_has_role():
    """Test role checking"""
    from auth_middleware import has_role
    
    logger.info("Testing role checking...")
    
    # Create dependency function
    admin_checker = has_role(["admin"])
    trader_checker = has_role(["trader"])
    viewer_checker = has_role(["viewer"])
    multi_role_checker = has_role(["admin", "trader"])
    
    # Test admin role
    admin_user = {"username": "admin", "roles": ["admin"]}
    trader_user = {"username": "trader", "roles": ["trader"]}
    viewer_user = {"username": "viewer", "roles": ["viewer"]}
    
    # Admin should have admin role
    try:
        result = await admin_checker(admin_user)
        logger.info("✅ Admin has admin role as expected")
    except Exception as e:
        logger.error(f"❌ Admin should have admin role but got error: {str(e)}")
        return False
    
    # Admin should not have trader role
    try:
        result = await trader_checker(admin_user)
        logger.error("❌ Admin should not have trader role but check passed")
        return False
    except Exception as e:
        logger.info("✅ Admin correctly lacks trader role")
    
    # Trader should be allowed when multiple roles are accepted
    try:
        result = await multi_role_checker(trader_user)
        logger.info("✅ Trader passes multi-role check as expected")
    except Exception as e:
        logger.error(f"❌ Trader should pass multi-role check but got error: {str(e)}")
        return False
    
    # Viewer should fail all role checks except viewer
    try:
        result = await viewer_checker(viewer_user)
        logger.info("✅ Viewer has viewer role as expected")
    except Exception as e:
        logger.error(f"❌ Viewer should have viewer role but got error: {str(e)}")
        return False
    
    # Viewer should not have admin role
    try:
        result = await admin_checker(viewer_user)
        logger.error("❌ Viewer should not have admin role but check passed")
        return False
    except Exception as e:
        logger.info("✅ Viewer correctly lacks admin role")
    
    return True

async def run_all_tests():
    """Run all auth middleware tests"""
    logger.info("Starting manual authentication tests...")
    
    # Run token validation tests
    token_validation_result = await test_validate_token()
    
    # Run role check tests
    role_check_result = await test_has_role()
    
    # Print summary
    logger.info("\n===== TEST RESULTS =====")
    logger.info(f"Token Validation: {'✅ PASS' if token_validation_result else '❌ FAIL'}")
    logger.info(f"Role Checking: {'✅ PASS' if role_check_result else '❌ FAIL'}")
    
    if token_validation_result and role_check_result:
        logger.info("\n🎉 All authentication tests passed!")
        return True
    else:
        logger.error("\n❌ Some tests failed. Review logs for details.")
        return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_all_tests())
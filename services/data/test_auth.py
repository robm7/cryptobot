import os
from datetime import datetime, timedelta
from jose import jwt
from auth.config import settings

# Test user data with different roles
TEST_USERS = [
    {
        "username": "data_reader",
        "roles": ["data_read"],
        "password": "reader_pass"
    },
    {
        "username": "data_writer", 
        "roles": ["data_read", "data_write"],
        "password": "writer_pass"
    },
    {
        "username": "monitoring",
        "roles": ["monitoring"],
        "password": "monitoring_pass"
    }
]

def create_test_token(user_data: dict, expires_in: int = 3600) -> str:
    """Create a test JWT token with specified roles"""
    expires = datetime.utcnow() + timedelta(seconds=expires_in)
    to_encode = {
        "sub": user_data["username"],
        "roles": user_data["roles"],
        "exp": expires
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

if __name__ == "__main__":
    print("Test tokens:")
    for user in TEST_USERS:
        token = create_test_token(user)
        print(f"\nUser: {user['username']}")
        print(f"Roles: {', '.join(user['roles'])}")
        print(f"Token: {token}")
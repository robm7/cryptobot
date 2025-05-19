from typing import Optional, List
from enum import Enum
import secrets
import pyotp
import json
import time
from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
# from sqlalchemy.ext.declarative import declarative_base # No longer needed here
from database.db import Base # Import shared Base
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext

# Base = declarative_base() # Removed, use shared Base
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Association table for users and roles
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("role_id", Integer, ForeignKey("roles.id"))
)

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)
    
    # Many-to-many relationship with users
    users = relationship("User", secondary=user_roles, back_populates="roles")


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    full_name = Column(String(100))
    hashed_password = Column(String(100))
    disabled = Column(Boolean, default=False)
    mfa_enabled = Column(Boolean, default=False)
    mfa_setup = Column(Boolean, default=False)
    totp_secret = Column(String(100), nullable=True)
    backup_codes = Column(Text, nullable=True)
    last_used_backup_code = Column(Integer, nullable=True)
    
    # Many-to-many relationship with roles
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    
    # API keys relationship
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    
    # Active sessions relationship
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

    @classmethod
    def get_user(cls, db, username: str):
        """Get user by username"""
        return db.query(cls).filter(cls.username == username).first()
        
    @classmethod
    def get_by_email(cls, db, email: str):
        """Get user by email"""
        return db.query(cls).filter(cls.email == email).first()
        
    def verify_password(self, password: str):
        """Verify password against stored hash"""
        return pwd_context.verify(password, self.hashed_password)
        
    def save(self, db):
        """Save user to database"""
        db.add(self)
        db.commit()
        db.refresh(self)
        return self

    @staticmethod
    def get_password_hash(password: str):
        """Generate password hash"""
        return pwd_context.hash(password)

    def generate_totp_secret(self):
        """Generate a new TOTP secret"""
        self.totp_secret = pyotp.random_base32()
        return self.totp_secret

    def get_totp_uri(self, issuer_name="Cryptobot"):
        """Get TOTP provisioning URI"""
        if not self.totp_secret:
            raise ValueError("TOTP secret not set")
        return pyotp.totp.TOTP(self.totp_secret).provisioning_uri(
            name=self.email,
            issuer_name=issuer_name
        )

    def verify_totp(self, code: str) -> bool:
        """Verify TOTP code"""
        if not self.totp_secret:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(code)

    def generate_backup_codes(self, count=10) -> List[str]:
        """Generate backup codes"""
        codes = [secrets.token_hex(4).upper() for _ in range(count)]
        self.backup_codes = json.dumps([pwd_context.hash(code) for code in codes])
        return codes

    def is_mfa_required(self) -> bool:
        """Check if MFA is required (admin users always require MFA)"""
        return any(role.name == "admin" for role in self.roles) or self.mfa_enabled

    def verify_backup_code(self, code: str) -> bool:
        """Verify backup code and mark as used if valid"""
        if not self.backup_codes:
            return False
            
        try:
            stored_codes = json.loads(self.backup_codes)
            for i, hashed_code in enumerate(stored_codes):
                if pwd_context.verify(code, hashed_code):
                    # Mark code as used by removing it
                    stored_codes.pop(i)
                    self.backup_codes = json.dumps(stored_codes)
                    self.last_used_backup_code = int(time.time())
                    return True
        except (json.JSONDecodeError, ValueError):
            pass
            
        return False


class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True)
    description = Column(String(200))
    exchange = Column(String(50))
    is_test = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Relationship to user
    user = relationship("User", back_populates="api_keys")


# Pydantic models for API
class RoleEnum(str, Enum):
    ADMIN = "admin"
    USER = "user"
    TRADER = "trader"
    READ_ONLY = "read_only"

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    disabled: Optional[bool] = False
    mfa_enabled: Optional[bool] = False
    mfa_setup: Optional[bool] = False

class UserCreate(UserBase):
    password: str
    roles: List[RoleEnum] = [RoleEnum.USER]

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    disabled: Optional[bool] = None
    roles: Optional[List[RoleEnum]] = None

class UserOut(UserBase):
    id: int
    roles: List[str]
    
    class Config:
        from_attributes = True

class APIKeyCreate(BaseModel):
    description: str
    exchange: str
    is_test: bool = False
    
class APIKeyOut(APIKeyCreate):
    id: int
    key: str
    
    class Config:
        from_attributes = True
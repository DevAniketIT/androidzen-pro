"""
User model for authentication and user management.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import Session, relationship
from .core.database import Base
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid


class User(Base):
    """
    Model representing a user account in AndroidZen Pro.
    """
    __tablename__ = "users"
    
    # Primary key
    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # Authentication credentials
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile information
    full_name = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    
    # Account status and permissions
    is_active = Column(Boolean, default=True, index=True)
    is_admin = Column(Boolean, default=False, index=True)
    is_verified = Column(Boolean, default=False)
    
    # Permissions and roles (JSON field for flexibility)
    permissions = Column(JSON, default=list)  # List of permission strings
    roles = Column(JSON, default=list)  # List of role names
    
    # Account settings
    preferences = Column(JSON, default=dict)  # User preferences
    
    # Security fields
    failed_login_attempts = Column(Integer, default=0)
    last_failed_login = Column(DateTime(timezone=True), nullable=True)
    account_locked_until = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), default=func.now())
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user_sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id='{self.id}', username='{self.username}', email='{self.email}')>"
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert user to dictionary representation."""
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "phone_number": self.phone_number,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "is_verified": self.is_verified,
            "permissions": self.permissions or [],
            "roles": self.roles or [],
            "preferences": self.preferences or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }
        
        if include_sensitive:
            data.update({
                "failed_login_attempts": self.failed_login_attempts,
                "last_failed_login": self.last_failed_login.isoformat() if self.last_failed_login else None,
                "account_locked_until": self.account_locked_until.isoformat() if self.account_locked_until else None,
                "password_changed_at": self.password_changed_at.isoformat() if self.password_changed_at else None
            })
        
        return data
    
    @classmethod
    def get_by_username(cls, db: Session, username: str) -> Optional['User']:
        """Get user by username."""
        return db.query(cls).filter(cls.username == username).first()
    
    @classmethod
    def get_by_email(cls, db: Session, email: str) -> Optional['User']:
        """Get user by email."""
        return db.query(cls).filter(cls.email == email).first()
    
    @classmethod
    def get_by_id(cls, db: Session, user_id: str) -> Optional['User']:
        """Get user by ID."""
        return db.query(cls).filter(cls.id == user_id).first()
    
    @classmethod
    def create_user(cls, db: Session, user_data: Dict[str, Any]) -> 'User':
        """Create a new user."""
        user = cls(**user_data)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @classmethod
    def get_all_users(cls, db: Session, skip: int = 0, limit: int = 100) -> List['User']:
        """Get all users with pagination."""
        return db.query(cls).offset(skip).limit(limit).all()
    
    def update_login_info(self, db: Session, success: bool = True):
        """Update login-related information."""
        if success:
            self.last_login = datetime.utcnow()
            self.failed_login_attempts = 0
            self.last_failed_login = None
        else:
            self.failed_login_attempts += 1
            self.last_failed_login = datetime.utcnow()
            
            # Lock account after 5 failed attempts for 15 minutes
            if self.failed_login_attempts >= 5:
                self.account_locked_until = datetime.utcnow() + timedelta(minutes=15)
        
        db.commit()
        db.refresh(self)
    
    def is_account_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.account_locked_until is None:
            return False
        return datetime.utcnow() < self.account_locked_until
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        if self.is_admin:
            return True
        return permission in (self.permissions or [])
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in (self.roles or [])
    
    def add_permission(self, db: Session, permission: str):
        """Add a permission to user."""
        if self.permissions is None:
            self.permissions = []
        if permission not in self.permissions:
            self.permissions.append(permission)
            db.commit()
            db.refresh(self)
    
    def remove_permission(self, db: Session, permission: str):
        """Remove a permission from user."""
        if self.permissions and permission in self.permissions:
            self.permissions.remove(permission)
            db.commit()
            db.refresh(self)
    
    def set_preference(self, db: Session, key: str, value: Any):
        """Set a user preference."""
        if self.preferences is None:
            self.preferences = {}
        self.preferences[key] = value
        db.commit()
        db.refresh(self)
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        if self.preferences is None:
            return default
        return self.preferences.get(key, default)


class UserSession(Base):
    """
    Model for tracking user login sessions.
    """
    __tablename__ = "user_sessions"
    
    # Primary key
    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign key to user
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    
    # Session information
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    refresh_token = Column(String(255), unique=True, index=True, nullable=True)
    
    # Session metadata
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    device_fingerprint = Column(String(255), nullable=True)
    
    # Session status
    is_active = Column(Boolean, default=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional session data
    session_data = Column(JSON, nullable=True)
    
    # Relationship back to user
    user = relationship("User", back_populates="user_sessions")
    
    def __repr__(self):
        return f"<UserSession(id='{self.id}', user_id='{self.user_id}', active={self.is_active})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
            "device_fingerprint": self.device_fingerprint,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "session_data": self.session_data
        }
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at
    
    def end_session(self, db: Session):
        """End the session."""
        self.is_active = False
        self.ended_at = datetime.utcnow()
        db.commit()
        db.refresh(self)
    
    def refresh_session(self, db: Session, extend_by_minutes: int = 30):
        """Refresh session expiry."""
        from datetime import timedelta
        self.expires_at = datetime.utcnow() + timedelta(minutes=extend_by_minutes)
        self.last_activity = datetime.utcnow()
        db.commit()
        db.refresh(self)
    
    @classmethod
    def get_active_sessions(cls, db: Session, user_id: str) -> List['UserSession']:
        """Get all active sessions for a user."""
        return db.query(cls).filter(
            cls.user_id == user_id,
            cls.is_active == True,
            cls.expires_at > datetime.utcnow()
        ).all()
    
    @classmethod
    def get_by_token(cls, db: Session, session_token: str) -> Optional['UserSession']:
        """Get session by token."""
        return db.query(cls).filter(cls.session_token == session_token).first()
    
    @classmethod
    def cleanup_expired_sessions(cls, db: Session) -> int:
        """Clean up expired sessions."""
        expired_sessions = db.query(cls).filter(
            cls.expires_at <= datetime.utcnow()
        ).all()
        
        for session in expired_sessions:
            session.is_active = False
            session.ended_at = datetime.utcnow()
        
        db.commit()
        return len(expired_sessions)


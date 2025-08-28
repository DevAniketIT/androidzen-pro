"""
Authentication and session management for AndroidZen Pro.
Handles JWT tokens, user authentication, and session management.
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()

class AuthManager:
    """Authentication manager for handling JWT tokens and user sessions."""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}  # In-memory session store
        self.blacklisted_tokens: set = set()  # Token blacklist
        
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        try:
            if token in self.blacklisted_tokens:
                return None
                
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.PyJWTError as e:
            logger.warning(f"Token verification failed: {e}")
            return None
    
    def create_session(self, user_data: Dict[str, Any], session_id: Optional[str] = None) -> str:
        """Create a new user session."""
        if not session_id:
            session_id = secrets.token_urlsafe(32)
        
        session_data = {
            "user_id": user_data.get("sub"),
            "username": user_data.get("username"),
            "email": user_data.get("email"),
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "user_agent": user_data.get("user_agent"),
            "ip_address": user_data.get("ip_address"),
            "is_active": True
        }
        
        self.active_sessions[session_id] = session_data
        logger.info(f"Created session for user: {user_data.get('username')}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by session ID."""
        session = self.active_sessions.get(session_id)
        if session and session["is_active"]:
            # Update last activity
            session["last_activity"] = datetime.utcnow()
            return session
        return None
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a user session."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["is_active"] = False
            logger.info(f"Invalidated session: {session_id}")
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions (call periodically)."""
        now = datetime.utcnow()
        expired_sessions = []
        
        for session_id, session_data in self.active_sessions.items():
            # Consider session expired if no activity for more than token expiry time
            if (now - session_data["last_activity"]).total_seconds() > (ACCESS_TOKEN_EXPIRE_MINUTES * 60):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Cleaned up expired session: {session_id}")
    
    def blacklist_token(self, token: str):
        """Add token to blacklist."""
        self.blacklisted_tokens.add(token)
        logger.info("Token added to blacklist")
    
    def get_user_sessions(self, user_id: str) -> list:
        """Get all active sessions for a user."""
        sessions = []
        for session_id, session_data in self.active_sessions.items():
            if session_data["user_id"] == user_id and session_data["is_active"]:
                sessions.append({
                    "session_id": session_id,
                    "created_at": session_data["created_at"],
                    "last_activity": session_data["last_activity"],
                    "user_agent": session_data.get("user_agent"),
                    "ip_address": session_data.get("ip_address")
                })
        return sessions
    
    def revoke_all_user_sessions(self, user_id: str) -> int:
        """Revoke all sessions for a specific user."""
        revoked_count = 0
        for session_id, session_data in self.active_sessions.items():
            if session_data["user_id"] == user_id and session_data["is_active"]:
                session_data["is_active"] = False
                revoked_count += 1
        
        logger.info(f"Revoked {revoked_count} sessions for user: {user_id}")
        return revoked_count

# Global auth manager instance
auth_manager = AuthManager()

class User:
    """User model for authentication (simplified for demo)."""
    
    # In a real application, this would come from a database
    _users = {
        "admin": {
            "id": "1",
            "username": "admin",
            "email": "admin@androidzen.com",
            "hashed_password": auth_manager.get_password_hash("admin123"),  # Default password
            "is_active": True,
            "is_admin": True,
            "permissions": ["read", "write", "admin"]
        },
        "demo": {
            "id": "2", 
            "username": "demo",
            "email": "demo@androidzen.com",
            "hashed_password": auth_manager.get_password_hash("demo123"),  # Default password
            "is_active": True,
            "is_admin": False,
            "permissions": ["read", "write"]
        }
    }
    
    @classmethod
    def get_by_username(cls, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        return cls._users.get(username)
    
    @classmethod
    def get_by_id(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        for user in cls._users.values():
            if user["id"] == user_id:
                return user
        return None
    
    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with username and password."""
        user = cls.get_by_username(username)
        if not user:
            return None
        if not auth_manager.verify_password(password, user["hashed_password"]):
            return None
        return user
    
    @classmethod
    def email_exists(cls, email: str) -> bool:
        """Check if email already exists."""
        for user in cls._users.values():
            if user["email"] == email:
                return True
        return False
    
    @classmethod
    def create_user(cls, username: str, email: str, password: str, full_name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new user account."""
        import uuid
        
        # Generate new user ID
        new_id = str(len(cls._users) + 1)
        
        # Hash password
        hashed_password = auth_manager.get_password_hash(password)
        
        # Create user data
        user_data = {
            "id": new_id,
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
            "is_active": True,
            "is_admin": False,
            "permissions": ["read", "write"],
            "full_name": full_name
        }
        
        # Store user
        cls._users[username] = user_data
        
        return user_data

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user credentials."""
    return User.authenticate(username, password)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = auth_manager.verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception
        
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
            
        # Check if it's an access token
        if payload.get("type") != "access":
            raise credentials_exception
            
    except Exception:
        raise credentials_exception
    
    user = User.get_by_username(username)
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get current active user."""
    if not current_user.get("is_active", False):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_admin_user(current_user: Dict[str, Any] = Depends(get_current_active_user)) -> Dict[str, Any]:
    """Get current admin user (for admin-only endpoints)."""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

def create_tokens_for_user(user: Dict[str, Any]) -> Dict[str, str]:
    """Create access and refresh tokens for a user."""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_manager.create_access_token(
        data={"sub": user["username"], "user_id": user["id"]},
        expires_delta=access_token_expires
    )
    
    refresh_token = auth_manager.create_refresh_token(
        data={"sub": user["username"], "user_id": user["id"]}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify refresh token and return user data."""
    payload = auth_manager.verify_token(token)
    if not payload or payload.get("type") != "refresh":
        return None
    
    username = payload.get("sub")
    if not username:
        return None
        
    return User.get_by_username(username)

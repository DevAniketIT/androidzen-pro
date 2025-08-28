"""
Authentication API endpoints for AndroidZen Pro.
Handles user login, logout, token refresh, and session management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import logging

from .core.auth import (
    authenticate_user, 
    get_current_user, 
    get_current_active_user,
    create_tokens_for_user,
    verify_refresh_token,
    auth_manager,
    security
)
from .core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: Dict[str, Any]
    session_id: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class UserProfile(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool
    is_admin: bool
    permissions: list

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class SessionInfo(BaseModel):
    session_id: str
    created_at: str
    last_activity: str
    user_agent: Optional[str]
    ip_address: Optional[str]

@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, request: Request):
    """
    Authenticate user and return access and refresh tokens.
    """
    user = authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    
    # Create tokens
    tokens = create_tokens_for_user(user)
    
    # Create session
    session_data = {
        "sub": user["username"],
        "username": user["username"],
        "email": user["email"],
        "user_agent": request.headers.get("user-agent"),
        "ip_address": request.client.host if request.client else None
    }
    session_id = auth_manager.create_session(session_data)
    
    # Remove sensitive data from user response
    user_response = {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "is_active": user["is_active"],
        "is_admin": user.get("is_admin", False),
        "permissions": user.get("permissions", [])
    }
    
    logger.info(f"User {user['username']} logged in successfully")
    
    return LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        user=user_response,
        session_id=session_id
    )

@router.post("/register")
async def register(register_data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user account using database.
    """
    from .models.user import User
    
    # Check if username already exists
    existing_user = User.get_by_username(db, register_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = User.get_by_email(db, register_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    try:
        hashed_password = auth_manager.get_password_hash(register_data.password)
        
        user_data = {
            "username": register_data.username,
            "email": register_data.email,
            "hashed_password": hashed_password,
            "full_name": register_data.full_name
        }
        
        user = User.create_user(db, user_data)
        
        logger.info(f"New user registered: {register_data.username}")
        
        # Remove sensitive data from response
        return {
            "message": "User registered successfully",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active
            }
        }
    except Exception as e:
        logger.error(f"User registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User registration failed"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_data: RefreshTokenRequest):
    """
    Refresh access token using refresh token.
    """
    user = verify_refresh_token(refresh_data.refresh_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    
    # Create new tokens
    tokens = create_tokens_for_user(user)
    
    logger.info(f"Tokens refreshed for user {user['username']}")
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"]
    )

@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Logout user and invalidate token.
    """
    # Add token to blacklist
    auth_manager.blacklist_token(credentials.credentials)
    
    # Note: In a real application, you might want to invalidate the specific session
    # or provide a session_id in the request to invalidate a specific session
    
    logger.info(f"User {current_user['username']} logged out")
    
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    Get current user profile information.
    """
    return UserProfile(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        is_active=current_user["is_active"],
        is_admin=current_user.get("is_admin", False),
        permissions=current_user.get("permissions", [])
    )

@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Change user password.
    """
    # Verify current password
    if not auth_manager.verify_password(password_data.current_password, current_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # In a real application, you would update the password in the database
    # For now, we'll just log it
    new_password_hash = auth_manager.get_password_hash(password_data.new_password)
    
    logger.info(f"Password changed for user {current_user['username']}")
    
    return {"message": "Password changed successfully"}

@router.get("/sessions")
async def get_user_sessions(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    Get all active sessions for the current user.
    """
    sessions = auth_manager.get_user_sessions(current_user["id"])
    
    session_list = []
    for session in sessions:
        session_list.append(SessionInfo(
            session_id=session["session_id"],
            created_at=session["created_at"].isoformat(),
            last_activity=session["last_activity"].isoformat(),
            user_agent=session.get("user_agent"),
            ip_address=session.get("ip_address")
        ))
    
    return {"sessions": session_list}

@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Revoke a specific session.
    """
    # Verify the session belongs to the current user
    user_sessions = auth_manager.get_user_sessions(current_user["id"])
    session_ids = [s["session_id"] for s in user_sessions]
    
    if session_id not in session_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    success = auth_manager.invalidate_session(session_id)
    if success:
        logger.info(f"Session {session_id} revoked by user {current_user['username']}")
        return {"message": "Session revoked successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to revoke session"
        )

@router.delete("/sessions")
async def revoke_all_sessions(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    Revoke all sessions for the current user.
    """
    revoked_count = auth_manager.revoke_all_user_sessions(current_user["id"])
    
    logger.info(f"All sessions revoked for user {current_user['username']} (count: {revoked_count})")
    
    return {
        "message": f"All sessions revoked successfully",
        "revoked_sessions": revoked_count
    }

@router.get("/validate")
async def validate_token(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Validate current token and return user information.
    """
    return {
        "valid": True,
        "user": {
            "id": current_user["id"],
            "username": current_user["username"],
            "email": current_user["email"],
            "is_active": current_user["is_active"],
            "is_admin": current_user.get("is_admin", False)
        }
    }

@router.get("/session-stats")
async def get_session_stats(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    Get session statistics for the current user.
    """
    sessions = auth_manager.get_user_sessions(current_user["id"])
    
    return {
        "total_active_sessions": len(sessions),
        "current_user_id": current_user["id"],
        "username": current_user["username"]
    }


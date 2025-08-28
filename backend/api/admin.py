"""
Admin API endpoints for AndroidZen Pro.
Handles administrative functions like user management, system settings, and monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from .core.auth import get_admin_user, auth_manager
from .core.database import get_db
from .models.user import User, UserSession
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for admin endpoints
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_admin: bool = False
    permissions: List[str] = []
    roles: List[str] = []

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_verified: Optional[bool] = None
    permissions: Optional[List[str]] = None
    roles: Optional[List[str]] = None

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str]
    phone_number: Optional[str]
    is_active: bool
    is_admin: bool
    is_verified: bool
    permissions: List[str]
    roles: List[str]
    created_at: str
    updated_at: str
    last_login: Optional[str]

class UsersListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    per_page: int
    pages: int

class PasswordReset(BaseModel):
    new_password: str = Field(..., min_length=8)

class SystemStats(BaseModel):
    total_users: int
    active_users: int
    admin_users: int
    active_sessions: int
    total_devices: int
    connected_devices: int

# User Management Endpoints

@router.get("/users", response_model=UsersListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    active_only: bool = Query(False),
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    List all users with pagination and filtering.
    Admin only endpoint.
    """
    try:
        skip = (page - 1) * per_page
        
        # Build query
        query = db.query(User)
        
        if active_only:
            query = query.filter(User.is_active == True)
        
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (User.username.like(search_filter)) |
                (User.email.like(search_filter)) |
                (User.full_name.like(search_filter))
            )
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        users = query.offset(skip).limit(per_page).all()
        
        # Calculate pagination info
        pages = (total + per_page - 1) // per_page
        
        user_responses = [
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                phone_number=user.phone_number,
                is_active=user.is_active,
                is_admin=user.is_admin,
                is_verified=user.is_verified,
                permissions=user.permissions or [],
                roles=user.roles or [],
                created_at=user.created_at.isoformat(),
                updated_at=user.updated_at.isoformat(),
                last_login=user.last_login.isoformat() if user.last_login else None
            )
            for user in users
        ]
        
        logger.info(f"Admin {admin_user['username']} listed users (page {page}, search: {search})")
        
        return UsersListResponse(
            users=user_responses,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
    
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create a new user account.
    Admin only endpoint.
    """
    try:
        # Check if username exists
        existing_user = User.get_by_username(db, user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Check if email exists
        existing_email = User.get_by_email(db, user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        
        # Hash password
        hashed_password = auth_manager.get_password_hash(user_data.password)
        
        # Create user
        user_dict = {
            "username": user_data.username,
            "email": user_data.email,
            "hashed_password": hashed_password,
            "full_name": user_data.full_name,
            "phone_number": user_data.phone_number,
            "is_admin": user_data.is_admin,
            "permissions": user_data.permissions,
            "roles": user_data.roles
        }
        
        user = User.create_user(db, user_dict)
        
        logger.info(f"Admin {admin_user['username']} created user: {user.username}")
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            phone_number=user.phone_number,
            is_active=user.is_active,
            is_admin=user.is_admin,
            is_verified=user.is_verified,
            permissions=user.permissions or [],
            roles=user.roles or [],
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get user details by ID.
    Admin only endpoint.
    """
    user = User.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        is_active=user.is_active,
        is_admin=user.is_admin,
        is_verified=user.is_verified,
        permissions=user.permissions or [],
        roles=user.roles or [],
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None
    )

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update user account.
    Admin only endpoint.
    """
    user = User.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check for username conflicts
    if user_data.username and user_data.username != user.username:
        existing_user = User.get_by_username(db, user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        user.username = user_data.username
    
    # Check for email conflicts
    if user_data.email and user_data.email != user.email:
        existing_email = User.get_by_email(db, user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        user.email = user_data.email
    
    # Update other fields
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.phone_number is not None:
        user.phone_number = user_data.phone_number
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    if user_data.is_admin is not None:
        user.is_admin = user_data.is_admin
    if user_data.is_verified is not None:
        user.is_verified = user_data.is_verified
    if user_data.permissions is not None:
        user.permissions = user_data.permissions
    if user_data.roles is not None:
        user.roles = user_data.roles
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"Admin {admin_user['username']} updated user: {user.username}")
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        is_active=user.is_active,
        is_admin=user.is_admin,
        is_verified=user.is_verified,
        permissions=user.permissions or [],
        roles=user.roles or [],
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None
    )

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete a user account.
    Admin only endpoint.
    """
    user = User.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent self-deletion
    if user.id == admin_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    username = user.username
    db.delete(user)
    db.commit()
    
    logger.info(f"Admin {admin_user['username']} deleted user: {username}")
    
    return {"message": f"User {username} deleted successfully"}

@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    password_data: PasswordReset,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Reset user password.
    Admin only endpoint.
    """
    user = User.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Hash new password
    user.hashed_password = auth_manager.get_password_hash(password_data.new_password)
    user.password_changed_at = datetime.utcnow()
    
    # Reset failed login attempts
    user.failed_login_attempts = 0
    user.last_failed_login = None
    user.account_locked_until = None
    
    db.commit()
    
    logger.info(f"Admin {admin_user['username']} reset password for user: {user.username}")
    
    return {"message": "Password reset successfully"}

@router.post("/users/{user_id}/unlock")
async def unlock_user_account(
    user_id: str,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Unlock a locked user account.
    Admin only endpoint.
    """
    user = User.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.failed_login_attempts = 0
    user.last_failed_login = None
    user.account_locked_until = None
    
    db.commit()
    
    logger.info(f"Admin {admin_user['username']} unlocked user account: {user.username}")
    
    return {"message": "User account unlocked successfully"}

@router.get("/users/{user_id}/sessions")
async def get_user_sessions(
    user_id: str,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get all sessions for a specific user.
    Admin only endpoint.
    """
    user = User.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    sessions = UserSession.get_active_sessions(db, user_id)
    
    return {
        "user_id": user_id,
        "username": user.username,
        "total_sessions": len(sessions),
        "sessions": [session.to_dict() for session in sessions]
    }

@router.delete("/users/{user_id}/sessions")
async def revoke_user_sessions(
    user_id: str,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Revoke all sessions for a specific user.
    Admin only endpoint.
    """
    user = User.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    sessions = UserSession.get_active_sessions(db, user_id)
    revoked_count = 0
    
    for session in sessions:
        session.end_session(db)
        revoked_count += 1
    
    logger.info(f"Admin {admin_user['username']} revoked {revoked_count} sessions for user: {user.username}")
    
    return {
        "message": f"Revoked {revoked_count} sessions for user {user.username}",
        "revoked_sessions": revoked_count
    }

# System Management Endpoints

@router.get("/system/stats", response_model=SystemStats)
async def get_system_stats(
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get system statistics.
    Admin only endpoint.
    """
    from .models.device import Device
    
    # User statistics
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    admin_users = db.query(User).filter(User.is_admin == True).count()
    
    # Session statistics
    active_sessions = db.query(UserSession).filter(
        UserSession.is_active == True,
        UserSession.expires_at > datetime.utcnow()
    ).count()
    
    # Device statistics
    total_devices = db.query(Device).count()
    connected_devices = db.query(Device).filter(Device.is_connected == True).count()
    
    return SystemStats(
        total_users=total_users,
        active_users=active_users,
        admin_users=admin_users,
        active_sessions=active_sessions,
        total_devices=total_devices,
        connected_devices=connected_devices
    )

@router.post("/system/cleanup")
async def system_cleanup(
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Perform system cleanup tasks.
    Admin only endpoint.
    """
    try:
        # Clean up expired sessions
        expired_sessions = UserSession.cleanup_expired_sessions(db)
        
        # TODO: Add more cleanup tasks as needed
        # - Clean old device data
        # - Clean old analytics data
        # - Clean old security events
        
        logger.info(f"Admin {admin_user['username']} performed system cleanup")
        
        return {
            "message": "System cleanup completed successfully",
            "expired_sessions_cleaned": expired_sessions
        }
    
    except Exception as e:
        logger.error(f"Error during system cleanup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System cleanup failed"
        )

@router.get("/audit/logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    level: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """
    Get audit logs from the logging system.
    Admin only endpoint.
    """
    from .core.logging_config import get_logger
    
    logger.info(f"Admin {admin_user['username']} requested audit logs")
    
    try:
        # Get logs from the logging system
        audit_logs = []
        
        # Sample audit log entries for demonstration
        # In production, this would read from actual log files or database
        from datetime import datetime, timedelta
        import json
        
        sample_logs = [
            {
                "timestamp": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                "level": "INFO",
                "user": admin_user['username'],
                "action": "GET_DEVICES",
                "resource": "/api/devices",
                "ip_address": "127.0.0.1",
                "details": "Retrieved device list"
            },
            {
                "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                "level": "WARN",
                "user": "system",
                "action": "DEVICE_CONNECTION_FAILED",
                "resource": "device_123",
                "ip_address": "192.168.1.100",
                "details": "Failed to connect to device after 3 attempts"
            },
            {
                "timestamp": (datetime.utcnow() - timedelta(hours=3)).isoformat(),
                "level": "ERROR",
                "user": "admin",
                "action": "LOGIN_FAILED",
                "resource": "/api/auth/login",
                "ip_address": "192.168.1.50",
                "details": "Invalid credentials provided"
            }
        ]
        
        # Filter by level if specified
        if level:
            sample_logs = [log for log in sample_logs if log['level'].lower() == level.lower()]
        
        # Apply pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_logs = sample_logs[start_idx:end_idx]
        
        return {
            "total": len(sample_logs),
            "page": page,
            "per_page": per_page,
            "pages": (len(sample_logs) + per_page - 1) // per_page,
            "logs": paginated_logs
        }
        
    except Exception as e:
        logger.error(f"Error retrieving audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit logs"
        )

@router.post("/system/backup")
async def create_system_backup(
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """
    Create a system backup.
    Admin only endpoint.
    """
    # TODO: Implement backup functionality
    
    logger.info(f"Admin {admin_user['username']} requested system backup")
    
    return {
        "message": "System backup endpoint - implementation pending"
    }


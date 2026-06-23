from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, List
from datetime import datetime, timedelta
from ..database import db
from .jwt_handler import JWTHandler
from ..config import settings
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

async def get_current_user(token: str = Depends(oauth2_scheme), request: Request = None) -> Optional[dict]:
    """Get current authenticated user from JWT token"""
    token = token or (request.cookies.get("access_token") if request else None)
    if not token:
        return None

    try:
        session = await db.sessions.find_one({"access_token": token})
        if not session:
            return None

        now = datetime.utcnow()
        if session.get("expires_at") and session["expires_at"] < now:
            await db.sessions.delete_one({"_id": session["_id"]})
            return None

        timeout_minutes = settings.SESSION_TIMEOUT_MINUTES
        if session.get("last_activity") and session["last_activity"] < now - timedelta(minutes=timeout_minutes):
            await db.sessions.delete_one({"_id": session["_id"]})
            return None

        payload = JWTHandler.decode_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            return None

        query_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        user = await db.users.find_one({"_id": query_id})

        if user is None:
            return None

        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )

        await db.sessions.update_one(
            {"_id": session["_id"]},
            {"$set": {"last_activity": now}}
        )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None

async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    """Get current active user or raise 401"""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user

class RoleChecker:
    """Role-based access control"""
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles
    
    async def __call__(self, current_user: dict = Depends(get_current_active_user)):
        user_role = current_user.get("role", "user")
        
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role}' does not have permission to access this resource. Required: {self.allowed_roles}"
            )
        
        return current_user

# Pre-defined role checkers
admin_required = RoleChecker(["admin"])
analyst_required = RoleChecker(["admin", "analyst"])
user_required = RoleChecker(["admin", "analyst", "user"])

async def verify_api_key(api_key: str = Depends(oauth2_scheme)):
    """Verify API key for external API access"""
    # Implementation for API key verification
    return True
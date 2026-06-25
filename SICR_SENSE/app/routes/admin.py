from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import secrets
from bson import ObjectId

from ..database import db
from ..auth.dependencies import get_current_user, RoleChecker
from ..schemas import UserResponse, AdminStats, UserActivity

logger = logging.getLogger(__name__)
router = APIRouter()

# Admin-only access
admin_only = RoleChecker(["admin"])

def to_user_dict(user: dict) -> dict:
    return {
        "id": str(user.get("_id")),
        "username": user.get("username"),
        "email": user.get("email"),
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "role": user.get("role", "user"),
        "is_active": user.get("is_active", True),
        "is_verified": user.get("is_verified", False),
        "two_factor_enabled": user.get("two_factor_enabled", False),
        "last_login": user.get("last_login"),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at")
    }

@router.get("/overview", response_model=AdminStats)
async def get_admin_overview(current_user: dict = Depends(admin_only)):
    """Get admin dashboard overview statistics"""
    try:
        # Get user statistics
        total_users = await db.users.count_documents({})
        active_users = await db.users.count_documents({"is_active": True})
        
        # Get session statistics
        active_sessions = await db.sessions.count_documents({
            "expires_at": {"$gt": datetime.utcnow()}
        })
        
        # Get API usage for today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        api_calls_today = await db.api_usage.count_documents({
            "timestamp": {"$gte": today_start}
        })
        
        # Get user growth data (last 30 days)
        user_growth = []
        for i in range(30, 0, -1):
            date = datetime.utcnow() - timedelta(days=i)
            next_date = date + timedelta(days=1)
            count = await db.users.count_documents({
                "created_at": {"$gte": date, "$lt": next_date}
            })
            user_growth.append({
                "date": date.strftime("%Y-%m-%d"),
                "count": count
            })
        
        # Get API usage data (last 24 hours)
        api_usage = []
        for i in range(24, 0, -1):
            hour_start = datetime.utcnow() - timedelta(hours=i)
            hour_end = hour_start + timedelta(hours=1)
            count = await db.api_usage.count_documents({
                "timestamp": {"$gte": hour_start, "$lt": hour_end}
            })
            api_usage.append({
                "hour": hour_start.strftime("%H:00"),
                "count": count
            })
        
        return AdminStats(
            total_users=total_users,
            active_users=active_users,
            active_sessions=active_sessions,
            api_calls_today=api_calls_today,
            user_growth_labels=[g["date"] for g in user_growth],
            user_growth_data=[g["count"] for g in user_growth],
            api_usage_labels=[u["hour"] for u in api_usage],
            api_usage_data=[u["count"] for u in api_usage]
        )
        
    except Exception as e:
        logger.error(f"Failed to get admin overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users")
async def get_all_users(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    role: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(admin_only)
):
    """Get all users with pagination and filtering"""
    try:
        # Build filter
        filter_query = {}
        if role:
            filter_query["role"] = role
        if status:
            filter_query["is_active"] = status == "active"
        if search:
            filter_query["$or"] = [
                {"username": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
                {"first_name": {"$regex": search, "$options": "i"}},
                {"last_name": {"$regex": search, "$options": "i"}}
            ]
        
        # Get total count
        total = await db.users.count_documents(filter_query)
        
        # Get users with pagination
        users = await db.users.find(filter_query) \
            .skip((page - 1) * limit) \
            .limit(limit) \
            .sort("created_at", -1) \
            .to_list(length=limit)
        
        return {
            "users": [to_user_dict(user) for user in users],
            "page": page,
            "pages": (total + limit - 1) // limit,
            "total": total
        }
        
    except Exception as e:
        logger.error(f"Failed to get users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}")
async def get_user_by_id(
    user_id: str,
    current_user: dict = Depends(admin_only)
):
    """Get a single user by ID"""
    query_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
    user = await db.users.find_one({"_id": query_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return to_user_dict(user)


@router.post("/users")
async def create_user(
    user_data: Dict[str, Any],
    current_user: dict = Depends(admin_only)
):
    """Create new user (admin only)"""
    try:
        # Check existing user
        existing = await db.users.find_one({
            "$or": [
                {"email": user_data["email"]},
                {"username": user_data["username"]}
            ]
        })
        
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")
        
        from ..auth.jwt_handler import JWTHandler
        provided_password = "password" in user_data and bool(user_data.get("password"))
        password = user_data.get("password") or secrets.token_urlsafe(12)
        user_data["password_hash"] = JWTHandler.hash_password(password)
        user_data.pop("password", None)
        
        # Return generated password only when admin did not supply one
        generated_password = password if not provided_password else None
        
        # Set defaults
        user_data.update({
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True,
            "is_verified": True,
            "two_factor_enabled": False
        })
        
        result = await db.users.insert_one(user_data)
        
        # Log activity
        await db.audit_logs.insert_one({
            "user_id": str(current_user["_id"]),
            "action": "create_user",
            "target_user": str(result.inserted_id),
            "timestamp": datetime.utcnow(),
            "details": f"Created user {user_data['username']}"
        })
        
        response = {
            "message": "User created successfully",
            "user_id": str(result.inserted_id)
        }
        if generated_password:
            response["generated_password"] = generated_password
        return response
        
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    user_data: Dict[str, Any],
    current_user: dict = Depends(admin_only)
):
    """Update user details"""
    try:
        # Remove sensitive fields
        if "password" in user_data:
            from ..auth.jwt_handler import JWTHandler
            user_data["password_hash"] = JWTHandler.hash_password(user_data["password"])
            del user_data["password"]
        
        user_data["updated_at"] = datetime.utcnow()
        
        query_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        result = await db.users.update_one(
            {"_id": query_id},
            {"$set": user_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Log activity
        await db.audit_logs.insert_one({
            "user_id": str(current_user["_id"]),
            "action": "update_user",
            "target_user": user_id,
            "timestamp": datetime.utcnow(),
            "details": f"Updated user {user_id}"
        })
        
        return {"message": "User updated successfully"}
        
    except Exception as e:
        logger.error(f"Failed to update user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(admin_only)
):
    """Delete user"""
    try:
        query_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        result = await db.users.delete_one({"_id": query_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Clean up related data
        await db.sessions.delete_many({"user_id": user_id})
        await db.api_usage.delete_many({"user_id": user_id})
        
        # Log activity
        await db.audit_logs.insert_one({
            "user_id": str(current_user["_id"]),
            "action": "delete_user",
            "target_user": user_id,
            "timestamp": datetime.utcnow(),
            "details": f"Deleted user {user_id}"
        })
        
        return {"message": "User deleted successfully"}
        
    except Exception as e:
        logger.error(f"Failed to delete user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/activity")
async def get_user_activity(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(admin_only)
):
    """Get user activity logs"""
    try:
        activities = await db.audit_logs.find() \
            .skip((page - 1) * limit) \
            .limit(limit) \
            .sort("timestamp", -1) \
            .to_list(length=limit)
        
        total = await db.audit_logs.count_documents({})
        
        return {
            "activities": activities,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit
        }
        
    except Exception as e:
        logger.error(f"Failed to get activity logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
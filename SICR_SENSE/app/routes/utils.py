from fastapi import APIRouter, HTTPException, Depends, Query, Body, Response
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from ..database import db
from ..auth.dependencies import get_current_active_user, RoleChecker

router = APIRouter()
admin_only = RoleChecker(["admin"])


def _parse_ids(ids: List[str]):
    parsed_ids = []
    for item in ids:
        if ObjectId.is_valid(item):
            parsed_ids.append(ObjectId(item))
        else:
            parsed_ids.append(item)
    return parsed_ids


# ============================================================
# FIX: Lazy initialization of collection mappings
# ============================================================
def get_collection(name: str):
    """Lazy get collection by name to avoid import-time database access"""
    collections = {
        "users": db.users,
        "predictions": db.predictions,
        "audit_logs": db.audit_logs,
        "notifications": db.notifications,
        "error_reports": db.error_reports
    }
    return collections.get(name)


@router.post("/bulk-delete")
async def bulk_delete(
    payload: Dict[str, Any] = Body(...),
    current_user: dict = Depends(admin_only)
):
    if not payload or not isinstance(payload.get("ids"), list):
        raise HTTPException(status_code=400, detail="ids must be provided as an array")

    collection_name = payload.get("collection", "users")
    collection = get_collection(collection_name)
    if collection is None:
        raise HTTPException(status_code=400, detail="Unsupported collection for bulk delete")

    ids = payload["ids"]
    parsed_ids = _parse_ids(ids)
    delete_filter = {"_id": {"$in": parsed_ids}}
    result = await collection.delete_many(delete_filter)

    if collection_name == "users":
        await db.sessions.delete_many({"user_id": {"$in": [str(item) for item in parsed_ids]}})
        await db.api_usage.delete_many({"user_id": {"$in": [str(item) for item in parsed_ids]}})

    return {
        "deleted_count": result.deleted_count,
        "collection": collection_name
    }


@router.get("/export")
async def export_items(
    ids: str = Query(...),
    collection: Optional[str] = Query("users"),
    current_user: dict = Depends(admin_only)
):
    collection_obj = get_collection(collection)
    if collection_obj is None:
        raise HTTPException(status_code=400, detail="Unsupported collection for export")

    ids_list = [item.strip() for item in ids.split(",") if item.strip()]
    parsed_ids = _parse_ids(ids_list)

    records = await collection_obj.find({"_id": {"$in": parsed_ids}}).to_list(length=len(parsed_ids))
    if not records:
        raise HTTPException(status_code=404, detail="No records found for export")

    # Build a basic CSV export with available fields
    headers = sorted({key for record in records for key in record.keys() if key != "_id"})
    csv_rows = [",".join(["id"] + headers)]
    for record in records:
        row = [str(record.get("_id"))]
        for field in headers:
            value = record.get(field, "")
            cell = str(value).replace('"', '""')
            row.append(f'"{cell}"')
        csv_rows.append(",".join(row))

    csv_data = "\n".join(csv_rows)
    filename = f"{collection}_export_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.csv"

    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/report-error")
async def report_error(
    error_info: Dict[str, Any] = Body(...),
    current_user: Optional[dict] = Depends(get_current_active_user)
):
    error_doc = {
        "user_id": str(current_user["_id"]) if current_user else None,
        "timestamp": datetime.utcnow(),
        "error_info": error_info
    }
    result = await db.error_reports.insert_one(error_doc)
    return {"message": "Error report submitted", "report_id": str(result.inserted_id)}


@router.get("/search")
async def search(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_active_user)
):
    q_regex = {"$regex": q, "$options": "i"}
    results = []

    try:
        users = await db.users.find({"$or": [{"username": q_regex}, {"email": q_regex}, {"first_name": q_regex}, {"last_name": q_regex}]}).limit(limit).to_list(length=limit)
        for user in users:
            # Convert ObjectId to string
            user_id = str(user["_id"])
            results.append({
                "id": user_id,
                "title": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get("username"),
                "subtitle": user.get("email"),
                "type": "User",
                "url": f"/admin/users/{user_id}",
                "icon": "fa-user"
            })

        if len(results) < limit:
            predictions = await db.predictions.find({"$or": [{"input.loan_id": q_regex}, {"output.risk_tier": q_regex}]}).limit(limit - len(results)).to_list(length=limit - len(results))
            for pred in predictions:
                results.append({
                    "id": str(pred["_id"]),
                    "title": pred.get("input", {}).get("loan_id", "Prediction"),
                    "subtitle": pred.get("output", {}).get("risk_tier", ""),
                    "type": "Prediction",
                    "url": "/dashboard",
                    "icon": "fa-chart-line"
                })

        if len(results) < limit:
            logs = await db.audit_logs.find({"details": q_regex}).limit(limit - len(results)).to_list(length=limit - len(results))
            for log in logs:
                results.append({
                    "id": str(log["_id"]),
                    "title": log.get("action", "Audit Event"),
                    "subtitle": log.get("details", ""),
                    "type": "Audit",
                    "url": "/admin/audit",
                    "icon": "fa-history"
                })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search service unavailable: {str(e)}")

    return {"results": results[:limit]}


@router.get("/notifications")
async def get_notifications(
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_active_user)
):
    user_id = str(current_user["_id"])
    notifications = await db.notifications.find({"user_id": user_id}).sort("created_at", -1).limit(limit).to_list(length=limit)
    unread_count = await db.notifications.count_documents({"user_id": user_id, "read": False})
    
    # Convert ObjectIds to strings for JSON serialization
    serialized = []
    for notif in notifications:
        notif["_id"] = str(notif["_id"])
        serialized.append(notif)
    
    return {
        "notifications": serialized,
        "unread_count": unread_count,
        "total": len(serialized)
    }


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    user_id = str(current_user["_id"])
    query_id = ObjectId(notification_id) if ObjectId.is_valid(notification_id) else notification_id
    result = await db.notifications.update_one(
        {"_id": query_id, "user_id": user_id},
        {"$set": {"read": True, "read_at": datetime.utcnow()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: dict = Depends(get_current_active_user)
):
    user_id = str(current_user["_id"])
    await db.notifications.update_many(
        {"user_id": user_id, "read": False},
        {"$set": {"read": True, "read_at": datetime.utcnow()}}
    )
    return {"message": "All notifications marked as read"}
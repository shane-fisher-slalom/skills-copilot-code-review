"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


def serialize_announcement(announcement: Dict) -> Dict:
    """Convert MongoDB document to JSON-serializable format"""
    if "_id" in announcement:
        announcement["id"] = str(announcement["_id"])
        del announcement["_id"]
    return announcement


@router.get("/active", response_model=List[Dict[str, Any]])
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get all currently active announcements (within date range)"""
    now = datetime.now().isoformat()
    
    # Query for announcements that are currently active
    query = {
        "$or": [
            # No start date or start date in the past, and end date in the future
            {
                "$and": [
                    {"$or": [{"start_date": None}, {"start_date": {"$lte": now}}]},
                    {"end_date": {"$gte": now}}
                ]
            }
        ]
    }
    
    announcements = []
    for announcement in announcements_collection.find(query).sort("created_at", -1):
        announcements.append(serialize_announcement(announcement))
    
    return announcements


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_all_announcements(teacher_username: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """Get all announcements (requires authentication) - for management interface"""
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    announcements = []
    for announcement in announcements_collection.find().sort("created_at", -1):
        announcements.append(serialize_announcement(announcement))
    
    return announcements


@router.post("", response_model=Dict[str, Any])
@router.post("/", response_model=Dict[str, Any])
def create_announcement(
    message: str,
    end_date: str,
    teacher_username: str = Query(...),
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new announcement (requires authentication)"""
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    # Validate dates
    try:
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if start_dt >= end_dt:
                raise HTTPException(
                    status_code=400, detail="Start date must be before end date")
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format")
    
    # Create announcement document
    announcement = {
        "message": message,
        "start_date": start_date,
        "end_date": end_date,
        "created_by": teacher_username,
        "created_at": datetime.now().isoformat()
    }
    
    result = announcements_collection.insert_one(announcement)
    announcement["id"] = str(result.inserted_id)
    
    return announcement


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    message: str,
    end_date: str,
    teacher_username: str = Query(...),
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """Update an existing announcement (requires authentication)"""
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    # Validate announcement exists
    try:
        obj_id = ObjectId(announcement_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    existing = announcements_collection.find_one({"_id": obj_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Validate dates
    try:
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if start_dt >= end_dt:
                raise HTTPException(
                    status_code=400, detail="Start date must be before end date")
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format")
    
    # Update announcement
    update_data = {
        "message": message,
        "start_date": start_date,
        "end_date": end_date,
        "updated_by": teacher_username,
        "updated_at": datetime.now().isoformat()
    }
    
    announcements_collection.update_one(
        {"_id": obj_id},
        {"$set": update_data}
    )
    
    updated = announcements_collection.find_one({"_id": obj_id})
    return serialize_announcement(updated)


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    teacher_username: str = Query(...)
) -> Dict[str, str]:
    """Delete an announcement (requires authentication)"""
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    # Validate announcement exists
    try:
        obj_id = ObjectId(announcement_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    result = announcements_collection.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}

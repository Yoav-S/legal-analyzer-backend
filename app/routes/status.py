"""
Document processing status endpoints.
"""
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_current_user_id, get_mongodb_db
from app.models.document import Document
from app.utils.errors import NotFoundError

router = APIRouter()


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_mongodb_db),
):
    """
    Get document processing status.
    
    Returns:
        Status information with progress
    """
    document = await Document.get_by_id(db, document_id, user_id)
    if not document:
        raise NotFoundError("Document", document_id)
    
    # Calculate progress percentage based on status
    status_progress = {
        "uploaded": 10,
        "parsing": 20,
        "waiting_in_queue": 30,
        "processing": 50,
        "building_report": 80,
        "completed": 100,
        "failed": 0,
    }
    
    progress = status_progress.get(document.status, 0)
    
    return {
        "document_id": document.document_id,
        "status": document.status,
        "progress_percent": progress,
        "error_message": document.error_message,
        "processing_started_at": document.processing_started_at.isoformat() if document.processing_started_at else None,
        "processing_completed_at": document.processing_completed_at.isoformat() if document.processing_completed_at else None,
    }


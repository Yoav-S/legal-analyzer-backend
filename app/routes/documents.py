"""
Document management endpoints.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_current_user_id, get_mongodb_db
from app.models.document import Document
from app.utils.errors import NotFoundError, AuthorizationError
from app.services.storage import StorageService

router = APIRouter()


@router.get("")
async def list_documents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    document_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_mongodb_db),
):
    """
    List user's documents with pagination and filters.
    
    Returns:
        List of documents with pagination metadata
    """
    documents = await Document.list_by_user(
        db=db,
        user_id=user_id,
        skip=skip,
        limit=limit,
        document_type=document_type,
        status=status,
    )
    
    total = await Document.count_by_user(
        db=db,
        user_id=user_id,
        document_type=document_type,
        status=status,
    )
    
    return {
        "documents": [doc.model_dump() for doc in documents],
        "pagination": {
            "skip": skip,
            "limit": limit,
            "total": total,
            "has_more": (skip + limit) < total,
        },
    }


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_mongodb_db),
):
    """
    Get document by ID.
    
    Returns:
        Document details
    """
    document = await Document.get_by_id(db, document_id, user_id)
    if not document:
        raise NotFoundError("Document", document_id)
    
    return document.model_dump()


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_mongodb_db),
):
    """
    Delete document and associated files.
    
    Returns:
        Success message
    """
    document = await Document.get_by_id(db, document_id, user_id)
    if not document:
        raise NotFoundError("Document", document_id)
    
    # Delete from storage
    storage = StorageService()
    file_key = storage.extract_file_key_from_url(document.file_url)
    await storage.delete_file(file_key)
    
    # Delete from database
    await document.delete(db)
    
    return {"message": "Document deleted successfully"}


"""
Document upload endpoints.
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_current_user_id, get_mongodb_db
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.services.storage import StorageService
from app.utils.errors import FileUploadError, ValidationError
from app.utils.security import validate_file_type, validate_file_size
from app.config import settings

router = APIRouter()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(default="other"),
    language: str = Form(default="en"),
    notes: str = Form(default=None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_mongodb_db),
):
    """
    Upload a document for analysis.
    
    Args:
        file: Uploaded file
        document_type: Type of document (contract, nda, employment, etc.)
        language: Document language code
        notes: Optional user notes
        
    Returns:
        Document metadata
    """
    # Validate file
    if not validate_file_type(file.filename):
        raise FileUploadError(
            f"Invalid file type. Allowed: {', '.join(settings.allowed_file_extensions)}"
        )
    
    # Read file content
    file_content = await file.read()
    file_size = len(file_content)
    
    if not validate_file_size(file_size):
        raise FileUploadError(
            f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB"
        )
    
    # Check user credits
    user = await User.get_by_id(db, user_id)
    if not user:
        raise ValidationError("User not found")
    
    plan_limits = user.get_plan_limits()
    if plan_limits["monthly_limit"] > 0:
        # Check if user has credits
        if user.credits_remaining <= 0:
            raise ValidationError(
                "Insufficient credits. Please upgrade your plan or wait for next billing cycle."
            )
    
    # Upload to storage
    storage = StorageService()
    try:
        file_url = await storage.upload_file(
            file_content=file_content,
            file_name=file.filename,
            user_id=user_id,
        )
    except Exception as e:
        raise FileUploadError(f"Failed to upload file: {str(e)}")
    
    # Create document record
    file_extension = file.filename.split(".")[-1].lower()
    document = await Document.create(
        db,
        {
            "user_id": user_id,
            "name": file.filename,
            "file_url": file_url,
            "file_type": file_extension,
            "file_size": file_size,
            "document_type": document_type,
            "status": DocumentStatus.UPLOADED,
            "language": language,
            "notes": notes,
        },
    )
    
    # Consume credit
    if plan_limits["monthly_limit"] > 0:
        await user.consume_credit(db)
    
    return {
        "document_id": document.document_id,
        "name": document.name,
        "upload_url": document.file_url,
        "status": document.status,
        "created_at": document.created_at.isoformat(),
    }


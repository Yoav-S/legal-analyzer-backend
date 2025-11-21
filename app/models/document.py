"""
Document MongoDB model.
"""
from typing import Optional, Literal
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from bson import ObjectId

from app.utils.errors import NotFoundError


class DocumentStatus(str):
    """Document processing status."""
    UPLOADED = "uploaded"
    PARSING = "parsing"
    WAITING_IN_QUEUE = "waiting_in_queue"
    PROCESSING = "processing"
    BUILDING_REPORT = "building_report"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str):
    """Document type."""
    CONTRACT = "contract"
    NDA = "nda"
    EMPLOYMENT = "employment"
    LEASE = "lease"
    COURT_FILING = "court_filing"
    OTHER = "other"


class Document(BaseModel):
    """Document model for MongoDB."""
    
    document_id: str = Field(default_factory=lambda: str(ObjectId()), description="Unique document ID")
    user_id: str = Field(..., description="Owner user ID")
    name: str = Field(..., description="Original file name")
    file_url: str = Field(..., description="S3/R2 file URL")
    file_type: str = Field(..., description="File extension: pdf, docx, txt")
    file_size: int = Field(..., description="File size in bytes")
    document_type: str = Field(default="other", description="Document type: contract, nda, employment, etc.")
    status: str = Field(default=DocumentStatus.UPLOADED, description="Processing status")
    risk_score: Optional[int] = Field(None, ge=0, le=10, description="Overall risk score (0-10)")
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    language: Optional[str] = Field(default="en", description="Document language code")
    notes: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "507f1f77bcf86cd799439011",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "employment_contract.pdf",
                "file_url": "https://s3.../documents/...",
                "file_type": "pdf",
                "file_size": 245678,
                "document_type": "employment",
                "status": "completed",
                "risk_score": 7,
                "upload_date": "2025-01-15T12:00:00Z",
            }
        }
    
    @classmethod
    async def get_by_id(cls, db: AsyncIOMotorDatabase, document_id: str, user_id: Optional[str] = None) -> Optional["Document"]:
        """Get document by ID (optionally filter by user)."""
        collection = db.documents
        query = {"document_id": document_id}
        if user_id:
            query["user_id"] = user_id
        
        doc = await collection.find_one(query)
        if doc:
            doc.pop("_id", None)
            return cls(**doc)
        return None
    
    @classmethod
    async def create(cls, db: AsyncIOMotorDatabase, document_data: dict) -> "Document":
        """Create new document."""
        collection = db.documents
        document = cls(**document_data)
        await collection.insert_one(document.model_dump())
        return document
    
    async def save(self, db: AsyncIOMotorDatabase) -> "Document":
        """Save document to database."""
        collection = db.documents
        self.updated_at = datetime.utcnow()
        await collection.update_one(
            {"document_id": self.document_id},
            {"$set": self.model_dump()},
            upsert=True,
        )
        return self
    
    async def update_status(self, db: AsyncIOMotorDatabase, status: str, error_message: Optional[str] = None) -> "Document":
        """Update document status."""
        self.status = status
        self.error_message = error_message
        if status == DocumentStatus.PROCESSING and not self.processing_started_at:
            self.processing_started_at = datetime.utcnow()
        elif status in [DocumentStatus.COMPLETED, DocumentStatus.FAILED]:
            self.processing_completed_at = datetime.utcnow()
        await self.save(db)
        return self
    
    @classmethod
    async def list_by_user(
        cls,
        db: AsyncIOMotorDatabase,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        document_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list["Document"]:
        """List documents for a user with filters."""
        collection = db.documents
        query = {"user_id": user_id}
        
        if document_type:
            query["document_type"] = document_type
        if status:
            query["status"] = status
        
        cursor = collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        documents = []
        async for doc in cursor:
            doc.pop("_id", None)
            documents.append(cls(**doc))
        
        return documents
    
    @classmethod
    async def count_by_user(
        cls,
        db: AsyncIOMotorDatabase,
        user_id: str,
        document_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        """Count documents for a user."""
        collection = db.documents
        query = {"user_id": user_id}
        
        if document_type:
            query["document_type"] = document_type
        if status:
            query["status"] = status
        
        return await collection.count_documents(query)
    
    async def delete(self, db: AsyncIOMotorDatabase) -> bool:
        """Delete document from database."""
        collection = db.documents
        result = await collection.delete_one({"document_id": self.document_id})
        return result.deleted_count > 0


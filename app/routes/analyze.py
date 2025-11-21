"""
AI analysis endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.dependencies import get_current_user_id, get_mongodb_db
from app.models.document import Document, DocumentStatus
from app.models.analysis import Analysis
from app.queues.tasks import process_document_analysis
from app.utils.errors import NotFoundError, ValidationError
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


class AnalyzeRequest(BaseModel):
    """Request model for analysis trigger."""
    document_type: str = "other"
    language: str = "en"
    priority: bool = False


@router.post("/{document_id}/analyze")
async def trigger_analysis(
    document_id: str,
    request: AnalyzeRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_mongodb_db),
):
    """
    Trigger AI analysis for a document.
    
    Returns:
        Analysis job information
    """
    document = await Document.get_by_id(db, document_id, user_id)
    if not document:
        raise NotFoundError("Document", document_id)
    
    if document.status == DocumentStatus.PROCESSING:
        raise ValidationError("Document is already being processed")
    
    if document.status == DocumentStatus.COMPLETED:
        # Check if analysis already exists
        existing_analysis = await Analysis.get_by_document_id(db, document_id, user_id)
        if existing_analysis:
            return {
                "analysis_id": existing_analysis.analysis_id,
                "status": "completed",
                "message": "Analysis already completed",
            }
    
    # Update document status
    await document.update_status(db, DocumentStatus.WAITING_IN_QUEUE)
    
    # Queue analysis task
    try:
        task = process_document_analysis.delay(document_id, user_id)
        logger.info(f"Queued analysis task {task.id} for document {document_id}")
        
        return {
            "analysis_id": task.id,
            "document_id": document_id,
            "status": "queued",
            "estimated_time": "2-5 minutes",
        }
    except Exception as e:
        logger.error(f"Error queueing analysis: {e}")
        await document.update_status(db, DocumentStatus.FAILED, str(e))
        raise ValidationError(f"Failed to queue analysis: {str(e)}")


@router.get("/{document_id}/analysis")
async def get_analysis(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_mongodb_db),
):
    """
    Get analysis results for a document.
    
    Returns:
        Complete analysis data
    """
    # Verify document exists and belongs to user
    document = await Document.get_by_id(db, document_id, user_id)
    if not document:
        raise NotFoundError("Document", document_id)
    
    # Get analysis
    analysis = await Analysis.get_by_document_id(db, document_id, user_id)
    if not analysis:
        raise NotFoundError("Analysis", document_id)
    
    # Convert to response format
    return {
        "document_id": analysis.document_id,
        "summary": analysis.summary,
        "parties": [p.model_dump() for p in analysis.parties],
        "dates": [d.model_dump() for d in analysis.dates],
        "financial_terms": [ft.model_dump() for ft in analysis.financial_terms],
        "obligations": [o.model_dump() for o in analysis.obligations],
        "risks": [r.model_dump() for r in analysis.risks],
        "missing_clauses": analysis.missing_clauses,
        "unusual_terms": analysis.unusual_terms,
        "timeline": analysis.timeline,
        "ai_model_used": analysis.ai_model_used,
        "tokens_used": analysis.tokens_used,
        "processing_time": analysis.processing_time,
        "cost_estimate": analysis.cost_estimate,
        "created_at": analysis.created_at.isoformat(),
    }


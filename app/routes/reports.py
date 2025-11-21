"""
Report generation endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
import json

from app.dependencies import get_current_user_id, get_mongodb_db
from app.models.document import Document
from app.models.analysis import Analysis
from app.services.report_builder import ReportBuilder
from app.utils.errors import NotFoundError

router = APIRouter()


@router.get("/{document_id}/report/pdf")
async def download_pdf_report(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_mongodb_db),
):
    """
    Download PDF report for a document.
    
    Returns:
        PDF file
    """
    document = await Document.get_by_id(db, document_id, user_id)
    if not document:
        raise NotFoundError("Document", document_id)
    
    analysis = await Analysis.get_by_document_id(db, document_id, user_id)
    if not analysis:
        raise NotFoundError("Analysis", document_id)
    
    # Generate PDF
    report_builder = ReportBuilder()
    pdf_path = await report_builder.generate_pdf(document, analysis)
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"{document.name}_report.pdf",
    )


@router.get("/{document_id}/report/json")
async def download_json_report(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_mongodb_db),
):
    """
    Download JSON report for a document.
    
    Returns:
        JSON file
    """
    document = await Document.get_by_id(db, document_id, user_id)
    if not document:
        raise NotFoundError("Document", document_id)
    
    analysis = await Analysis.get_by_document_id(db, document_id, user_id)
    if not analysis:
        raise NotFoundError("Analysis", document_id)
    
    # Generate JSON
    report_data = {
        "document": document.model_dump(),
        "analysis": analysis.model_dump(),
    }
    
    return JSONResponse(
        content=report_data,
        headers={"Content-Disposition": f'attachment; filename="{document.name}_report.json"'},
    )


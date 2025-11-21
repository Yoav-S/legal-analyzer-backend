"""
Celery tasks for async document processing.
"""
import time
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from app.queues.worker import celery_app
from app.config import settings
from app.models.document import Document, DocumentStatus
from app.models.analysis import Analysis, Party, DateItem, FinancialTerm, Obligation, RiskItem
from app.services.storage import StorageService
from app.services.pdf_parser import PDFParser
from app.services.docx_parser import DOCXParser
from app.services.ocr import OCRService
from app.services.chunker import DocumentChunker
from app.services.ai_engine import AIEngine
from app.services.risk_engine import RiskEngine
from app.services.emailer import EmailService
from app.models.user import User
from app.models.billing import Subscription
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def process_document_analysis(self, document_id: str, user_id: str):
    """
    Main task for processing document analysis.
    
    This task:
    1. Downloads document from storage
    2. Extracts text (PDF/DOCX/OCR)
    3. Chunks document
    4. Sends chunks to AI
    5. Combines results
    6. Calculates risk scores
    7. Saves analysis to database
    """
    import asyncio
    
    # Run async function
    return asyncio.run(_process_document_analysis_async(document_id, user_id, self))


async def _process_document_analysis_async(document_id: str, user_id: str, task_instance):
    """Async implementation of document processing."""
    start_time = time.time()
    
    # Get MongoDB connection
    client = AsyncIOMotorClient(settings.mongodb_connection_string)
    db = client[settings.MONGODB_DB_NAME]
    
    try:
        # Get document
        document = await Document.get_by_id(db, document_id, user_id)
        if not document:
            logger.error(f"Document not found: {document_id}")
            return
        
        # Update status to processing
        await document.update_status(db, DocumentStatus.PROCESSING)
        
        # Download file from storage
        storage = StorageService()
        file_key = storage.extract_file_key_from_url(document.file_url)
        file_content = await storage.download_file(file_key)
        
        # Extract text based on file type
        logger.info(f"Extracting text from {document.file_type} file")
        if document.file_type == "pdf":
            # Check if scanned
            pdf_parser = PDFParser()
            is_scanned = await pdf_parser.is_scanned(file_content)
            
            if is_scanned:
                logger.info("PDF appears to be scanned, using OCR")
                ocr = OCRService()
                if ocr.is_available():
                    text = await ocr.extract_text_from_pdf(file_content)
                else:
                    logger.warning("OCR not available, using regular PDF extraction")
                    text = await pdf_parser.extract_text(file_content)
            else:
                text = await pdf_parser.extract_text(file_content)
        elif document.file_type == "docx":
            docx_parser = DOCXParser()
            text = await docx_parser.extract_text(file_content)
        elif document.file_type == "txt":
            text = file_content.decode("utf-8")
        else:
            raise ValueError(f"Unsupported file type: {document.file_type}")
        
        if not text or len(text.strip()) < 100:
            raise ValueError("Extracted text is too short or empty")
        
        logger.info(f"Extracted {len(text)} characters of text")
        
        # Chunk document
        chunker = DocumentChunker()
        chunks = chunker.chunk_text(text)
        
        if not chunks:
            raise ValueError("Failed to chunk document")
        
        logger.info(f"Split into {len(chunks)} chunks")
        
        # Analyze each chunk with AI
        ai_engine = AIEngine()
        chunk_analyses = []
        total_tokens = 0
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Analyzing chunk {i + 1}/{len(chunks)}")
            try:
                result = await ai_engine.analyze_document_chunk(
                    chunk_text=chunk["text"],
                    document_type=document.document_type,
                    chunk_index=i,
                    total_chunks=len(chunks),
                )
                chunk_analyses.append(result)
                total_tokens += result.get("tokens_used", 0)
            except Exception as e:
                logger.error(f"Error analyzing chunk {i}: {e}")
                # Continue with other chunks
                continue
        
        if not chunk_analyses:
            raise ValueError("No chunks were successfully analyzed")
        
        # Generate summary
        logger.info("Generating executive summary")
        summary = await ai_engine.generate_summary(chunk_analyses, document.document_type)
        
        # Combine analyses
        combined_data = ai_engine._combine_chunk_analyses(chunk_analyses)
        
        # Calculate risk score
        risk_engine = RiskEngine()
        risks = [RiskItem(**r) for r in combined_data.get("risks", [])]
        risk_score = risk_engine.calculate_overall_risk_score(risks)
        
        # Identify missing clauses
        missing_clauses = risk_engine.identify_missing_clauses(
            document.document_type,
            [],  # Would need to extract clause names from analysis
        )
        
        # Build analysis model
        processing_time = int(time.time() - start_time)
        
        # Estimate cost (rough calculation)
        cost_estimate = 0.0
        if ai_engine.default_model.startswith("gpt-4"):
            cost_estimate = (total_tokens / 1000) * 0.03  # Rough estimate
        elif ai_engine.default_model.startswith("claude-3"):
            cost_estimate = (total_tokens / 1000) * 0.015  # Rough estimate
        
        analysis = await Analysis.create(
            db,
            {
                "document_id": document_id,
                "user_id": user_id,
                "summary": summary,
                "parties": [Party(**p) for p in combined_data.get("parties", [])],
                "dates": [DateItem(**d) for d in combined_data.get("dates", [])],
                "financial_terms": [FinancialTerm(**ft) for ft in combined_data.get("financial_terms", [])],
                "obligations": [Obligation(**o) for o in combined_data.get("obligations", [])],
                "risks": risks,
                "missing_clauses": missing_clauses,
                "unusual_terms": combined_data.get("unusual_terms", []),
                "timeline": combined_data.get("timeline", []),
                "ai_model_used": ai_engine.default_model,
                "tokens_used": total_tokens,
                "processing_time": processing_time,
                "cost_estimate": cost_estimate,
            },
        )
        
        # Update document with risk score and status
        document.risk_score = risk_score
        await document.update_status(db, DocumentStatus.COMPLETED)
        
        # Send email notification
        try:
            user = await User.get_by_id(db, user_id)
            if user and user.email:
                email_service = EmailService()
                await email_service.send_analysis_complete_notification(
                    user_email=user.email,
                    user_name=user.full_name or "User",
                    document_name=document.name,
                    document_id=document_id,
                    risk_score=risk_score,
                )
                
                # Send high-risk alert if applicable
                if risk_score >= 7:
                    await email_service.send_high_risk_alert(
                        user_email=user.email,
                        user_name=user.full_name or "User",
                        document_name=document.name,
                        document_id=document_id,
                        risk_score=risk_score,
                    )
        except Exception as email_error:
            logger.warning(f"Failed to send email notification: {email_error}")
        
        logger.info(f"Analysis completed for document {document_id} in {processing_time}s")
        
        return {
            "analysis_id": analysis.analysis_id,
            "document_id": document_id,
            "risk_score": risk_score,
            "processing_time": processing_time,
        }
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}", exc_info=True)
        
        # Update document status to failed
        try:
            document = await Document.get_by_id(db, document_id, user_id)
            if document:
                await document.update_status(db, DocumentStatus.FAILED, str(e))
        except:
            pass
        
        # Retry if not max retries
        if task_instance.request.retries < task_instance.max_retries:
            raise task_instance.retry(exc=e, countdown=60 * (task_instance.request.retries + 1))
        else:
            raise
    
    finally:
        client.close()


@celery_app.task
def handle_stripe_webhook(event_type: str, event_data: dict):
    """Handle Stripe webhook events (sync wrapper)."""
    import asyncio
    return asyncio.run(_handle_stripe_webhook_async(event_type, event_data))


async def _handle_stripe_webhook_async(event_type: str, event_data: dict):
    """
    Handle Stripe webhook events.
    
    Event types:
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_succeeded
    - invoice.payment_failed
    """
    client = AsyncIOMotorClient(settings.mongodb_connection_string)
    db = client[settings.MONGODB_DB_NAME]
    
    try:
        if event_type == "customer.subscription.created":
            subscription_id = event_data.get("id")
            customer_id = event_data.get("customer")
            status = event_data.get("status")
            
            # Find subscription by Stripe ID
            subscription = await Subscription.get_by_stripe_subscription_id(db, subscription_id)
            if subscription:
                subscription.status = status
                await subscription.save(db)
        
        elif event_type == "customer.subscription.updated":
            subscription_id = event_data.get("id")
            status = event_data.get("status")
            cancel_at_period_end = event_data.get("cancel_at_period_end", False)
            
            subscription = await Subscription.get_by_stripe_subscription_id(db, subscription_id)
            if subscription:
                subscription.status = status
                subscription.cancel_at_period_end = cancel_at_period_end
                await subscription.save(db)
        
        elif event_type == "invoice.payment_succeeded":
            # Reset user credits on successful payment
            subscription_id = event_data.get("subscription")
            if subscription_id:
                subscription = await Subscription.get_by_stripe_subscription_id(db, subscription_id)
                if subscription:
                    user = await User.get_by_id(db, subscription.user_id)
                    if user:
                        from app.services.stripe import StripeService
                        stripe_service = StripeService()
                        monthly_limit = stripe_service.get_plan_limits(subscription.plan)
                        if monthly_limit > 0:
                            user.credits_remaining = monthly_limit
                            await user.save(db)
        
        logger.info(f"Processed Stripe webhook: {event_type}")
        
    except Exception as e:
        logger.error(f"Error handling Stripe webhook: {e}", exc_info=True)
    finally:
        client.close()


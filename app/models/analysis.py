"""
Analysis MongoDB model for AI analysis results.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from bson import ObjectId


class Party(BaseModel):
    """Party involved in document."""
    name: str
    role: str
    contact: Optional[str] = None


class DateItem(BaseModel):
    """Important date in document."""
    type: str  # e.g., "Start Date", "Deadline", "Termination Date"
    date: str  # ISO format date string
    description: Optional[str] = None


class FinancialTerm(BaseModel):
    """Financial term extracted from document."""
    type: str  # e.g., "Salary", "Payment", "Penalty"
    amount: float
    currency: str = "USD"
    frequency: Optional[str] = None  # e.g., "annual", "monthly"


class Obligation(BaseModel):
    """Obligation of a party."""
    party: str
    obligation: str
    deadline: Optional[str] = None


class RiskItem(BaseModel):
    """Risk identified in document."""
    severity: str  # "high", "medium", "low"
    title: str
    description: str
    recommendation: Optional[str] = None
    page_reference: Optional[int] = None
    clause_name: Optional[str] = None


class Analysis(BaseModel):
    """AI analysis result model."""
    
    analysis_id: str = Field(default_factory=lambda: str(ObjectId()), description="Unique analysis ID")
    document_id: str = Field(..., description="Associated document ID")
    user_id: str = Field(..., description="Owner user ID")
    
    # Summary
    summary: str = Field(..., description="Executive summary (2-3 paragraphs)")
    
    # Extracted data
    parties: List[Party] = Field(default_factory=list)
    dates: List[DateItem] = Field(default_factory=list)
    financial_terms: List[FinancialTerm] = Field(default_factory=list)
    obligations: List[Obligation] = Field(default_factory=list)
    
    # Risk analysis
    risks: List[RiskItem] = Field(default_factory=list)
    missing_clauses: List[str] = Field(default_factory=list)
    unusual_terms: List[str] = Field(default_factory=list)
    
    # Timeline
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Metadata
    ai_model_used: str = Field(..., description="AI model used: gpt-4, claude-3, etc.")
    tokens_used: int = Field(default=0, description="Total tokens consumed")
    processing_time: int = Field(default=0, description="Processing time in seconds")
    cost_estimate: float = Field(default=0.0, description="Estimated cost in USD")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "analysis_id": "507f1f77bcf86cd799439011",
                "document_id": "507f1f77bcf86cd799439012",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "summary": "This employment agreement...",
                "parties": [{"name": "Company A", "role": "Employer"}],
                "risks": [{"severity": "high", "title": "Missing indemnification"}],
                "ai_model_used": "gpt-4-turbo-preview",
                "tokens_used": 15000,
            }
        }
    
    @classmethod
    async def get_by_document_id(cls, db: AsyncIOMotorDatabase, document_id: str, user_id: Optional[str] = None) -> Optional["Analysis"]:
        """Get analysis by document ID."""
        collection = db.analyses
        query = {"document_id": document_id}
        if user_id:
            query["user_id"] = user_id
        
        doc = await collection.find_one(query)
        if doc:
            doc.pop("_id", None)
            return cls(**doc)
        return None
    
    @classmethod
    async def create(cls, db: AsyncIOMotorDatabase, analysis_data: dict) -> "Analysis":
        """Create new analysis."""
        collection = db.analyses
        analysis = cls(**analysis_data)
        await collection.insert_one(analysis.model_dump())
        return analysis
    
    async def save(self, db: AsyncIOMotorDatabase) -> "Analysis":
        """Save analysis to database."""
        collection = db.analyses
        await collection.update_one(
            {"analysis_id": self.analysis_id},
            {"$set": self.model_dump()},
            upsert=True,
        )
        return self
    
    def get_risk_summary(self) -> Dict[str, int]:
        """Get risk count by severity."""
        summary = {"high": 0, "medium": 0, "low": 0}
        for risk in self.risks:
            severity = risk.severity.lower()
            if severity in summary:
                summary[severity] += 1
        return summary


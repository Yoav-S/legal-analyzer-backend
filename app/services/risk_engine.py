"""
Risk scoring engine for legal documents.
"""
from typing import List, Dict, Any
from app.models.analysis import RiskItem

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class RiskEngine:
    """Service for calculating risk scores and identifying risks."""
    
    # Risk weights for different severity levels
    RISK_WEIGHTS = {
        "high": 3,
        "medium": 2,
        "low": 1,
    }
    
    # Standard clauses that should be present in different document types
    STANDARD_CLAUSES = {
        "contract": [
            "Termination clause",
            "Liability limitation",
            "Indemnification clause",
            "Dispute resolution",
            "Force majeure",
        ],
        "employment": [
            "Non-compete clause",
            "Confidentiality clause",
            "Termination terms",
            "Severance terms",
            "Intellectual property assignment",
        ],
        "nda": [
            "Definition of confidential information",
            "Exclusions",
            "Term",
            "Return of materials",
        ],
        "lease": [
            "Security deposit terms",
            "Maintenance responsibilities",
            "Termination conditions",
            "Renewal options",
        ],
    }
    
    def calculate_overall_risk_score(self, risks: List[RiskItem]) -> int:
        """
        Calculate overall risk score (0-10) from risk items.
        
        Args:
            risks: List of risk items
            
        Returns:
            Risk score from 0-10
        """
        if not risks:
            return 0
        
        total_weight = 0
        for risk in risks:
            severity = risk.severity.lower()
            weight = self.RISK_WEIGHTS.get(severity, 1)
            total_weight += weight
        
        # Normalize to 0-10 scale
        # Max possible: all high risks (3 each)
        # Formula: (total_weight / (num_risks * 3)) * 10, capped at 10
        if total_weight == 0:
            return 0
        
        max_possible = len(risks) * 3
        score = min(10, int((total_weight / max_possible) * 10))
        
        return score
    
    def identify_missing_clauses(
        self,
        document_type: str,
        extracted_clauses: List[str],
    ) -> List[str]:
        """
        Identify missing standard clauses for document type.
        
        Args:
            document_type: Type of document (contract, employment, etc.)
            extracted_clauses: List of clause names found in document
            
        Returns:
            List of missing standard clauses
        """
        standard_clauses = self.STANDARD_CLAUSES.get(document_type.lower(), [])
        
        # Normalize for comparison (lowercase, remove special chars)
        extracted_normalized = [
            self._normalize_clause_name(clause) for clause in extracted_clauses
        ]
        
        missing = []
        for standard_clause in standard_clauses:
            normalized = self._normalize_clause_name(standard_clause)
            if normalized not in extracted_normalized:
                missing.append(standard_clause)
        
        return missing
    
    def _normalize_clause_name(self, clause_name: str) -> str:
        """Normalize clause name for comparison."""
        return clause_name.lower().replace(" ", "").replace("-", "").replace("_", "")
    
    def prioritize_risks(self, risks: List[RiskItem]) -> List[RiskItem]:
        """
        Sort risks by priority (high first, then medium, then low).
        
        Args:
            risks: List of risk items
            
        Returns:
            Sorted list of risks
        """
        priority_order = {"high": 0, "medium": 1, "low": 2}
        
        return sorted(
            risks,
            key=lambda r: priority_order.get(r.severity.lower(), 3),
        )
    
    def get_risk_summary(self, risks: List[RiskItem]) -> Dict[str, int]:
        """
        Get risk count by severity.
        
        Args:
            risks: List of risk items
            
        Returns:
            Dictionary with counts by severity
        """
        summary = {"high": 0, "medium": 0, "low": 0}
        
        for risk in risks:
            severity = risk.severity.lower()
            if severity in summary:
                summary[severity] += 1
        
        return summary


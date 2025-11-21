"""
Report generation service (PDF and JSON).
"""
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors

from app.models.document import Document
from app.models.analysis import Analysis
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ReportBuilder:
    """Service for generating PDF and JSON reports."""
    
    def __init__(self):
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
    
    async def generate_pdf(self, document: Document, analysis: Analysis) -> str:
        """
        Generate PDF report.
        
        Args:
            document: Document model
            analysis: Analysis model
            
        Returns:
            Path to generated PDF file
        """
        pdf_path = self.reports_dir / f"{document.document_id}_report.pdf"
        
        # Create PDF document
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )
        
        # Build story (content)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#1E3A8A"),
            spaceAfter=30,
        )
        story.append(Paragraph("Legal Document Analysis Report", title_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Document Info
        story.append(Paragraph("<b>Document Information</b>", styles["Heading2"]))
        doc_info = [
            ["Document Name:", document.name],
            ["Document Type:", document.document_type],
            ["Upload Date:", document.upload_date.strftime("%Y-%m-%d %H:%M:%S")],
            ["Status:", document.status],
        ]
        if document.risk_score is not None:
            doc_info.append(["Risk Score:", f"{document.risk_score}/10"])
        
        doc_table = Table(doc_info, colWidths=[2 * inch, 4 * inch])
        doc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (1, 0), (1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(doc_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Executive Summary
        story.append(Paragraph("<b>Executive Summary</b>", styles["Heading2"]))
        story.append(Paragraph(analysis.summary, styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))
        
        # Risk Analysis
        story.append(Paragraph("<b>Risk Analysis</b>", styles["Heading2"]))
        risk_summary = analysis.get_risk_summary()
        story.append(Paragraph(
            f"High: {risk_summary['high']} | Medium: {risk_summary['medium']} | Low: {risk_summary['low']}",
            styles["Normal"]
        ))
        story.append(Spacer(1, 0.2 * inch))
        
        # Risk Items
        for risk in analysis.risks[:10]:  # Limit to top 10
            severity_color = {
                "high": colors.red,
                "medium": colors.orange,
                "low": colors.yellow,
            }.get(risk.severity.lower(), colors.black)
            
            risk_text = f"<b>[{risk.severity.upper()}]</b> {risk.title}"
            story.append(Paragraph(risk_text, styles["Normal"]))
            story.append(Paragraph(risk.description, styles["Normal"]))
            if risk.recommendation:
                story.append(Paragraph(f"<i>Recommendation: {risk.recommendation}</i>", styles["Normal"]))
            story.append(Spacer(1, 0.1 * inch))
        
        story.append(PageBreak())
        
        # Key Terms
        story.append(Paragraph("<b>Key Terms</b>", styles["Heading2"]))
        
        # Parties
        if analysis.parties:
            story.append(Paragraph("<b>Parties Involved</b>", styles["Heading3"]))
            for party in analysis.parties:
                story.append(Paragraph(f"• {party.name} ({party.role})", styles["Normal"]))
            story.append(Spacer(1, 0.2 * inch))
        
        # Dates
        if analysis.dates:
            story.append(Paragraph("<b>Important Dates</b>", styles["Heading3"]))
            for date_item in analysis.dates[:10]:  # Top 10
                story.append(Paragraph(
                    f"• {date_item.type}: {date_item.date}",
                    styles["Normal"]
                ))
            story.append(Spacer(1, 0.2 * inch))
        
        # Financial Terms
        if analysis.financial_terms:
            story.append(Paragraph("<b>Financial Terms</b>", styles["Heading3"]))
            for term in analysis.financial_terms[:10]:  # Top 10
                story.append(Paragraph(
                    f"• {term.type}: {term.currency} {term.amount:,.2f}",
                    styles["Normal"]
                ))
            story.append(Spacer(1, 0.2 * inch))
        
        # Missing Clauses
        if analysis.missing_clauses:
            story.append(Paragraph("<b>Missing Standard Clauses</b>", styles["Heading3"]))
            for clause in analysis.missing_clauses:
                story.append(Paragraph(f"• {clause}", styles["Normal"]))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"Generated PDF report: {pdf_path}")
        return str(pdf_path)


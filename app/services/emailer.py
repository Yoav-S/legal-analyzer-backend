"""
Email service using SendGrid.
"""
from typing import Optional, List
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class EmailService:
    """Service for sending transactional emails."""
    
    def __init__(self):
        if settings.SENDGRID_API_KEY:
            self.client = SendGridAPIClient(settings.SENDGRID_API_KEY)
        else:
            self.client = None
            logger.warning("SendGrid API key not configured. Emails will be logged only.")
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """
        Send email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text content (optional)
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.client:
            logger.info(f"Email would be sent to {to_email}: {subject}")
            return False
        
        try:
            message = Mail(
                from_email=Email(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content),
            )
            
            if text_content:
                message.add_content(Content("text/plain", text_content))
            
            response = self.client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent to {to_email}: {subject}")
                return True
            else:
                logger.error(f"Failed to send email: {response.status_code} - {response.body}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    async def send_analysis_complete_notification(
        self,
        user_email: str,
        user_name: str,
        document_name: str,
        document_id: str,
        risk_score: Optional[int] = None,
    ) -> bool:
        """Send notification when document analysis is complete."""
        subject = f"Analysis Complete: {document_name}"
        
        risk_text = f"Risk Score: {risk_score}/10" if risk_score is not None else "Analysis complete"
        
        html_content = f"""
        <html>
        <body>
            <h2>Document Analysis Complete</h2>
            <p>Hello {user_name},</p>
            <p>Your document <strong>{document_name}</strong> has been analyzed.</p>
            <p>{risk_text}</p>
            <p><a href="{settings.API_BASE_URL}/reports/{document_id}">View Report</a></p>
            <p>Best regards,<br>CreativeDoc Team</p>
        </body>
        </html>
        """
        
        return await self.send_email(user_email, subject, html_content)
    
    async def send_high_risk_alert(
        self,
        user_email: str,
        user_name: str,
        document_name: str,
        document_id: str,
        risk_score: int,
    ) -> bool:
        """Send alert for high-risk documents."""
        subject = f"⚠️ High Risk Alert: {document_name}"
        
        html_content = f"""
        <html>
        <body>
            <h2>High Risk Document Detected</h2>
            <p>Hello {user_name},</p>
            <p>Your document <strong>{document_name}</strong> has been flagged with a high risk score: <strong>{risk_score}/10</strong>.</p>
            <p>Please review the analysis report carefully.</p>
            <p><a href="{settings.API_BASE_URL}/reports/{document_id}">View Report</a></p>
            <p>Best regards,<br>CreativeDoc Team</p>
        </body>
        </html>
        """
        
        return await self.send_email(user_email, subject, html_content)


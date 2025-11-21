"""
PDF text extraction service.
"""
from typing import Optional
import pdfplumber
from PyPDF2 import PdfReader
import io

from app.utils.logger import setup_logger
from app.utils.errors import ProcessingError

logger = setup_logger(__name__)


class PDFParser:
    """Service for extracting text from PDF files."""
    
    @staticmethod
    async def extract_text(pdf_content: bytes) -> str:
        """
        Extract text from PDF content.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Extracted text
        """
        try:
            # Try pdfplumber first (better for complex PDFs)
            text = await PDFParser._extract_with_pdfplumber(pdf_content)
            if text and len(text.strip()) > 100:
                return text
            
            # Fallback to PyPDF2
            logger.info("Falling back to PyPDF2 for PDF extraction")
            text = await PDFParser._extract_with_pypdf2(pdf_content)
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise ProcessingError(f"Failed to extract text from PDF: {str(e)}")
    
    @staticmethod
    async def _extract_with_pdfplumber(pdf_content: bytes) -> str:
        """Extract text using pdfplumber."""
        try:
            pdf_file = io.BytesIO(pdf_content)
            text_parts = []
            
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
            return ""
    
    @staticmethod
    async def _extract_with_pypdf2(pdf_content: bytes) -> str:
        """Extract text using PyPDF2."""
        try:
            pdf_file = io.BytesIO(pdf_content)
            reader = PdfReader(pdf_file)
            text_parts = []
            
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
            raise ProcessingError(f"Failed to extract text: {str(e)}")
    
    @staticmethod
    async def get_page_count(pdf_content: bytes) -> int:
        """Get number of pages in PDF."""
        try:
            pdf_file = io.BytesIO(pdf_content)
            reader = PdfReader(pdf_file)
            return len(reader.pages)
        except Exception as e:
            logger.error(f"Error getting page count: {e}")
            return 0
    
    @staticmethod
    async def is_scanned(pdf_content: bytes) -> bool:
        """
        Check if PDF is scanned (image-based).
        
        Args:
            pdf_content: PDF file content
            
        Returns:
            True if likely scanned, False otherwise
        """
        try:
            # Extract text from first page
            pdf_file = io.BytesIO(pdf_content)
            reader = PdfReader(pdf_file)
            
            if len(reader.pages) == 0:
                return True
            
            first_page_text = reader.pages[0].extract_text()
            
            # If very little text, likely scanned
            if not first_page_text or len(first_page_text.strip()) < 50:
                return True
            
            return False
        except Exception:
            return True  # Assume scanned if we can't determine


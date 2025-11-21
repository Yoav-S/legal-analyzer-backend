"""
OCR service for scanned documents using Tesseract.
"""
from typing import Optional
import io
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes

from app.config import settings
from app.utils.logger import setup_logger
from app.utils.errors import ProcessingError

logger = setup_logger(__name__)


class OCRService:
    """Service for OCR text extraction from scanned PDFs."""
    
    def __init__(self):
        if settings.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    
    async def extract_text_from_pdf(self, pdf_content: bytes, dpi: int = 300) -> str:
        """
        Extract text from scanned PDF using OCR.
        
        Args:
            pdf_content: PDF file content as bytes
            dpi: DPI for image conversion (higher = better quality, slower)
            
        Returns:
            Extracted text
        """
        try:
            # Convert PDF pages to images
            images = convert_from_bytes(pdf_content, dpi=dpi)
            
            text_parts = []
            
            for i, image in enumerate(images):
                logger.info(f"Processing page {i + 1}/{len(images)} with OCR")
                page_text = pytesseract.image_to_string(image, lang="eng")
                if page_text.strip():
                    text_parts.append(page_text)
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"Error in OCR extraction: {e}")
            raise ProcessingError(f"OCR extraction failed: {str(e)}")
    
    async def extract_text_from_image(self, image_content: bytes) -> str:
        """
        Extract text from image using OCR.
        
        Args:
            image_content: Image file content as bytes
            
        Returns:
            Extracted text
        """
        try:
            image = Image.open(io.BytesIO(image_content))
            text = pytesseract.image_to_string(image, lang="eng")
            return text
        except Exception as e:
            logger.error(f"Error in OCR image extraction: {e}")
            raise ProcessingError(f"OCR image extraction failed: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if Tesseract OCR is available."""
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False


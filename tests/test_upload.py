"""
Tests for document upload functionality.
"""
import pytest
from app.models.document import Document
from app.models.user import User

@pytest.mark.asyncio
async def test_document_creation(db, test_user_data):
    """Test creating a document."""
    # Create test user
    user = await User.create(db, test_user_data)
    
    # Create document
    document_data = {
        "user_id": user.user_id,
        "name": "test.pdf",
        "file_url": "https://s3.../test.pdf",
        "file_type": "pdf",
        "file_size": 1024,
        "document_type": "contract",
    }
    
    document = await Document.create(db, document_data)
    
    assert document.document_id is not None
    assert document.name == "test.pdf"
    assert document.user_id == user.user_id


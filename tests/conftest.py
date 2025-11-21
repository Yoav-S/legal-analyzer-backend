"""
Pytest configuration and fixtures.
"""
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

@pytest.fixture
async def db():
    """Get test database connection."""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME + "_test"]
    yield db
    # Cleanup
    await client.drop_database(settings.MONGODB_DB_NAME + "_test")
    client.close()

@pytest.fixture
def test_user_data():
    """Sample user data for testing."""
    return {
        "user_id": "test-user-123",
        "email": "test@example.com",
        "full_name": "Test User",
        "plan": "starter",
        "credits_remaining": 20,
    }


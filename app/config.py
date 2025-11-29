"""
Application configuration using Pydantic Settings.
All environment variables are loaded here.
"""
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_BASE_URL: str = "http://localhost:8000"
    
    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "creativedoc"
    MONGODB_ATLAS_URL: Optional[str] = None
    
    # Supabase Auth
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str
    
    # File Storage
    STORAGE_TYPE: str = "s3"  # s3 or r2
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "creativedoc-documents"
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: str = "creativedoc-documents"
    R2_ENDPOINT_URL: Optional[str] = None
    
    # AI APIs
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: Optional[str] = None
    DEFAULT_AI_MODEL: str = "gpt-5.1"  # Updated to GPT-5.1 (better performance, lower cost than GPT-4)
    AI_FALLBACK_MODEL: str = "claude-3-sonnet-20240229"
    MAX_TOKENS_PER_CHUNK: int = 8000
    AI_TEMPERATURE: float = 0.3
    
    # Queue & Workers
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Stripe
    STRIPE_SECRET_KEY: str
    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    STRIPE_PRICE_ID_STARTER: str
    STRIPE_PRICE_ID_PROFESSIONAL: str
    STRIPE_PRICE_ID_ENTERPRISE: str
    
    # Email
    SENDGRID_API_KEY: Optional[str] = None
    SENDGRID_FROM_EMAIL: str = "noreply@creativedoc.com"
    SENDGRID_FROM_NAME: str = "CreativeDoc"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # File Upload
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_FILE_TYPES: str = "pdf,docx,txt"
    
    # OCR
    TESSERACT_CMD: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def allowed_file_extensions(self) -> List[str]:
        """Parse allowed file types from comma-separated string."""
        return [ext.strip() for ext in self.ALLOWED_FILE_TYPES.split(",")]
    
    @property
    def max_file_size_bytes(self) -> int:
        """Convert MB to bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    @property
    def mongodb_connection_string(self) -> str:
        """Get MongoDB connection string (prefer Atlas if available)."""
        return self.MONGODB_ATLAS_URL or self.MONGODB_URL


# Global settings instance
settings = Settings()


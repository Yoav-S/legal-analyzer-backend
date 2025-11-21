# Legal Analyzer Backend

FastAPI backend for AI-powered legal document analysis.

## 🏗️ Architecture

- **Framework:** FastAPI 0.109+
- **Database:** MongoDB (Motor async driver)
- **Queue:** Celery + Redis
- **Storage:** AWS S3 / Cloudflare R2
- **Auth:** Supabase JWT
- **AI:** OpenAI GPT-4 + Anthropic Claude
- **Payments:** Stripe
- **Email:** SendGrid

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- MongoDB (local or Atlas)
- Redis (for Celery)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd legal-analyzer-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your actual keys

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, run Celery worker
celery -A app.queues.worker worker --loglevel=info
```

## 📚 API Documentation

Once running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

## 📁 Project Structure

```
app/
├── main.py              # FastAPI app entry point
├── config.py            # Configuration
├── dependencies.py      # Dependency injection
├── routes/              # API endpoints
├── models/              # MongoDB models
├── services/            # Business logic services
├── queues/              # Celery tasks
├── middleware/          # Middleware (rate limiting, etc.)
├── utils/               # Utilities
└── schemas/             # Pydantic schemas
```

## 🔗 Related Repositories

- **Frontend:** [legal-analyzer-frontend](../legal-analyzer-frontend)
- **Infrastructure:** [legal-analyzer-infra](../legal-analyzer-infra)
- **Scripts:** [legal-analyzer-scripts](../legal-analyzer-scripts)
- **Documentation:** [legal-analyzer-docs](../legal-analyzer-docs)

## 📝 Environment Variables

See `.env.example` for all required variables.

Key variables:
- `MONGODB_URL` - MongoDB connection string
- `SUPABASE_URL` & `SUPABASE_ANON_KEY` - Supabase credentials
- `OPENAI_API_KEY` - OpenAI API key
- `STRIPE_SECRET_KEY` - Stripe secret key
- `AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY` - S3 credentials
- `REDIS_URL` - Redis connection for Celery

## 🐳 Docker

For production deployment, see [legal-analyzer-infra](../legal-analyzer-infra).

For local development:
```bash
docker build -t legal-analyzer-backend .
docker run -p 8000:8000 --env-file .env legal-analyzer-backend
```

## 📖 Documentation

Full documentation available in [legal-analyzer-docs](../legal-analyzer-docs):
- API Reference
- Deployment Guide
- Architecture Overview
- Development Setup

## 🤝 Contributing

1. Create feature branch
2. Make changes
3. Write tests
4. Submit pull request

## 📄 License

Proprietary and confidential.


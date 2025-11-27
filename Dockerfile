# Multi-stage Dockerfile for CreativeDoc Backend with Multi-Repo Support
# Stage 1: Builder - Clone repositories and install dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies including git for cloning repos
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# GitHub token for cloning private repositories (passed as build arg)
# This should be set in Railway/Render as GITHUB_TOKEN environment variable
ARG GITHUB_TOKEN
ENV GITHUB_TOKEN=${GITHUB_TOKEN}

# GitHub username/organization (update with your GitHub username)
ARG GITHUB_USER=Yoav-S
ENV GITHUB_USER=${GITHUB_USER}

# Clone private repositories during build
# Repository 1: Backend code (main application)
RUN if [ -z "$GITHUB_TOKEN" ]; then \
        echo "ERROR: GITHUB_TOKEN is required for cloning private repositories" && exit 1; \
    fi && \
    git clone --depth=1 https://${GITHUB_TOKEN}@github.com/${GITHUB_USER}/legal-analyzer-backend.git /tmp/backend || \
    (echo "Failed to clone legal-analyzer-backend. Check GITHUB_TOKEN and repository access." && exit 1)

# Repository 2: Scripts (migrations, utilities - optional, only if needed)
# Uncomment if you need scripts during build/runtime
# RUN git clone --depth=1 https://${GITHUB_TOKEN}@github.com/${GITHUB_USER}/legal-analyzer-scripts.git /tmp/scripts

# Copy backend application code from cloned repository
RUN cp -r /tmp/backend/app ./app && \
    cp -r /tmp/backend/tests ./tests && \
    cp /tmp/backend/requirements.txt ./requirements.txt && \
    # Copy any other necessary files from backend repo
    (cp /tmp/backend/.env.example .env.example 2>/dev/null || true) && \
    (cp /tmp/backend/pytest.ini pytest.ini 2>/dev/null || true)

# Copy scripts if cloned (uncomment if using scripts repo)
# RUN if [ -d "/tmp/scripts" ]; then \
#     mkdir -p ./scripts && \
#     cp -r /tmp/scripts/migrations ./migrations && \
#     cp -r /tmp/scripts/utils ./scripts/utils || true; \
#     fi

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt && \
    pip install --no-cache-dir --user email-validator==2.1.0

# Clean up cloned repositories and git history to reduce image size
RUN rm -rf /tmp/backend /tmp/scripts && \
    apt-get purge -y git && \
    apt-get autoremove -y

# Stage 2: Production - Minimal runtime image
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder stage
COPY --from=builder /root/.local /root/.local

# Copy application code from builder stage
COPY --from=builder /app/app ./app
COPY --from=builder /app/tests ./tests

# Ensure scripts are executable and add to PATH
ENV PATH=/root/.local/bin:$PATH

# Install critical dependencies to ensure they're available
# Must be after PATH is set and packages are copied
RUN pip install --no-cache-dir --user email-validator==2.1.0 tiktoken==0.5.2 && \
    python -c "import email_validator; import tiktoken; print(f'email-validator {email_validator.__version__} installed'); print(f'tiktoken {tiktoken.__version__} installed')" || \
    (echo "ERROR: Failed to install critical dependencies" && exit 1)

# Create necessary directories
RUN mkdir -p logs reports

# Expose port
EXPOSE 8000

# Final verification: Ensure critical dependencies are importable (catches cache issues)
# This will fail the build if dependencies are missing, preventing runtime crashes
RUN python -c "\
import email_validator; \
import tiktoken; \
from pydantic import EmailStr; \
print('✅ EMAIL VALIDATOR OK:', email_validator.__version__); \
print('✅ TIKTOKEN OK:', tiktoken.__version__); \
print('✅ Pydantic EmailStr import test passed'); \
print('✅ All critical dependencies verified')" || \
    (echo "❌ ERROR: Critical dependencies are not importable. This indicates a Docker cache issue." && \
     echo "   Solution: Rebuild with --no-cache flag" && \
     exit 1)

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


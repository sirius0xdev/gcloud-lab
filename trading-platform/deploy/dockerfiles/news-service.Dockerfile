# =============================================================================
# News Service Dockerfile — Multi-stage build with NLTK data
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build
COPY trading-platform/news-service/requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Production stage
FROM python:3.12-slim AS production

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies from builder
COPY --from=builder /install /usr/local

# Download NLTK data for textblob
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('averaged_perceptron_tagger')"

# Security: non-root user
RUN useradd -m --system appuser

# Copy application code
WORKDIR /app
COPY --chown=appuser:appuser trading-platform/news-service/app/ ./app/
COPY --chown=appuser:appuser trading-platform/news-service/requirements.txt ./

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8002/health')" || exit 1

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "4"]

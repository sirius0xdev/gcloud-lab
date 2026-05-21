# =============================================================================
# Data Service Dockerfile — Multi-stage build
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build
COPY trading-platform/data-service/pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

# Production stage
FROM python:3.12-slim AS production

# Security: non-root user
RUN useradd -m --system appuser

# Copy dependencies from builder
COPY --from=builder /install /usr/local

# Copy application code
WORKDIR /app
COPY --chown=appuser:appuser trading-platform/data-service/data_service/ ./data_service/
COPY --chown=appuser:appuser trading-platform/data-service/pyproject.toml ./

USER appuser

# Health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

EXPOSE 8001

CMD ["uvicorn", "data_service.app.main:app", "--host", "0.0.0.0", "--port", "8001"]

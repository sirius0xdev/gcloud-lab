# =============================================================================
# Execute Service Dockerfile — Multi-stage build for minimal image
# =============================================================================
# Build stage: compile dependencies
FROM python:3.12-slim AS builder

WORKDIR /build
COPY trading-platform/execute-service/pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

# Production stage
FROM python:3.12-slim AS production

# Security: non-root user
RUN useradd -m --system appuser

# Copy dependencies from builder
COPY --from=builder /install /usr/local

# Copy application code
WORKDIR /app
COPY --chown=appuser:appuser trading-platform/execute-service/app/ ./app/
COPY --chown=appuser:appuser trading-platform/execute-service/pyproject.toml ./

# Create required directories with proper permissions
RUN mkdir -p /tmp /app/data && chown -R appuser:appuser /tmp /app/data

USER appuser

# Health check using Python (curl not in slim)
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

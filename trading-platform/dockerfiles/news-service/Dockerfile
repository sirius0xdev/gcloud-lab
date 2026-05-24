# Multi-stage build for news-service (CNPG connector + Kafka producer)
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
RUN useradd -m --system appuser

# Copy installed deps from builder
COPY --from=builder /install /usr/local

# Install system deps for NLTK
RUN apt-get update && \\
    apt-get install -y --no-install-recommends gcc libpq-dev && \\
    rm -rf /var/lib/apt/lists/*

# Download NLTK data as root before switching user
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('averaged_perceptron_tagger')"

WORKDIR /app
COPY --chown=appuser:appuser . .
USER appuser

HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8002/health')" || exit 1

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "4"]

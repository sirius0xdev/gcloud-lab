# Multi-stage build for execute-service (Hyperliquid + Solana trading engine)
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim
RUN useradd -m --system appuser

COPY --from=builder /install /usr/local

WORKDIR /app
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser pyproject.toml ./

USER appuser

HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

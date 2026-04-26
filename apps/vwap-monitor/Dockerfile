FROM python:3.13-slim

LABEL maintainer="sirius0xdev" \
      description="VWAP Wave Breach Scanner — monitors Gold, NASDAQ, S&P, Crude Oil"

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/scanner.py .

# Default scan interval: 120s (2 min), threshold: 2σ
ENV SCAN_INTERVAL_SEC=120 \
    BREACH_THRESHOLD=2.0

# Health check: ensure process is alive
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD ["python3", "-c", "import os; assert os.path.exists('/proc/1/fd/0')"]

CMD ["python3", "scanner.py"]

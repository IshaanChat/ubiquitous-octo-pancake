# syntax=docker/dockerfile:1

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (minimal; add if you need build tools)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# App code
COPY src ./src
COPY config ./config

EXPOSE 8000

# Healthcheck using Python stdlib (no curl dependency)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python - <<'PY'
import sys, urllib.request
try:
    with urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3) as r:
        sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
PY

# Default command
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ═══════════════════════════════════════════
# FakeBuster AI — Backend Dockerfile
# Multi-stage build for production readiness
# ═══════════════════════════════════════════

FROM python:3.11-slim AS base

# Prevent Python from writing .pyc and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps for psycopg2 and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc g++ \
    libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Create media storage directory
RUN mkdir -p /app/media

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

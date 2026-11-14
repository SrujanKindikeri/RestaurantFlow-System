# =============================================================================
# RestaurantFlow — Backend Dockerfile (multi-stage)
# Phase 23: Production-ready image
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: builder — compile Python packages
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: runtime — lean production image
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled packages from builder
COPY --from=builder /install /usr/local

# Copy application source
WORKDIR /app
COPY . /app

# Environment for collectstatic (placeholder secret — real value injected at runtime)
ENV DJANGO_SETTINGS_MODULE=config.settings \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBUG=False \
    SECRET_KEY=build-time-placeholder

# Collect static files at build time (whitenoise serves them)
RUN python manage.py collectstatic --noinput

# Create a non-root user and lock down the app directory
RUN useradd --uid 1000 --no-create-home --shell /bin/false appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

CMD ["uvicorn", "config.asgi:application", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker"]

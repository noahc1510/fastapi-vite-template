# ============================================
# Stage 1: Frontend Builder
# ============================================
FROM oven/bun:1.2-alpine AS frontend-builder

WORKDIR /frontend

# Copy frontend package files
COPY frontend/package.json frontend/bun.lock* ./

# Install frontend dependencies
RUN bun install --frozen-lockfile

# Copy frontend source code
COPY frontend/ ./

# Build frontend for production
RUN bun run build


# ============================================
# Stage 2: Python Builder
# ============================================
FROM python:3.13-slim AS python-builder

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy Python dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies into a virtual environment
RUN uv sync --frozen --no-dev


# ============================================
# Stage 3: Runtime
# ============================================
FROM python:3.13-slim AS runtime

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Apply OS security updates
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy uv binary from builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy Python virtual environment from builder
COPY --from=python-builder /app/.venv /app/.venv

# Copy application code
COPY app ./app
COPY main.py ./
COPY pyproject.toml uv.lock ./

# Copy frontend build from frontend-builder
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Start application with gunicorn
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "--bind", "0.0.0.0:8000", "app:api"]

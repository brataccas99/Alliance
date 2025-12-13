# Unified Dockerfile for Alliance PNRR Futura Dashboard
# Builds frontend and backend into a single container

# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./
COPY frontend/tsconfig.json ./

# Install frontend dependencies
RUN npm install

# Copy frontend source
COPY frontend/src/ ./src/

# Build frontend (TypeScript + assets)
RUN npm run build

# Stage 2: Build backend with frontend
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ .

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/dist/templates ./templates
COPY --from=frontend-builder /app/frontend/dist/css ./static/css
COPY --from=frontend-builder /app/frontend/dist/js ./static/js

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose port (Cloud Run will override this with PORT env var)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; import requests; port = os.getenv('PORT', '8080'); requests.get(f'http://localhost:{port}/', timeout=5)" || exit 1

# Run the application with gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 4 --timeout 120 'src.app:create_app()'"]

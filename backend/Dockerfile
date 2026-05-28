# ──────────────────────────────────────────────────────────────────────────────
# Stage 1: Build dependencies in a virtual environment
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

# Install compilation tools (gcc, etc.) to compile any C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install packages in user space
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --user -r requirements.txt

# ──────────────────────────────────────────────────────────────────────────────
# Stage 2: Final lightweight runtime container
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Copy installed dependencies from the builder stage
COPY --from=builder /root/.local /root/.local

# Copy application source code
COPY backend/ ./backend/

# Ensure local user path is on PATH for uvicorn/pip binaries
ENV PATH=/root/.local/bin:$PATH

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

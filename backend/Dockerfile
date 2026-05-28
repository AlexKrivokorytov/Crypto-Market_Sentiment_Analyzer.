# ──────────────────────────────────────────────────────────────────────────────
# Stage 1: Build — install Python dependencies in an isolated virtual env.
#
# Using a full python:3.12-slim base with build-essential so C extensions
# (e.g. cryptography, bcrypt) can be compiled from source when no wheel exists.
# The resulting /opt/venv directory is copied to the lean runner below.
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Prevent pip from polluting the home dir
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install C build toolchain only in the builder — it will NOT appear in runner.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a dedicated virtual environment for clean, predictable installs.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install requirements in a separate layer so Docker cache is reused
# when only source code changes (not dependencies).
COPY backend/requirements.txt ./requirements.txt
RUN pip install --prefer-binary -r requirements.txt

# ──────────────────────────────────────────────────────────────────────────────
# Stage 2: Runner — minimal production image with no build tooling.
#
# Only the compiled /opt/venv and the application source code are present.
# Image is ~180 MB smaller than a naive single-stage approach.
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    # Activate the venv copied from the builder
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy only the pre-built virtual environment from builder — no compiler needed.
COPY --from=builder /opt/venv /opt/venv

# Copy application source code as the final layer so code changes do not
# invalidate the expensive dependency layer above.
COPY backend/ ./backend/

EXPOSE 8000

# Docker-native health check using the DB-bypass warmup endpoint.
# --start-period gives the container time to boot before probes begin.
# Uses python's urllib so no extra curl/wget package is required.
HEALTHCHECK \
    --interval=30s \
    --timeout=10s \
    --start-period=45s \
    --retries=3 \
    CMD python -c \
        "import urllib.request, sys; \
         r = urllib.request.urlopen('http://localhost:8000/api/v1/healthz', timeout=8); \
         sys.exit(0 if r.status == 200 else 1)"

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

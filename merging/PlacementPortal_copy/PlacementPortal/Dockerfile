# ─────────────────────────────────────────────────────────────────────────────
# Django (PlacementPortal) Dockerfile
#
# HOW IT WORKS WITH VOLUME MOUNTS:
#  1. During `docker build`:
#     - System packages are installed (gcc, ffmpeg, portaudio, etc.)
#     - requirements.txt from the build context is copied into image
#     - All Python packages are installed into the image layer
#
#  2. During `docker compose up`:
#     - The source directory is mounted as a volume at /app
#     - This OVERRIDES the /app directory (code comes from your local disk)
#     - Python packages remain installed in the image layer → NOT overridden
#     - `python manage.py runserver` auto-reloads on any .py file change
#
# So: edit code locally → saved → Django restarts inside container automatically
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Avoid interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# ── System dependencies ───────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Compiler (needed by mysqlclient, numpy, etc.)
    gcc g++ \
    # MySQL client dev headers (for mysqlclient pip package)
    default-libmysqlclient-dev pkg-config \
    # Audio support
    portaudio19-dev \
    ffmpeg \
    # For faster-whisper (OpenMP)
    libgomp1 \
    # Useful for debugging inside container
    curl netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────────────────
# Copy requirements.txt FIRST for Docker layer caching.
# When you only change code (not requirements), this layer is reused → fast rebuild.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── NOTE: We do NOT COPY the app code here ───────────────────────────────
# The code is injected at runtime via docker-compose volume mount:
#   volumes:
#     - ../merging/PlacementPortal_copy/PlacementPortal:/app
#
# This means:
#   - /app/manage.py          → your local manage.py
#   - /app/PlacementPortal/   → your local settings, urls
#   - /app/accounts/          → your local accounts app
#   - etc.

EXPOSE 8000

# Development command — auto-reloads on code changes
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

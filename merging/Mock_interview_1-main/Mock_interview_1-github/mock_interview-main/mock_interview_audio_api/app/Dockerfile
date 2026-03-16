# ─────────────────────────────────────────────────────────────────────────────
# Flask Audio Analysis API Dockerfile
#
# Same volume-mount hot-reload pattern as the Django Dockerfile:
#  - Image bakes in system packages + Python packages
#  - Code comes from volume mount at runtime
#  - Flask debug=True means it reloads on .py file changes
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_ENV=development
ENV FLASK_DEBUG=1

WORKDIR /app

# ── System dependencies ───────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    ffmpeg \
    libgomp1 \
    # For PyAudio / SpeechRecognition
    portaudio19-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# NOTE: Code is NOT copied — volume mount provides it at runtime

EXPOSE 5000

# Flask development server (auto-reload on file changes)
CMD ["python", "app.py"]

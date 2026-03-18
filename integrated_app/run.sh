#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# run.sh — One-shot script to build and start the integrated app in WSL
# Usage (from WSL):
#   cd /mnt/e/DOCKER_NOTES/internal_project/integrated_app
#   chmod +x run.sh
#   ./run.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "════════════════════════════════════════════════════════"
echo "  INTEGRATED APP — PlacementPortal + Mock Interview"
echo "════════════════════════════════════════════════════════"
echo ""

# ── Step 1: Create .env if it doesn't exist ───────────────────────────────
if [ ! -f ".env" ]; then
    echo "→ .env not found. Copying from .env.example..."
    cp .env.example .env
    echo "  ✔ Created .env — EDIT IT before going to production!"
    echo ""
fi

# ── Step 2: Build images ──────────────────────────────────────────────────
echo "→ Building Docker images (this installs all packages inside containers)..."
docker compose build
echo "  ✔ Images built"
echo ""

# ── Step 3: Start infrastructure first (DB, Kafka, HDFS) ─────────────────
echo "→ Starting infrastructure services (MySQL, Kafka, HDFS)..."
docker compose up -d db zookeeper kafka namenode datanode
echo "  ✔ Infrastructure started"
echo ""

# ── Step 4: Wait for MySQL to be ready ───────────────────────────────────
echo "→ Waiting for MySQL to be healthy..."
until docker compose exec db mysqladmin ping -h localhost --silent 2>/dev/null; do
    printf '.'
    sleep 2
done
echo ""
echo "  ✔ MySQL is ready"
echo ""

# ── Step 5: Run Django migrations ─────────────────────────────────────────
echo "→ Running Django migrations..."
docker compose run --rm web python manage.py makemigrations --noinput
docker compose run --rm web python manage.py migrate --noinput
echo "  ✔ Migrations applied"
echo ""

# ── Step 6: Collect static files ─────────────────────────────────────────
echo "→ Collecting static files..."
docker compose run --rm web python manage.py collectstatic --noinput 2>/dev/null || true
echo "  ✔ Static files collected"
echo ""

# ── Step 7: Start all services ────────────────────────────────────────────
echo "→ Starting all services..."
docker compose up -d
echo ""

echo "════════════════════════════════════════════════════════"
echo "  ALL SERVICES RUNNING"
echo "════════════════════════════════════════════════════════"
echo ""
echo "  PlacementPortal (Django) : http://localhost:8000"
echo "  Audio Analysis API (Flask): http://localhost:5000"
echo "  HDFS Web UI              : http://localhost:9870"
echo "  Nginx (proxy)            : http://localhost:80"
echo "  MySQL                    : localhost:3306"
echo ""
echo "  📂 Edit code in:"
echo "     Django  → ../merging/PlacementPortal_copy/PlacementPortal/"
echo "     Flask   → ../merging/.../mock_interview_audio_api/app/"
echo "  Changes reflect immediately (Django auto-reload, Flask debug=True)"
echo ""
echo "  View live logs:"
echo "     docker compose logs -f web           (Django)"
echo "     docker compose logs -f audio_api      (Flask)"
echo "     docker compose logs -f db             (MySQL)"
echo ""
echo "  Stop everything:"
echo "     docker compose down"
echo ""

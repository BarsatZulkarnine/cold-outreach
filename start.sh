#!/usr/bin/env bash
set -e

echo "=== Cold Outreach Bot ==="

# ── Check Docker is running ───────────────────────────────────────────────────
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Start Docker Desktop and try again."
    exit 1
fi

# ── Check .env exists ─────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "Created .env from .env.example"
    echo "Open it and fill in at least these keys, then run ./start.sh again:"
    echo ""
    echo "  ANTHROPIC_API_KEY=   ← required for message generation"
    echo "  GOOGLE_MAPS_API_KEY= ← required for company discovery"
    echo "  HUNTER_API_KEY=      ← optional, improves email finding"
    echo ""
    exit 1
fi

# ── Pre-create bind-mount files ───────────────────────────────────────────────
# Docker creates a DIRECTORY for any file mount that doesn't exist on the host.
# That silently breaks everything, so we touch them first.
for f in outreach.db persona.json gmail_token.json credentials.json \
          linkedin_cookies.json linkedin_rate_limit.json linkedin_daily_counts.json; do
    [ -f "$f" ] || touch "$f"
done

# ── Build and start ───────────────────────────────────────────────────────────
echo "Building and starting containers (first run takes a few minutes)..."
docker compose up --build -d

echo ""
echo "Running at http://localhost:5174"
echo ""
echo "First time? Go to Settings and fill in your persona."
echo ""
echo "Useful commands:"
echo "  docker compose logs -f backend   ← watch backend logs"
echo "  docker compose down              ← stop everything"
echo "  ./start.sh                       ← restart / apply updates"

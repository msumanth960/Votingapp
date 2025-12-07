#!/usr/bin/env bash
# Render Build Script for Django Local Elections App

set -o errexit  # Exit on error

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt

echo "=== Collecting static files ==="
python manage.py collectstatic --no-input

echo "=== Checking database readiness ==="
# Wait for database to be ready before running migrations
# Retries up to 30 times with 2-second intervals (60 seconds max)
MAX_RETRIES=30
RETRY_INTERVAL=2

for i in $(seq 1 $MAX_RETRIES); do
    echo "Attempt $i/$MAX_RETRIES: Checking database connection..."
    
    if python manage.py check --database default 2>/dev/null; then
        echo "Database is ready!"
        break
    fi
    
    if [ $i -eq $MAX_RETRIES ]; then
        echo "ERROR: Database did not become ready after $MAX_RETRIES attempts"
        exit 1
    fi
    
    echo "Database not ready, waiting ${RETRY_INTERVAL}s..."
    sleep $RETRY_INTERVAL
done

echo "=== Running database migrations ==="
python manage.py migrate --no-input

echo "=== Build complete ==="


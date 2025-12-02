#!/bin/bash
set -e

# Function to wait for database (only if using PostgreSQL)
wait_for_db() {
    if [ "${DATABASE_ENGINE:-postgresql}" = "postgresql" ]; then
        echo "Waiting for PostgreSQL database..."
        until python -c "import psycopg2; psycopg2.connect(dbname='${DB_NAME:-cryptobot}', user='${DB_USER:-postgres}', password='${DB_PASSWORD:-postgres}', host='${DB_HOST:-db}', port='${DB_PORT:-5432}')" 2>/dev/null; do
            echo "Database is unavailable - sleeping"
            sleep 1
        done
        echo "Database is ready!"
    else
        echo "Using SQLite database - no wait needed"
    fi
}

wait_for_db

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

echo "Starting server..."
exec "$@"

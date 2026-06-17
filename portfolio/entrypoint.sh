
!/bin/sh

set -e
# set -e = exit immediately if ANY command fails
# Without this: if migrate fails, gunicorn starts anyway on a broken DB

echo "=== Waiting for database to be ready ==="
# Small sleep to let postgres fully initialise on first run
sleep 2

echo "=== Running database migrations ==="
python manage.py migrate --noinput
# Creates all database tables from the migration files without needing confirmation

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput
# Copies all CSS/JS/images from portfolio_pages/static/

echo "=== Starting Gunicorn ==="
exec gunicorn portfolio.wsgi:application     --bind 0.0.0.0:8000     --workers 3     --access-logfile -     --error-logfile -
# exec replaces the shell process with gunicorn

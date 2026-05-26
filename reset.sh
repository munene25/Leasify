#!/bin/bash
# ./reset.sh          # full reset
# ./reset.sh -m       # skip migration deletion
# ./reset.sh -d       # skip db deletion
# ./reset.sh -ms      # skip migrations and seed
set -e

APPS=("apartments" "payments" "tenancy" "users" "billing")

# Default flags
SKIP_MIGRATIONS=false
SKIP_DB=false
SKIP_SEED=false

# Parse flags
while getopts "mds" flag; do
    case "$flag" in
        m) SKIP_MIGRATIONS=true ;;
        d) SKIP_DB=true ;;
        s) SKIP_SEED=true ;;
        *) echo "Usage: $0 [-m skip migrations] [-d skip db] [-s skip seed]"; exit 1 ;;
    esac
done

echo "Cleaning pycache..."
find . -type d -name "__pycache__" -exec rm -rf {} +

if [ "$SKIP_MIGRATIONS" = false ]; then
    for app in "${APPS[@]}"; do
        if [ -d "$app/migrations" ]; then
            echo "Cleaning migrations in $app..."
            find "$app/migrations" -type f -name "*.py" ! -name "__init__.py" -delete
            find "$app/migrations" -type f -name "*.pyc" -delete
        else
            echo "⚠️ No migrations folder found in $app."
        fi
    done
fi

if [ "$SKIP_DB" = false ]; then
    if [ -f "db.sqlite3" ]; then
        rm db.sqlite3
        echo "🗑️ Deleted db.sqlite3"
    fi
fi

echo "Making migrations..."
python3 manage.py makemigrations

echo "Applying migrations..."
python3 manage.py migrate

if [ "$SKIP_SEED" = false ]; then
    echo "Seeding database..."
    python3 manage.py runscript seed
fi

echo "Project reset complete!"

#!/bin/bash

# Exit on error
set -e

APPS=("apartments" "payments" "semesters" "tenancy" "users")

echo "Cleaning pycache and migrations for project apps..."

find . -type d -name "__pycache__" -exec rm -rf {} +

# Loop through each app and clean migrations
for app in "${APPS[@]}"; do
    if [ -d "$app/migrations" ]; then
        echo "Cleaning migrations in $app..."
        # Deletes all files except __init__.py
        find "$app/migrations" -type f -name "*.py" ! -name "__init__.py" -delete
        find "$app/migrations" -type f -name "*.pyc" -delete
    else
        echo "⚠️ No migrations folder found in $app."
    fi
done

# Remove SQLite DB if it exists
if [ -f "db.sqlite3" ]; then
    rm db.sqlite3
    echo "🗑️ Deleted db.sqlite3"
fi

# Run Django migrations again
echo "Making migrations..."
python3 manage.py makemigrations

echo "Applying migrations..."
python3 manage.py migrate

echo "Seeding database from seed.py..."
# Assumes you have django-extensions installed for runscript
python3 manage.py runscript seed

echo "Project reset complete!"

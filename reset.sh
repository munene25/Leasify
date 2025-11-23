#!/bin/bash

# List your Django apps here
APPS=("apartments" "payments" "semesters" "tenancy" "users")

echo "🧹 Cleaning pycache and migrations for project apps..."

# Remove all __pycache__ folders across the project
find . -type d -name "__pycache__" -exec rm -rf {} +

# Loop through each app and clean migrations
for app in "${APPS[@]}"; do
    if [ -d "$app/migrations" ]; then
        echo "Cleaning migrations in $app..."
        find "$app/migrations" -type f -name "*.py" ! -name "__init__.py" -delete
        find "$app/migrations" -type f -name "*.pyc" -delete
    else
        echo "No migrations folder found in $app."
    fi
done

echo "Pycache and app migrations cleaned."

# Remove SQLite DB if it exists
if [ -f "db.sqlite3" ]; then
    rm db.sqlite3
    echo "Deleted db.sqlite3"
else
    echo "No db.sqlite3 file found."
fi

# Run Django migrations again
echo "Making migrations..."
python manage.py makemigrations

echo "Applying migrations..."
python manage.py migrate

echo "Project reset complete!"

echo "Seeding database from seed.py"
python manage.py runscript seed

echo "Seeding database complete"

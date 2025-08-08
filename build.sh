#!/usr/bin/env bash
# Build script for Render deployment

set -e

echo "Installing dependencies..."
pip install --upgrade pip

# Install dependencies from pyproject.toml
echo "Installing project dependencies..."
python -m pip install .

echo "Verifying installation..."
python -c "import flask, psycopg2, gunicorn; print('✓ Required packages installed successfully')"

echo "Setting up database..."
python -c "
import os
if os.environ.get('DATABASE_URL'):
    try:
        from app import app, db
        with app.app_context():
            db.create_all()
            print('✓ Database tables created successfully')
    except Exception as e:
        print(f'⚠️  Database setup will be completed on first run: {e}')
else:
    print('⚠️  DATABASE_URL not set, skipping database setup')
"

echo "✅ Build completed successfully!"
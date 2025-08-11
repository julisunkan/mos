#!/bin/bash

echo "🚀 Starting Cloud POS & Inventory Manager build process..."

# Update pip and install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -e .

# Alternative: Install from pyproject.toml directly if above fails
if [ $? -ne 0 ]; then
    echo "🔄 Installing dependencies from pyproject.toml..."
    pip install $(grep -E "^\s*[\"']" pyproject.toml | sed 's/[",]//g' | awk '{print $1}')
fi

# Install gunicorn specifically if missing
echo "🛠️ Ensuring gunicorn is available..."
pip install gunicorn

# Verify critical dependencies are installed
echo "🔍 Verifying dependencies..."
python -c "import werkzeug, flask, sqlalchemy, psycopg2, gunicorn; print('✅ Core dependencies verified')"

echo "✅ Build process completed successfully!"
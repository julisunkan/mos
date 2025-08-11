#!/bin/bash

echo "🚀 Starting Cloud POS & Inventory Manager build process..."

# Run deployment migration to ensure all data exists
echo "📊 Running deployment data migration..."
python deploy_setup.py

# Install any additional dependencies if needed
echo "📦 Installing dependencies..."
pip install -r requirements.txt 2>/dev/null || echo "Using existing dependencies"

echo "✅ Build process completed successfully!"